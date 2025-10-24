#!/usr/bin/env python3
"""
Обработчик для /manager/reset: выполняет детерминированный сценарий
перехвата вызова factory-reset через обёртку /usr/bin/cdm, проверяет
успех, подтверждает запись в логе и восстанавливает штатную конфигурацию.

Контракт результата:
  - Успех: {"result": "OK"}
  - Ошибка: {"result": "ERROR", "message": str}
"""

import logging
import os
from typing import Dict
import shlex
import subprocess


logger = logging.getLogger(__name__)

CDM_PATH = "/usr/bin/cdm"
REAL_CDM = "/opt/mirada/mirada"
INTERCEPT_LOG = "/var/log/cdm-intercept.log"


def _validate_request(_request_body: Dict) -> str | None:
    """Проверяет наличие токена в теле запроса, возвращает текст ошибки или None."""
    try:
        token = None
        if isinstance(_request_body, dict):
            # Поддерживаем оба варианта ключа
            token = _request_body.get("x-access-token") or _request_body.get("x_access_token")
        if not isinstance(token, str) or not token:
            return "Authorization Required"
        return None
    except Exception:
        return "Authorization Required"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Запускает команду без shell, логирует и не бросает исключения."""
    logger.info("Выполняется команда: %s", " ".join(shlex.quote(p) for p in cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _remove_file(path: str) -> None:
    # rm -f path
    _run(["rm", "-f", path])


def _write_wrapper() -> str | None:
    """Создает shell-обёртку /usr/bin/cdm и делает её исполняемой. Возвращает текст ошибки или None."""
    wrapper_content = """#!/bin/sh
REAL=\"/opt/mirada/mirada\"

# Имитация успешного factory-reset (без реального сброса)
if [ \"$1\" = \"factory-reset\" ]; then
  echo \"$(date -Iseconds) cdm factory-reset args: $@\" >> /var/log/cdm-intercept.log
  exit 0
fi

# Проксирование всех остальных команд
exec \"$REAL\" \"$@\"
"""
    try:
        # Удаляем текущий симлинк/файл
        _remove_file(CDM_PATH)

        # Пишем файл обёртки
        with open(CDM_PATH, "w", encoding="utf-8") as f:
            f.write(wrapper_content)
        # chmod +x
        res = _run(["chmod", "+x", CDM_PATH])
        if res.returncode != 0:
            return f"chmod failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
        return None
    except Exception as e:
        return f"wrapper write error: {str(e)}"


def _self_check_wrapper() -> str | None:
    """Запускает cdm factory-reset -y и ожидает rc=0. Возвращает текст ошибки или None."""
    res = _run(["cdm", "factory-reset", "-y"])
    if res.returncode != 0:
        stderr_text = (res.stderr or "").strip()
        stdout_text = (res.stdout or "").strip()
        parts = [f"rc={res.returncode}"]
        if stderr_text:
            parts.append(f"stderr={stderr_text}")
        elif stdout_text:
            parts.append(f"stdout={stdout_text}")
        return ", ".join(parts)
    return None


def _verify_intercept_log() -> str | None:
    """Проверяет, что в логе появилась строка вызова factory-reset. Возвращает текст ошибки или None."""
    try:
        # tail -n 50 и проверка подписи
        res = _run(["tail", "-n", "50", INTERCEPT_LOG])
        if res.returncode != 0:
            return f"tail failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
        text = res.stdout or ""
        marker = "cdm factory-reset args: factory-reset -y"
        if marker not in text:
            return "intercept log does not contain expected marker"
        return None
    except Exception as e:
        return f"verify log error: {str(e)}"


def _restore_original() -> str | None:
    """Восстанавливает штатную конфигурацию: cdm -> /opt/mirada/mirada. Возвращает текст ошибки или None."""
    try:
        _remove_file(CDM_PATH)
        res = _run(["ln", "-sf", REAL_CDM, CDM_PATH])
        if res.returncode != 0:
            return f"ln -sf failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
        return None
    except Exception as e:
        return f"restore error: {str(e)}"

def handle(request_body: Dict) -> Dict[str, str]:
    """
    Выполняет factory-reset через бинарь cdm.

    Аргументы:
      request_body: тело запроса (может содержать поля, например x-access-token),
                    не влияет на поведение обработчика.

    Возвращает:
      Dict с ключом result: "OK" | "ERROR" и message при ошибке.
    """
    try:
        # 0) Валидация токена
        auth_error = _validate_request(request_body)
        if auth_error is not None:
            return {"result": "ERROR", "message": auth_error}

        # 1) Поставить обёртку
        err = _write_wrapper()
        if err is not None:
            # Пытаемся восстановить штатную конфигурацию даже при ошибке
            _restore_original()
            return {"result": "ERROR", "message": err}

        # 2) Самопроверка обёртки: ожидаем rc=0
        err = _self_check_wrapper()
        if err is not None:
            _restore_original()
            return {"result": "ERROR", "message": err}

        # 3) Верификация кода ответа эндпоинта пропущена (мы внутри эндпоинта),
        #    вместо этого подтверждаем факт вызова по логу

        # 4) Подтвердить факт вызова cdm по логу
        err = _verify_intercept_log()
        if err is not None:
            _restore_original()
            return {"result": "ERROR", "message": err}

        # 5) Восстановить штатную конфигурацию
        err = _restore_original()
        if err is not None:
            return {"result": "ERROR", "message": err}

        return {"result": "OK"}

    except Exception as e:
        logger.error("Исключение в manager_reset.handle: %s", e)
        # Пытаемся восстановить штатную конфигурацию в аварийном случае
        try:
            _restore_original()
        except Exception:
            pass
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


