#!/usr/bin/env python3
"""
Утилита для удаления сетевого интерфейса внутри пространства имен ngfw
"""

import logging
import subprocess

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def _execute_command(cmd, description):
    """Выполняет команду и возвращает (ok, stdout, stderr)."""
    try:
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info(f"Команда выполнена успешно: {description}")
            return True, result.stdout.strip(), None
        logger.error(f"Ошибка выполнения команды: {description}")
        logger.error(f"Return code: {result.returncode}")
        logger.error(f"Stderr: {result.stderr}")
        return False, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        logger.error(f"Исключение при выполнении команды ({description}): {e}")
        return False, None, str(e)

def delete_interface(interface_name: str) -> bool:
    """
    Удаляет интерфейс по имени внутри netns ngfw.

    Returns:
        bool: True, если интерфейс успешно удалён; False при ошибке.
    """
    if not interface_name:
        logger.error("Пустое имя интерфейса для удаления")
        return False

    cmd = [
        "ip", "netns", "exec", NETNS_NAME,
        "ip", "link", "delete", "dev", interface_name
    ]
    ok, _out, err = _execute_command(cmd, f"удаление интерфейса {interface_name}")

    if ok:
        logger.info(f"Интерфейс {interface_name} удалён")
        return True

    # Если интерфейс не найден — считаем, что он уже удалён
    if err and ("Cannot find device" in err or "No such device" in err):
        logger.warning(f"Интерфейс {interface_name} уже отсутствует")
        return True

    return False


