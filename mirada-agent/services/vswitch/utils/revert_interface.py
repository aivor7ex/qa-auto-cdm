#!/usr/bin/env python3
"""
Утилита для реверса настроек сетевого интерфейса внутри пространства имен ngfw

Идея реверса:
- Если в запросе был установлен IP (не "0"), удаляем этот IP из интерфейса
- Если в запросе был удалён IP ("0"), откат невозможен без исходных данных — пропускаем
- Если задавался MTU, возвращаем MTU к 1500
- Broadcast сбрасывать отдельно не требуется — удаление адреса снимает привязанный broadcast
"""

import logging
import subprocess
from typing import Dict, Tuple


logger = logging.getLogger(__name__)


NETNS_NAME = "ngfw"


def _run_cmd(cmd: list[str]) -> Tuple[bool, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return False, result.stdout.strip(), result.stderr.strip()
        return True, result.stdout.strip(), ""
    except Exception as e:
        return False, "", str(e)


def _delete_ip_address(interface: str, cidr: str) -> bool:
    if not cidr:
        return True
    cmd = [
        "ip", "netns", "exec", NETNS_NAME,
        "ip", "addr", "del", cidr, "dev", interface,
    ]
    ok, out, err = _run_cmd(cmd)
    if not ok and ("Cannot find device" in err or "No such device" in err):
        # Нечего удалять — считаем успешно
        return True
    if not ok and ("Cannot assign requested address" in err or "RTNETLINK answers: Cannot assign requested address" in err):
        # Такого адреса нет — уже откатили
        return True
    if not ok:
        logger.error(f"Ошибка удаления IP {cidr} с {interface}: {err}")
    return ok


def _set_mtu(interface: str, mtu: int) -> bool:
    mtu_value = 1500
    cmd = [
        "ip", "netns", "exec", NETNS_NAME,
        "ifconfig", interface, "mtu", str(mtu_value), "up",
    ]
    ok, out, err = _run_cmd(cmd)
    if not ok:
        logger.error(f"Ошибка установки MTU {mtu_value} на {interface}: {err}")
    return ok


def revert_interface_changes(request_data: Dict) -> Dict:
    """
    Отменяет изменения интерфейса согласно данным исходного запроса.

    Args:
        request_data: словарь с полями interface, ip, mtu, broadcast, mac

    Returns:
        {"result": "OK"} или {"result": "ERROR", "message": str}
    """
    try:
        interface = (request_data or {}).get("interface")
        if not interface:
            return {"result": "ERROR", "message": "Не указано имя интерфейса"}

        ip_cidr = (request_data or {}).get("ip")
        mtu = (request_data or {}).get("mtu")

        # 1) Откат IP
        if ip_cidr and ip_cidr != "0":
            if not _delete_ip_address(interface, ip_cidr):
                return {"result": "ERROR", "message": f"Не удалось удалить IP {ip_cidr}"}
        # Если ip == "0" — исходный IP неизвестен, пропускаем

        # 2) Откат MTU (если передавался) к 1500
        if mtu is not None and mtu != "":
            if not _set_mtu(interface, 1500):
                return {"result": "ERROR", "message": "Не удалось восстановить MTU 1500"}

        return {"result": "OK"}
    except Exception as e:
        logger.error(f"Ошибка реверса настроек интерфейса: {e}")
        return {"result": "ERROR", "message": str(e)}


