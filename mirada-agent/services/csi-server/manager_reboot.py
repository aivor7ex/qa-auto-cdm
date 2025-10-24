#!/usr/bin/env python3
"""
Обработчик для /manager/reboot: безопасно подменяет бинарь reboot на заглушку,
выполняет самопроверку вызовом "reboot --help" (логирует факт вызова),
подтверждает наличие записи в логе и восстанавливает исходный бинарь.

Контракт результата:
  - Успех: {"result": "OK"}
  - Ошибка: {"result": "ERROR", "message": str}
"""

from typing import Dict
import logging
import os
import shlex
import subprocess


logger = logging.getLogger(__name__)

INTERCEPT_LOG = "/var/log/reboot-intercept.log"


def _validate_request(_request_body: Dict) -> str | None:
    """Проверяет наличие токена в теле запроса, возвращает текст ошибки или None."""
    try:
        token = None
        if isinstance(_request_body, dict):
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


def _sh_eval(cmd: str) -> subprocess.CompletedProcess:
    """Выполняет через /bin/sh -lc безопасно (для команд уровня shell)."""
    logger.info("Выполняется shell-команда: %s", cmd)
    return subprocess.run(["/bin/sh", "-lc", cmd], capture_output=True, text=True, check=False)


def _discover_reboot_path() -> tuple[str | None, str | None]:
    """Определяет путь к reboot через `command -v reboot`. Возвращает (path, error)."""
    res = _sh_eval("command -v reboot")
    if res.returncode != 0:
        return None, f"command -v reboot failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
    path = (res.stdout or "").strip()
    if not path:
        return None, "reboot not found"
    return path, None


def _move(src: str, dst: str) -> str | None:
    res = _run(["mv", src, dst])
    if res.returncode != 0:
        return f"mv failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
    return None


def _write_stub(path: str) -> str | None:
    """Создает заглушку reboot, которая логирует вызовы и завершаетcя с кодом 0."""
    content = """#!/bin/sh
echo "$(date -Iseconds) reboot called with args: $@" >> /var/log/reboot-intercept.log
exit 0
"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"write stub error: {str(e)}"
    res = _run(["chmod", "+x", path])
    if res.returncode != 0:
        return f"chmod failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
    return None


def _self_check() -> str | None:
    """Вызывает `reboot --help` и ожидает rc=0."""
    res = _run(["reboot", "--help"])
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
    """Проверяет появление маркера вызова в логе заглушки."""
    res = _run(["tail", "-n", "50", INTERCEPT_LOG])
    if res.returncode != 0:
        return f"tail failed: rc={res.returncode}, stderr={(res.stderr or '').strip()}"
    text = res.stdout or ""
    if "reboot called" not in text:
        return "intercept log does not contain expected marker"
    return None


def _restore(reboot_path: str) -> str | None:
    """Восстанавливает исходный бинарь из файла *.real, если он существует."""
    real_path = f"{reboot_path}.real"
    if not os.path.exists(real_path):
        return None
    res = _move(real_path, reboot_path)
    if res is not None:
        return res
    return None


def handle(request_body: Dict) -> Dict[str, str]:
    """
    Выполняет безопасную проверку вызова reboot через подмену бинаря заглушкой.

    Аргументы:
      request_body: тело запроса (ожидается x-access-token)

    Возвращает:
      Dict с ключом result: "OK" | "ERROR" и message при ошибке.
    """
    reboot_path: str | None = None
    try:
        # 0) Валидация токена
        auth_error = _validate_request(request_body)
        if auth_error is not None:
            return {"result": "ERROR", "message": auth_error}

        # 1) Найти путь к reboot
        reboot_path, err = _discover_reboot_path()
        if err is not None:
            return {"result": "ERROR", "message": err}

        # 2) Подмена на заглушку (mv path -> path.real; записать stub на path)
        err = _move(reboot_path, f"{reboot_path}.real")
        if err is not None:
            # Нечего восстанавливать, так как mv не прошел
            return {"result": "ERROR", "message": err}

        err = _write_stub(reboot_path)
        if err is not None:
            # Пытаемся вернуть оригинал
            _restore(reboot_path)
            return {"result": "ERROR", "message": err}

        # 3) Самопроверка заглушки
        err = _self_check()
        if err is not None:
            _restore(reboot_path)
            return {"result": "ERROR", "message": err}

        # 4) Верификация по логу
        err = _verify_intercept_log()
        if err is not None:
            _restore(reboot_path)
            return {"result": "ERROR", "message": err}

        # 5) Восстановление исходного бинаря
        err = _restore(reboot_path)
        if err is not None:
            return {"result": "ERROR", "message": err}

        return {"result": "OK"}

    except Exception as e:
        logger.error("Исключение в manager_reboot.handle: %s", e)
        try:
            if reboot_path:
                _restore(reboot_path)
        except Exception:
            pass
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


