#!/usr/bin/env python3
"""
Обработчик для POST /update/rules/start-download

Требования (детерминированно, без побочных эффектов вне описанных шагов):
  1) Принимает JSON-тело: {"x-access-token": "<token>"}
  2) Выполняет последовательность шагов согласно задаче:
    0) POST на /api/update/rules/check-for-updates с {login,password,channel} -> {found: bool}
       Если found == false -> переходим к шагу 1, иначе к шагу 6
    1) Очистка каталога /opt/cdm-upload/files/*
    2) Загрузка правил и подписи в /opt/cdm-upload/files/
    3) Проверка наличия файлов через ls
    4) POST /api/manager/maintenanceUpdateBrp и поллинг статуса до смены
       затем GET /api/manager/maintenanceUpdateBrpStatusAndLogs, ожидаем message == "OK"
     5) /manager/maintenanceUpdateBrpStatusAndLogs должен ответить "message": "OK"
     6) Повторный POST на /api/update/rules/start-download {x-access-token}, ожидаем {"ok": 1}

Возвращает:
  - {"result":"OK"} при успехе
  - {"result":"ERROR","message":"..."} при ошибке

Конфигурация через переменные окружения (без хардкода):
  - MIRADA_LOCAL_BASE (по умолчанию http://127.0.0.1:2999/api)
  - UPDATE_LOGIN (по умолчанию test)
  - UPDATE_PASSWORD (по умолчанию JDlmRGPq)
  - UPDATE_CHANNEL (по умолчанию release)
  - UPDATE_BASE_URL (по умолчанию prod URL из ТЗ)
  - AUTH_HEADER_B64 (по умолчанию dGVzdDpKRGxtUkdQcQ==)
  - ZIP_NAME, SIG_NAME (имена файлов правил; по умолчанию берутся из URL)
  - MAINTENANCE_* и RULESET_* таймауты/интервалы
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
import logging
from typing import Any, Dict, Optional, Tuple

import requests
import importlib.util as _importlib_util


logger = logging.getLogger(__name__)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if (v is not None and str(v).strip() != "") else default


def _extract_token(body: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    token = body.get("x-access-token") or body.get("x_access_token")
    if isinstance(token, str):
        token = token.strip()
        if token:
            return token
    return None


def _http_json(method: str, url: str, headers: Dict[str, str], body: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Tuple[int, Dict[str, Any]]:
    logger.info("http %s %s headers=%s body_keys=%s timeout=%ss", method.upper(), url, 
                ",".join(sorted(headers.keys())), 
                ",".join(sorted((body or {}).keys())), timeout)
    kwargs: Dict[str, Any] = {"headers": headers, "timeout": timeout}
    if body is not None:
        kwargs["json"] = body
    resp = requests.request(method=method.upper(), url=url, **kwargs)
    status = resp.status_code
    try:
        data = resp.json() if resp.content else {}
    except Exception:
        data = {}
    logger.info("http status=%s json_keys=%s", status, ",".join(sorted(data.keys())) if isinstance(data, dict) else type(data).__name__)
    return status, data


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    logger.info("exec: %s", " ".join(shlex.quote(x) for x in cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    logger.info("rc=%s stdout_len=%d stderr_len=%d", res.returncode, len(res.stdout or ""), len(res.stderr or ""))
    return res


def _ensure_dir(path: str) -> bool:
    try:
        logger.info("ensure dir: %s", path)
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        logger.exception("ensure dir failed: %s", path)
        return False


def _download_rules(zip_url: str, sig_url: str, auth_header_b64: str, files_dir: str) -> Tuple[bool, str]:
    """Скачивает правила и подпись в указанную директорию"""
    # Очистка каталога
    logger.info("step1: cleanup dir %s", files_dir)
    if not _ensure_dir(files_dir):
        return False, f"cannot ensure dir: {files_dir}"

    _run(["/bin/sh", "-lc", f"rm -rf {shlex.quote(files_dir)}/*"])  # игнорируем результат

    # Скачивание curl -k --location ... --header 'Authorization: Basic ...' --output ...
    logger.info("step2: download rules -> %s and signature -> %s", zip_url, sig_url)
    zip_name = _env("ZIP_NAME", os.path.basename(zip_url)) or os.path.basename(zip_url)
    sig_name = _env("SIG_NAME", os.path.basename(sig_url)) or os.path.basename(sig_url)

    curl_base = ["curl", "-k", "--location", "--fail", "--silent", "--show-error"]

    zip_out = os.path.join(files_dir, zip_name)
    sig_out = os.path.join(files_dir, sig_name)

    auth_header = f"Authorization: Basic {auth_header_b64}"

    p1 = _run(curl_base + ["--header", auth_header, "--output", zip_out, zip_url])
    if p1.returncode != 0:
        logger.error("zip download failed")
        return False, f"zip download failed: rc={p1.returncode} err={p1.stderr.strip()}"

    p2 = _run(curl_base + ["--header", auth_header, "--output", sig_out, sig_url])
    if p2.returncode != 0:
        logger.error("sig download failed")
        return False, f"sig download failed: rc={p2.returncode} err={p2.stderr.strip()}"

    # Проверка наличия файлов через ls -la
    logger.info("step3: verify files presence via ls -la")
    p3 = _run(["/bin/sh", "-lc", f"ls -la {shlex.quote(files_dir)}"])
    if p3.returncode != 0:
        return False, f"ls failed: rc={p3.returncode} err={p3.stderr.strip()}"

    if not (os.path.isfile(zip_out) and os.path.isfile(sig_out)):
        return False, "downloaded files not found"

    logger.info("files present: %s, %s", zip_out, sig_out)
    return True, "ok"


def _maintenance_update_brp(local_base: str, token: str) -> Tuple[bool, str]:
    """Выполняет обновление BRP и ожидает завершения"""
    # 4) Основной POST: /manager/maintenanceUpdateBrp
    logger.info("step4: POST maintenanceUpdateBrp")
    post_headers = {"x-access-token": token, "Connection": "keep-alive", "Keep-Alive": "timeout=60, max=1000"}
    post_timeout = int(_env("MAINTENANCE_POST_TIMEOUT", "60") or 60)
    st, resp = _http_json("POST", f"{local_base}/manager/maintenanceUpdateBrp", post_headers, body=None, timeout=post_timeout)
    if st != 200:
        return False, f"maintenanceUpdateBrp POST failed: {st}"

    # 4.1) Поллинг статуса, пока message == "updating"
    logger.info("step4.1: polling maintenanceUpdateBrpStatus")
    max_wait_s = int(_env("MAINTENANCE_STATUS_TIMEOUT", "300") or 300)
    interval_s = int(_env("MAINTENANCE_STATUS_INTERVAL", "2") or 2)
    start_ts = time.time()
    while True:
        st_s, resp_s = _http_json("GET", f"{local_base}/manager/maintenanceUpdateBrpStatus", {"x-access-token": token, "Connection": "keep-alive"}, body=None, timeout=max(interval_s * 2, 10))
        if st_s != 200:
            return False, f"status GET failed: {st_s}"
        msg = resp_s.get("message") if isinstance(resp_s, dict) else None
        logger.info("status message=%s elapsed=%.1fs", msg, time.time() - start_ts)
        if msg != "updating":
            break
        if time.time() - start_ts > max_wait_s:
            return False, "status timeout"
        time.sleep(interval_s)

    # 4.2) Получить статус и логи
    logger.info("step4.2: GET maintenanceUpdateBrpStatusAndLogs")
    st_l, resp_l = _http_json("GET", f"{local_base}/manager/maintenanceUpdateBrpStatusAndLogs", {"x-access-token": token, "Connection": "keep-alive"}, body=None, timeout=30)
    if st_l != 200:
        return False, f"statusAndLogs GET failed: {st_l}"
    if not isinstance(resp_l, dict) or resp_l.get("message") != "OK":
        return False, "maintenanceUpdateBrpStatusAndLogs not OK"

    return True, "ok"


def handle(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        token = _extract_token(body)
        if not token:
            return {"result": "ERROR", "message": "Authorization Required"}

        local_base = _env("MIRADA_LOCAL_BASE", "http://127.0.0.1:2999/api")
        login = _env("UPDATE_LOGIN", "test")
        password = _env("UPDATE_PASSWORD", "JDlmRGPq")
        channel = _env("UPDATE_CHANNEL", "release")
        update_base = _env("UPDATE_BASE_URL", "https://update.codemaster.pro/mirada/rules/release/2025-09-19T10%3A44%3A25.185744")
        auth_header_b64 = _env("AUTH_HEADER_B64", "dGVzdDpKRGxtUkdQcQ==")
        files_dir = "/opt/cdm-upload/files"

        logger.info("env: local_base=%s channel=%s", local_base, channel)

        # Шаг 0: локальная проверка обновлений (без токена)
        st0, resp0 = _http_json(
            "POST",
            f"{local_base}/update/rules/check-for-updates",
            headers={"Content-Type": "application/json", "x-access-token": token},
            body={"login": login, "password": password, "channel": channel},
            timeout=30,
        )
        if st0 != 200 or not isinstance(resp0, dict) or "found" not in resp0:
            return {"result": "ERROR", "message": f"initial check failed: {st0}"}

        found = bool(resp0.get("found"))
        logger.info("step0: found=%s", found)

        # Если обновления не найдены — выполняем предварительные шаги 1-5
        if not found:
            # 1) Очистка каталога
            logger.info("step1: cleanup dir %s", files_dir)
            if not _ensure_dir(files_dir):
                return {"result": "ERROR", "message": f"cannot ensure dir: {files_dir}"}
            _run(["/bin/sh", "-lc", f"rm -rf {shlex.quote(files_dir)}/*"])

            # 2) Скачивание правил и подписи
            zip_url = f"{update_base}/U-IDS1.0.1-19.09.2025-1.zip"
            sig_url = f"{update_base}/U-IDS1.0.1-19.09.2025-1.zip.sig"
            
            ok, err = _download_rules(zip_url, sig_url, auth_header_b64, files_dir)
            if not ok:
                return {"result": "ERROR", "message": err}

            # 4) maintenanceUpdateBrp (+ статус и логи)
            ok, err = _maintenance_update_brp(local_base, token)
            if not ok:
                return {"result": "ERROR", "message": err}

        # 6) Повторный POST на /api/update/rules/start-download
        logger.info("step6: final POST to start-download")
        st6, resp6 = _http_json(
            "POST",
            f"{local_base}/update/rules/start-download",
            headers={"x-access-token": token},
            body=None,
            timeout=30,
        )
        if st6 != 200 or not isinstance(resp6, dict) or resp6.get("ok") != 1:
            return {"result": "ERROR", "message": "final start-download check failed"}

        return {"result": "OK"}
    except Exception as e:
        logger.exception("update_rules_start-download: exception")
        return {"result": "ERROR", "message": str(e)}


if __name__ == "__main__":
    print(handle({"x-access-token": "token"}))
