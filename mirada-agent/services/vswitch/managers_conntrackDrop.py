#!/usr/bin/env python3
"""
Сервис для удаления записей conntrack по фильтрам в namespace ngfw
"""

import logging
import subprocess
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

# Допустимые протоколы для conntrack
ALLOWED_PROTOCOLS = {"tcp", "udp", "icmp"}


def _is_valid_host(value: str) -> bool:
    """Простая валидация значений адресов/хостов для CLI (числа, буквы, точка, двоеточие, дефис)."""
    if not isinstance(value, str):
        return False
    return re.match(r"^[0-9A-Za-z\.:\-]+$", value) is not None


def _is_valid_port(value: Any) -> bool:
    """Проверка порта."""
    try:
        port = int(value)
        return 1 <= port <= 65535
    except Exception:
        return False


def _build_conntrack_filters(data: Dict[str, Any]) -> List[str]:
    """Формирует список аргументов conntrack по предоставленным фильтрам."""
    filters: List[str] = []

    protocol = (data.get("protocol") or "").lower()
    if protocol:
        if protocol not in ALLOWED_PROTOCOLS:
            raise ValueError(f"Unsupported protocol: {protocol}")
        filters += ["-p", protocol]

    src = data.get("src")
    if src:
        if not _is_valid_host(src):
            raise ValueError("Invalid src")
        filters += ["-s", src]

    dst = data.get("dst")
    if dst:
        if not _is_valid_host(dst):
            raise ValueError("Invalid dst")
        filters += ["-d", dst]

    sport = data.get("sport")
    if sport is not None:
        if not _is_valid_port(sport):
            raise ValueError("Invalid sport")
        filters += ["--sport", str(int(sport))]

    dport = data.get("dport")
    if dport is not None:
        if not _is_valid_port(dport):
            raise ValueError("Invalid dport")
        filters += ["--dport", str(int(dport))]

    return filters


def _run_conntrack_delete(filters: List[str]) -> Dict[str, Any]:
    """Выполняет команду удаления conntrack и возвращает результат."""
    base_cmd = ["ip", "netns", "exec", NETNS_NAME, "conntrack", "-D"]
    cmd = base_cmd + filters
    logger.info(f"Выполняем команду: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "index": 0,
        "cmd": " ".join(cmd),
        "res": (result.stdout or ""),
        "error": (result.stderr or ""),
    }


def handle(data: Dict[str, Any]):
    """Обработчик удаления записей conntrack.

    Ожидаемые поля (все опциональны, но должен быть задан хотя бы один фильтр):
      - protocol: tcp|udp|icmp
      - src: источник
      - dst: назначение
      - sport: порт источника
      - dport: порт назначения

    Возвращает массив с объектом результата: [{cmd, stdout, stderr, returncode}].
    """
    try:
        logger.info("=== НАЧАЛО УДАЛЕНИЯ ЗАПИСЕЙ CONNTRACK ===")
        logger.info(f"Получены данные запроса: {data}")

        if not isinstance(data, dict):
            logger.error("Некорректный формат запроса: ожидался JSON объект")
            return [{
                "cmd": "",
                "stdout": "",
                "stderr": "invalid request format",
                "returncode": 2,
            }]

        # Формируем фильтры; исключаем выполнение без фильтров
        filters = _build_conntrack_filters(data)
        if not filters:
            logger.error("Отказ от выполнения без фильтров для предотвращения массового удаления")
            return [{
                "index": 0,
                "cmd": "",
                "res": "",
                "error": "at least one filter is required",
            }]

        result = _run_conntrack_delete(filters)
        return [result]

    except ValueError as ve:
        logger.error(f"Ошибка валидации параметров: {ve}")
        return [{
            "index": 0,
            "cmd": "",
            "res": "",
            "error": str(ve),
        }]
    except Exception as e:
        logger.error(f"Внутренняя ошибка при удалении conntrack: {e}")
        return [{
            "index": 0,
            "cmd": "",
            "res": "",
            "error": str(e),
        }]


