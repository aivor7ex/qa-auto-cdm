#!/usr/bin/env python3
"""
Утилита для удаления правил iptables в сетевом пространстве имён ngfw
"""

import logging
import subprocess
import threading
import time


logger = logging.getLogger(__name__)


NETNS_NAME = "ngfw"


def _run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды: {' '.join(cmd)}")
            logger.error(f"returncode={result.returncode} stderr={result.stderr}")
            return False, result.stdout, result.stderr
        return True, result.stdout, result.stderr
    except Exception as e:
        logger.error(f"Исключение при выполнении команды {' '.join(cmd)}: {e}")
        return False, "", str(e)


def delete_rule_by_number(table: str, chain: str, rule_number: int) -> bool:
    """
    Удаляет правило по номеру строки в цепочке.

    Аналог: ip netns exec ngfw iptables -t <table> -D <chain> <num>
    """
    if not table or not chain or rule_number is None:
        logger.error("Некорректные параметры для удаления правила")
        return False

    cmd = [
        "ip", "netns", "exec", NETNS_NAME,
        "iptables", "-t", table, "-D", chain, str(rule_number),
    ]
    ok, out, err = _run_cmd(cmd)
    if ok:
        logger.info(f"Удалено правило: table={table} chain={chain} number={rule_number}")
    return ok


def delete_rule_by_spec(table: str, chain: str, rule_spec: list[str]) -> bool:
    """
    Удаляет правило по спецификации (аргументы как для добавления).

    Пример: ["-p", "tcp", "--dport", "80", "-j", "ACCEPT"]
    """
    if not table or not chain or not rule_spec:
        logger.error("Некорректные параметры для удаления по спецификации")
        return False

    cmd = [
        "ip", "netns", "exec", NETNS_NAME,
        "iptables", "-t", table, "-D", chain,
    ] + rule_spec
    ok, out, err = _run_cmd(cmd)
    if ok:
        logger.info(f"Удалено правило по спецификации: table={table} chain={chain} spec={' '.join(rule_spec)}")
    return ok


def delete_all_chain_rules(table: str, chain: str) -> bool:
    """
    Удаляет все правила в цепочке, проходя с конца к началу.
    """
    if not table or not chain:
        logger.error("Некорректные параметры для очистки цепочки")
        return False

    # Получаем количество правил
    list_cmd = [
        "ip", "netns", "exec", NETNS_NAME,
        "iptables", "-t", table, "-L", chain, "--line-numbers",
    ]
    ok, out, err = _run_cmd(list_cmd)
    if not ok:
        return False

    # Считаем максимальный номер правила
    max_num = 0
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            num = int(parts[0])
            if num > max_num:
                max_num = num
        except ValueError:
            continue

    # Удаляем с конца
    success = True
    for num in range(max_num, 0, -1):
        if not delete_rule_by_number(table, chain, num):
            success = False

    return success


def schedule_delete_rule_by_number(table: str, chain: str, rule_number: int, delay_seconds: int = 2) -> None:
    """
    Планирует удаление правила через delay_seconds в отдельном потоке.
    """
    def _delayed():
        try:
            time.sleep(delay_seconds)
            delete_rule_by_number(table, chain, rule_number)
        except Exception as e:
            logger.error(f"Ошибка отложенного удаления правила: {e}")

    threading.Thread(target=_delayed, daemon=True).start()


def schedule_delete_all_chain_rules(table: str, chain: str, delay_seconds: int = 2) -> None:
    """
    Планирует удаление всех правил цепочки через задержку.
    """
    def _delayed():
        try:
            time.sleep(delay_seconds)
            delete_all_chain_rules(table, chain)
        except Exception as e:
            logger.error(f"Ошибка отложенной очистки цепочки: {e}")

    threading.Thread(target=_delayed, daemon=True).start()


