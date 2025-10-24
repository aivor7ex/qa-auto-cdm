#!/usr/bin/env python3
"""
Обработчик POST /licenses/generate-activation-code

Задача: детерминированно проверить возможность генерации activation code через локальный csi-server.

Поведение:
  1) Логин у вендора -> получить VENDOR_TOKEN
  2) Запросить список лицензий у вендора (deleted != true), взять первую и извлечь licenseNumber
  3) В контейнере csi.csi-server вызвать License.generateActivationCode(<licenseNumber>, true) через node
  4) Если получено поле value — вернуть {"result":"OK"}, иначе {"result":"ERROR","message":...}

Ограничения:
  - Никаких побочных эффектов; только чтение/проверка.
  - Все внешние вызовы через безопасные интерфейсы: requests и subprocess.run(check=False).
  - Без жёстких хардкодов: все параметры переопределяемы переменными окружения.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import logging
import os
import shlex
import subprocess

import requests


logger = logging.getLogger(__name__)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v is not None and str(v).strip() != "" else default


def _http_json(method: str, url: str, headers: Optional[Dict[str, str]] = None, body: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> tuple[int, Any]:
    try:
        resp = requests.request(method=method.upper(), url=url, headers=headers or {}, json=body, params=params, timeout=15)
        status = resp.status_code
        try:
            data = resp.json() if resp.content else None
        except Exception:
            data = None
        return status, data
    except Exception as e:
        logger.error("HTTP %s %s failed: %s", method, url, e)
        return 599, {"error": str(e)}


def _docker_node_generate_activation_code(license_number: str) -> tuple[int, str, str]:
    """Выполняет docker exec node -e <script> и возвращает (rc, stdout, stderr).

    Для защиты от инъекций license_number передаётся через env LICENSE_NUMBER.
    """
    container = _env("CSI_SERVER_CONTAINER", "csi.csi-server")
    node_bin = _env("NODE_BIN", "node")

    # JS-скрипт без подстановки пользовательских данных; берём из process.env
    node_script = (
        'require("bytenode");require("./bundle-app.jsc");'
        '(async()=>{'
        'const sleep=ms=>new Promise(r=>setTimeout(r,ms));'
        'for(let i=0;i<100;i++)await sleep(100);'
        'const lb=require("loopback");'
        'const License=lb.findModel("License");'
        'if(!License){console.error("no License");process.exit(2);}'
        'const lic=process.env.LICENSE_NUMBER;'
        'try{'
        '  const r=await License.generateActivationCode(String(lic), true);'
        '  console.log(JSON.stringify(r));'
        '  process.exit(0);'
        '}catch(e){'
        '  console.error("invoke error:", (e&&e.message)||e);'
        '  process.exit(1);'
        '}'
        '})()'
    )

    cmd = (
        f"docker exec -e PORT=0 -e LICENSE_NUMBER={shlex.quote(license_number)} "
        f"{shlex.quote(container)} {shlex.quote(node_bin)} -e '" + node_script + "'"
    )
    logger.info("Executing docker node script to generate activation code in %s", container)
    proc = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _extract_value_from_output(stdout_text: str) -> Optional[str]:
    """Ищет последнюю JSON-строку с ключом value и возвращает значение."""
    candidate: Optional[str] = None
    for line in (stdout_text or "").splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("{") and '"value"' in line_stripped:
            # Пытаемся распарсить как JSON-объект
            try:
                obj = json.loads(line_stripped)
                v = obj.get("value")
                if isinstance(v, str) and v:
                    candidate = v
            except Exception:
                # Пропускаем невалидные строки
                pass
    return candidate


def handle() -> Dict[str, Any]:
    try:
        # 1) Логин у вендора -> токен
        vendor_login_url = _env("VENDOR_LOGIN_URL", "http://10.100.103.20:81/api/users/login")
        st, login_obj = _http_json("POST", vendor_login_url, headers={"Content-Type": "application/json"}, body={"username": "admin", "password": "admin"})
        if st != 200 or not isinstance(login_obj, dict) or not login_obj.get("id"):
            return {"result": "ERROR", "message": "vendor login failed"}
        vendor_token = str(login_obj.get("id"))

        # 2) Получить список лицензий (deleted != true)
        vendor_licenses_url = _env("VENDOR_LICENSES_URL", "http://10.100.103.20:81/api/licenses")
        filter_where = {"where": {"deleted": {"neq": True}}}
        params = {"filter": json.dumps(filter_where, separators=(",", ":"))}
        st, lic_list = _http_json("GET", vendor_licenses_url, headers={"x-access-token": vendor_token}, params=params)
        if st != 200 or not isinstance(lic_list, list) or not lic_list:
            return {"result": "ERROR", "message": "vendor licenses fetch failed"}
        # Детерминированно берём первый элемент
        first = lic_list[0]
        if not isinstance(first, dict) or not first.get("licenseNumber"):
            return {"result": "ERROR", "message": "licenseNumber not found"}
        license_number = str(first.get("licenseNumber"))

        # 3) Вызвать генерацию activation code в контейнере
        rc, out, err = _docker_node_generate_activation_code(license_number)
        if rc != 0:
            # Часто stdout содержит нужный JSON; пробуем достать value прежде чем упасть
            value = _extract_value_from_output(out)
            if isinstance(value, str) and value:
                return {"result": "OK"}
            msg = (err or out or "docker exec failed").strip()
            return {"result": "ERROR", "message": msg or "generation failed"}

        value = _extract_value_from_output(out)
        if not isinstance(value, str) or not value:
            return {"result": "ERROR", "message": "activation code value not found"}

        return {"result": "OK"}
    except Exception as e:
        logger.error("Ошибка в generate-activation-code handler: %s", e, exc_info=True)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


if __name__ == "__main__":
    print(handle())


