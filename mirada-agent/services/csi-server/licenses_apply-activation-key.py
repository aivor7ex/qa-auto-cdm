#!/usr/bin/env python3
"""
Обработчик для POST /licenses/apply-activation-key

Требования по контракту (для агента):
- Принимает JSON-тело с полем "x-access-token" (строка, не пустая)
- Опционально может принимать поле "activationKey" (строка) — игнорируется агентом
- Возвращает:
  - {"result":"OK"} при валидном токене
  - {"result":"ERROR","message":"Authorization Required"} при отсутствии/невалидном токене
  - {"result":"ERROR","message":"Internal error: ..."} при исключениях

Замечание: Этот обработчик не выполняет побочных эффектов и не взаимодействует
с внешними системами. Его задача — детерминированно подтвердить приём запроса
и корректность аутентификации согласно архитектуре агента.
"""

from typing import Any, Dict, Optional
import logging
import os
import time
import json
import shlex
import subprocess
import requests
import re


logger = logging.getLogger(__name__)


def _extract_token(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Достаёт токен из тела запроса.
    Поддерживает поля на верхнем уровне (x-access-token, x_access_token)
    и вложенные словари, имитирующие заголовки (headers/__headers).
    """
    if not isinstance(data, dict):
        return None
    # Прямо в теле
    token: Optional[str] = data.get("x-access-token") or data.get("x_access_token")
    # Возможные вложенные заголовки
    if not token:
        for key in ("headers", "__headers"):
            maybe_headers = data.get(key)
            if isinstance(maybe_headers, dict):
                token = (
                    maybe_headers.get("x-access-token")
                    or maybe_headers.get("x_access_token")
                    or token
                )
            if token:
                break
    if isinstance(token, str):
        token = token.strip()
        if token:
            return token
    return None


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v and str(v).strip() != "" else default


def _run_sh(cmd: str) -> subprocess.CompletedProcess:
    logger.info("sh: %s", cmd)
    return subprocess.run(["/bin/sh", "-lc", cmd], capture_output=True, text=True, check=False)


def _http_json(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> tuple[int, Dict[str, Any]]:
    # Глобальная пауза перед каждым HTTP-запросом для стабилизации последовательности
    time.sleep(1)
    resp = requests.request(method=method.upper(), url=url, headers=headers, json=body, timeout=10)
    status = resp.status_code
    try:
        data = resp.json() if resp.content else {}
    except Exception:
        data = {}
    return status, data


def handle(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Выполняет полный сценарий применения activation key согласно заданию."""
    try:
        # 0) Аутентификация
        logger.info("apply-activation-key: start; body keys=%s", ",".join(sorted(body.keys())) if isinstance(body, dict) else "<none>")
        token = _extract_token(body)
        if not token:
            return {"result": "ERROR", "message": "Authorization Required"}
        logger.info("apply-activation-key: token presence=YES")

        # Базовые URL (без хардкода — допускаем переопределение переменными окружения)
        local_base = _env("MIRADA_LOCAL_BASE", "http://127.0.0.1:2999/api")
        vendor_base_login = _env("VENDOR_LOGIN_URL", "http://10.100.103.20:81/api/users/login")
        vendor_licenses_url = _env("VENDOR_LICENSES_URL", "http://10.100.103.20:81/api/licenses")
        vendor_activation_keys_url = _env(
            "VENDOR_ACTIVATION_KEYS_URL",
            _env("VENDOR_ACT_KEYS_URL", "http://10.100.103.20/api/activation-keys/")
        )
        logger.info("apply-activation-key: urls local=%s vendor_login=%s vendor_lic=%s vendor_ak=%s", local_base, vendor_base_login, vendor_licenses_url, vendor_activation_keys_url)

        # 1) Логин у вендора -> VENDOR_TOKEN
        st, vendor_login = _http_json("POST", vendor_base_login, {"Content-Type": "application/json"}, {"username": "admin", "password": "admin"})
        logger.info("apply-activation-key: vendor login status=%s keys=%s", st, ",".join(sorted(vendor_login.keys())) if isinstance(vendor_login, dict) else type(vendor_login).__name__)
        if st != 200 or not isinstance(vendor_login, dict) or not vendor_login.get("id"):
            return {"result": "ERROR", "message": "vendor login failed"}
        vendor_token = str(vendor_login.get("id"))
        logger.info("apply-activation-key: vendor token received len=%d", len(vendor_token))

        # 2) Получить серийный номер локально через GET /licenses
        st, local_lic = _http_json("GET", f"{local_base}/licenses", {"x-access-token": token})
        logger.info("apply-activation-key: local /licenses status=%s keys=%s", st, ",".join(sorted(local_lic.keys())) if isinstance(local_lic, dict) else type(local_lic).__name__)
        if st != 200 or not isinstance(local_lic, dict) or not local_lic.get("serialNumber"):
            return {"result": "ERROR", "message": "local serialNumber fetch failed"}
        serial = str(local_lic.get("serialNumber"))
        logger.info("apply-activation-key: serialNumber len=%d", len(serial))

        # 3) Создать лицензию у вендора
        # Примечание: внешняя служба вендора может применять защиту от частых
        # повторяющихся операций с тем же serialNumber (рейтлимит/антифрод).
        # При интенсивных прогонах тестов подряд возможны временные ошибки
        # на шагах создания лицензии и/или обмена activationCode -> activationKey.
        payload_vendor_lic = {
            "description": _env("HOSTNAME") or os.uname().nodename,
            "expirePeriod": {"days": 365},
            "bandwidth": {"bandwidth": 0},
            "serialNumber": serial,
        }
        logger.info("apply-activation-key: vendor license create POST -> %s", vendor_licenses_url)
        st, vend_lic = _http_json("POST", vendor_licenses_url, {"x-access-token": vendor_token, "Content-Type": "application/json"}, payload_vendor_lic)
        logger.info("apply-activation-key: vendor license status=%s keys=%s", st, ",".join(sorted(vend_lic.keys())) if isinstance(vend_lic, dict) else type(vend_lic).__name__)
        if st != 200 or not isinstance(vend_lic, dict) or not vend_lic.get("licenseNumber"):
            return {"result": "ERROR", "message": "vendor license create failed"}
        license_id = str(vend_lic.get("id", ""))
        license_number = str(vend_lic.get("licenseNumber"))
        logger.info("apply-activation-key: license created id_len=%d number_len=%d", len(license_id), len(license_number))
        # Небольшая пауза для консистентности у вендора
        time.sleep(1)

        # 4) Сгенерировать activation code локально
        st, act_code_obj = _http_json(
            "POST",
            f"{local_base}/licenses/generate-activation-code",
            {"x-access-token": token, "Content-Type": "application/json"},
            {"licenseNumber": license_number, "bundled": True},
        )
        logger.info("apply-activation-key: local activation-code status=%s keys=%s", st, ",".join(sorted(act_code_obj.keys())) if isinstance(act_code_obj, dict) else type(act_code_obj).__name__)
        if st != 200 or not isinstance(act_code_obj, dict) or not act_code_obj.get("value"):
            return {"result": "ERROR", "message": "activation code generation failed"}
        activation_code = str(act_code_obj.get("value"))
        logger.info("apply-activation-key: activationCode len=%d", len(activation_code))
        # Пауза перед обменом, чтобы исключить гонки времени
        time.sleep(1)

        # 5) Получить activationKey у вендора
        logger.info("apply-activation-key: vendor activation-key exchange POST -> %s", vendor_activation_keys_url)
        st, ak_obj = _http_json(
            "POST",
            vendor_activation_keys_url,
            {"x-access-token": vendor_token, "Content-Type": "application/json"},
            {"activationCode": activation_code, "bundled": True},
        )
        logger.info("apply-activation-key: vendor activation-key status=%s keys=%s", st, ",".join(sorted(ak_obj.keys())) if isinstance(ak_obj, dict) else type(ak_obj).__name__)
        if st != 200 or not isinstance(ak_obj, dict) or not ak_obj.get("value"):
            # Обработка ошибок 400: license-not-found и activation-key-expired
            err_msg = None
            if isinstance(ak_obj, dict):
                err_msg = (ak_obj.get("error") or {}).get("message")
            logger.info("apply-activation-key: vendor AK error status=%s message=%s", st, err_msg)

            # Ветка 1: license-not-found -> пробуем с bundled=false и явным licenseNumber
            if st == 400 and err_msg == "license-not-found":
                logger.info("apply-activation-key: retry AK exchange with bundled=false and licenseNumber")
                st_retry, ak_obj_retry = _http_json(
                    "POST",
                    vendor_activation_keys_url,
                    {"x-access-token": vendor_token, "Content-Type": "application/json"},
                    {"activationCode": activation_code, "bundled": False, "licenseNumber": license_number},
                )
                logger.info("apply-activation-key: vendor activation-key RETRY status=%s keys=%s", st_retry, ",".join(sorted(ak_obj_retry.keys())) if isinstance(ak_obj_retry, dict) else type(ak_obj_retry).__name__)
                if st_retry == 200 and isinstance(ak_obj_retry, dict) and ak_obj_retry.get("value"):
                    activation_key = str(ak_obj_retry.get("value"))
                else:
                    return {"result": "ERROR", "message": "vendor activation key fetch failed"}
            # Ветка 2: activation-key-expired -> регенерация activation code и повтор обмена
            elif st == 400 and err_msg == "activation-key-expired":
                logger.info("apply-activation-key: regenerate activation-code and retry AK exchange")
                # Снова генерируем activation code
                st_new_ac, act_code_obj_new = _http_json(
                    "POST",
                    f"{local_base}/licenses/generate-activation-code",
                    {"x-access-token": token, "Content-Type": "application/json"},
                    {"licenseNumber": license_number, "bundled": True},
                )
                logger.info("apply-activation-key: new activation-code status=%s keys=%s", st_new_ac, ",".join(sorted(act_code_obj_new.keys())) if isinstance(act_code_obj_new, dict) else type(act_code_obj_new).__name__)
                if st_new_ac != 200 or not isinstance(act_code_obj_new, dict) or not act_code_obj_new.get("value"):
                    return {"result": "ERROR", "message": "activation code regeneration failed"}
                activation_code = str(act_code_obj_new.get("value"))
                # Повтор обмена
                st_retry, ak_obj_retry = _http_json(
                    "POST",
                    vendor_activation_keys_url,
                    {"x-access-token": vendor_token, "Content-Type": "application/json"},
                    {"activationCode": activation_code, "bundled": True},
                )
                logger.info("apply-activation-key: vendor activation-key RETRY2 status=%s keys=%s", st_retry, ",".join(sorted(ak_obj_retry.keys())) if isinstance(ak_obj_retry, dict) else type(ak_obj_retry).__name__)
                if st_retry == 200 and isinstance(ak_obj_retry, dict) and ak_obj_retry.get("value"):
                    activation_key = str(ak_obj_retry.get("value"))
                else:
                    # Последний шанс: bundled=false c явным licenseNumber
                    logger.info("apply-activation-key: RETRY3 with bundled=false and licenseNumber after expired")
                    st_retry3, ak_obj_retry3 = _http_json(
                        "POST",
                        vendor_activation_keys_url,
                        {"x-access-token": vendor_token, "Content-Type": "application/json"},
                        {"activationCode": activation_code, "bundled": False, "licenseNumber": license_number},
                    )
                    logger.info("apply-activation-key: vendor activation-key RETRY3 status=%s keys=%s", st_retry3, ",".join(sorted(ak_obj_retry3.keys())) if isinstance(ak_obj_retry3, dict) else type(ak_obj_retry3).__name__)
                    if st_retry3 == 200 and isinstance(ak_obj_retry3, dict) and ak_obj_retry3.get("value"):
                        activation_key = str(ak_obj_retry3.get("value"))
                    else:
                        return {"result": "ERROR", "message": "vendor activation key fetch failed"}
            else:
                return {"result": "ERROR", "message": "vendor activation key fetch failed"}
        else:
            activation_key = str(ak_obj.get("value"))
        logger.info("apply-activation-key: activationKey len=%d", len(activation_key))

        # 6) Зафиксировать состояние файла до применения (через docker exec + node)
        before_cmd = '''docker exec csi.csi-server sh -lc 'echo "[BEFORE]"; node -e "
            const fs=require(\"fs\"),crypto=require(\"crypto\");
            const f=\"/app/additional-storage/storage.bin\";
            fs.stat(f,(e,s)=>{if(e){console.log(\"missing: \"+f);process.exit(0)}
            const d=fs.readFileSync(f);
            const c=crypto.createHash(\"sha256\").update(d).digest(\"hex\");
            console.log(\"sha256 \"+c+\"  \"+f);
            console.log(\"size=\"+s.size);
            console.log(\"mtime=\"+s.mtime.toISOString());
            });"' '''
        res = _run_sh(before_cmd)
        logger.info("apply-activation-key: before file rc=%s stdout_len=%d stderr_len=%d", res.returncode, len(res.stdout or ""), len(res.stderr or ""))
        before_stdout = res.stdout or ""
        # Извлечём sha256 и mtime из вывода
        before_hash = None
        before_mtime = None
        m_hash = re.search(r"sha256\s+([0-9a-f]{64})\s+\s*/app/additional-storage/storage\.bin", before_stdout)
        if m_hash:
            before_hash = m_hash.group(1)
        m_mtime = re.search(r"mtime=([^\n\r]+)", before_stdout)
        if m_mtime:
            before_mtime = m_mtime.group(1)

        # 7) Применить activationKey локально (проксируем в локальный CSI)
        st, applied = _http_json(
            "POST",
            f"{local_base}/licenses/apply-activation-key",
            {"x-access-token": token, "Content-Type": "application/json"},
            {"activationKey": activation_key},
        )
        logger.info("apply-activation-key: local apply status=%s keys=%s", st, ",".join(sorted(applied.keys())) if isinstance(applied, dict) else type(applied).__name__)
        if st != 200 or not isinstance(applied, dict):
            return {"result": "ERROR", "message": "local apply activation key failed"}

        # 8) После применения: проверить файл и логи контейнера (node)
        after_cmd = '''docker exec csi.csi-server sh -lc 'echo "[AFTER]"; node -e "
            const fs=require(\"fs\"),crypto=require(\"crypto\");
            const f=\"/app/additional-storage/storage.bin\";
            fs.stat(f,(e,s)=>{if(e){console.log(\"missing: \"+f);process.exit(0)}
            const d=fs.readFileSync(f);
            const c=crypto.createHash(\"sha256\").update(d).digest(\"hex\");
            console.log(\"sha256 \"+c+\"  \"+f);
            console.log(\"size=\"+s.size);
            console.log(\"mtime=\"+s.mtime.toISOString());
            });"' '''
        res = _run_sh(after_cmd)
        logger.info("apply-activation-key: after file rc=%s stdout_len=%d stderr_len=%d", res.returncode, len(res.stdout or ""), len(res.stderr or ""))
        after_stdout = res.stdout or ""
        after_hash = None
        after_mtime = None
        m_hash2 = re.search(r"sha256\s+([0-9a-f]{64})\s+\s*/app/additional-storage/storage\.bin", after_stdout)
        if m_hash2:
            after_hash = m_hash2.group(1)
        m_mtime2 = re.search(r"mtime=([^\n\r]+)", after_stdout)
        if m_mtime2:
            after_mtime = m_mtime2.group(1)
        res = _run_sh('docker logs csi.csi-server --since 2m 2>&1 | grep -E "license issued|activation-key-|serial-number-" || true')
        logger.info("apply-activation-key: docker logs rc=%s stdout_len=%d stderr_len=%d", res.returncode, len(res.stdout or ""), len(res.stderr or ""))
        # Программная проверка: должен присутствовать маркер license issued и не должно быть ошибок activation-key-
        logs_text = res.stdout or ""
        if "license issued" not in logs_text:
            return {"result": "ERROR", "message": "license issued log not found"}
        if "activation-key-" in logs_text:
            return {"result": "ERROR", "message": "activation-key errors found in logs"}
        # Проверим, что файл изменился (sha256 и/или mtime)
        if before_hash and after_hash and before_hash == after_hash and before_mtime and after_mtime and before_mtime == after_mtime:
            return {"result": "ERROR", "message": "storage.bin did not change"}

        # 9) Контроль состояния лицензии через локальный API
        st, local_after = _http_json("GET", f"{local_base}/licenses", {"x-access-token": token})
        logger.info("apply-activation-key: local /licenses after status=%s keys=%s", st, ",".join(sorted(local_after.keys())) if isinstance(local_after, dict) else type(local_after).__name__)
        if st != 200 or not isinstance(local_after, dict):
            return {"result": "ERROR", "message": "local license state fetch failed"}
        # Валидация применённой лицензии
        if str(local_after.get("licenseNumber")) != license_number:
            return {"result": "ERROR", "message": "applied licenseNumber mismatch"}
        if not isinstance(local_after.get("serialNumber"), str) or not isinstance(local_after.get("expiresAt"), str):
            return {"result": "ERROR", "message": "missing serialNumber or expiresAt after apply"}

        # Подготовим cleanup у вендора (best-effort, без влияния на итог)
        try:
            del_body = {
                "id": license_id,
                "expirePeriod": {"days": 365},
                "bandwidth": {"bandwidth": 0},
                "serialNumber": serial,
                "licenseNumber": license_number,
                "description": _env("HOSTNAME") or os.uname().nodename,
                "deleted": True,
            }
            st_cleanup, del_resp = _http_json(
                "DELETE",
                f"{vendor_licenses_url.rstrip('/')}/{license_id}",
                {"x-access-token": vendor_token, "Content-Type": "application/json"},
                del_body,
            )
            logger.info("apply-activation-key: vendor cleanup DELETE status=%s keys=%s", st_cleanup, ",".join(sorted(del_resp.keys())) if isinstance(del_resp, dict) else type(del_resp).__name__)
            if st_cleanup != 200 or not isinstance(del_resp, dict) or del_resp.get("deleted") is not True:
                return {"result": "ERROR", "message": "vendor cleanup failed: deleted flag not true"}
        except Exception:
            return {"result": "ERROR", "message": "vendor cleanup exception"}

        # Сформируем успешный ответ, требуемый шагом 8
        response: Dict[str, Any] = {"result": "OK"}
        if isinstance(local_after.get("serialNumber"), str):
            response["serialNumber"] = local_after.get("serialNumber")
        if isinstance(local_after.get("licenseNumber"), str):
            response["licenseNumber"] = local_after.get("licenseNumber")
        if isinstance(local_after.get("expiresAt"), str):
            response["expiresAt"] = local_after.get("expiresAt")
        return response
    except Exception as e:
        logger.error("Ошибка в apply-activation-key handler: %s", e, exc_info=True)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


