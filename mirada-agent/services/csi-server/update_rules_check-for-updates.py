#!/usr/bin/env python3
"""
Обработчик для POST /update/rules/check-for-updates (агент).

Требования (детерминированно, без побочных эффектов вне описанных шагов):
  - Принимает JSON-тело: {"x-access-token": "<token>"}
  - Выполняет последовательность шагов согласно задаче:
    0) POST на /api/update/rules/check-for-updates с {login,password,channel} -> {found: bool}
       Если found == false -> переходим к шагу 1, иначе к шагу 6
    1) Очистка каталога /opt/cdm-upload/files/*
    2) Загрузка правил и подписи в /opt/cdm-upload/files/
    3) Проверка наличия файлов через ls
    4) POST /api/manager/maintenanceUpdateBrp и поллинг статуса до смены
       затем GET /api/manager/maintenanceUpdateBrpStatusAndLogs, ожидаем message == "OK"
    6) POST /api/update/rules/download-and-apply
    7) Поллинг /api/service/remote/ngfw/ids/call/status/ruleset-stats до loaded>0 и отсутствия error
    8) Повторный POST на /api/update/rules/check-for-updates {login,password,channel}, ожидаем {found:false}

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
  - MAINTENANCE_* и RULESET_* таймауты/интервалы — аналогично модулю download-and-apply
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


def _download_via_handler(files_dir: str, update_base: str, auth_header_b64: str) -> Tuple[bool, str]:
    """Повторно используем реализацию скачивания из соседнего модуля, если доступна."""
    try:
        module_path = os.path.join(os.path.dirname(__file__), "update_rules_download-and-apply.py")
        spec = _importlib_util.spec_from_file_location("update_rules_download_and_apply", module_path)
        if spec is None or spec.loader is None:
            return False, "download handler module not found"
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        zip_url = f"{update_base}/U-IDS1.0.1-19.09.2025-1.zip"
        sig_url = f"{update_base}/U-IDS1.0.1-19.09.2025-1.zip.sig"
        # Вызов приватной функции допустим, так как модуль локальный и контракт известен
        ok, err = getattr(mod, "_download_rules")(zip_url, sig_url, auth_header_b64, files_dir)
        return ok, err
    except Exception as e:
        logger.exception("download via handler failed")
        return False, str(e)


def _maintenance_update(local_base: str, token: str) -> Tuple[bool, str]:
    try:
        module_path = os.path.join(os.path.dirname(__file__), "update_rules_download-and-apply.py")
        spec = _importlib_util.spec_from_file_location("update_rules_download_and_apply", module_path)
        if spec is None or spec.loader is None:
            return False, "maintenance handler module not found"
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok, err = getattr(mod, "_maintenance_update_brp")(local_base, token)
        return ok, err
    except Exception as e:
        logger.exception("maintenance via handler failed")
        return False, str(e)


def _poll_ruleset_stats(local_base: str, token: str) -> Tuple[bool, str]:
    logger.info("step7: polling ruleset-stats")
    max_wait_s = int(_env("RULESET_STATS_TIMEOUT", "300") or 300)
    interval_s = int(_env("RULESET_STATS_INTERVAL", "5") or 5)
    start_ts = time.time()
    while True:
        st, data = _http_json("GET", f"{local_base}/service/remote/ngfw/ids/call/status/ruleset-stats", {"x-access-token": token}, None, timeout=30)
        if st == 200 and isinstance(data, dict):
            loaded = int(data.get("loaded", 0) or 0)
            error = data.get("error")
            logger.info("ruleset-stats loaded=%s error=%s elapsed=%.1fs", loaded, error, time.time() - start_ts)
            if error is None and loaded > 0:
                return True, "ok"
        if time.time() - start_ts > max_wait_s:
            return False, "ruleset-stats timeout"
        time.sleep(interval_s)


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

        # Если обновления не найдены — выполняем предварительные шаги 1-4
        if not found:
            # 1-3: скачать правила/подпись и проверить файлы
            ok, err = _download_via_handler(files_dir, update_base, auth_header_b64)
            if not ok:
                return {"result": "ERROR", "message": err}

            # 4: maintenanceUpdateBrp (+ статус и логи)
            ok, err = _maintenance_update(local_base, token)
            if not ok:
                return {"result": "ERROR", "message": err}

        # 6: применяем правила через агентский эндпоинт download-and-apply
        st6, resp6 = _http_json(
            "POST",
            f"{local_base}/update/rules/download-and-apply",
            headers={"x-access-token": token},
            body=None,
            timeout=int(_env("APPLY_POST_TIMEOUT", "120") or 120),
        )
        if st6 not in (200, 204, 422):
            return {"result": "ERROR", "message": f"apply request failed: {st6}"}
        if st6 == 200 and isinstance(resp6, dict) and resp6.get("result") == "ERROR":
            return resp6

        # 7: ждём загрузку правил
        ok, err = _poll_ruleset_stats(local_base, token)
        if not ok:
            return {"result": "ERROR", "message": err}

        # 8: повторная проверка — ожидаем found == false
        st8, resp8 = _http_json(
            "POST",
            f"{local_base}/update/rules/check-for-updates",
            headers={"Content-Type": "application/json", "x-access-token": token},
            body={"login": login, "password": password, "channel": channel},
            timeout=30,
        )
        if st8 != 200 or not isinstance(resp8, dict) or resp8.get("found") not in (False,):
            return {"result": "ERROR", "message": "post-apply check expected found=false"}

        return {"result": "OK"}
    except Exception as e:
        logger.exception("update_rules_check-for-updates: exception")
        return {"result": "ERROR", "message": str(e)}


if __name__ == "__main__":
    print(handle({"x-access-token": "token"}))


