#!/usr/bin/env python3
"""
Сервис для проверки правил iptables
"""

import logging
import subprocess
import re
from .utils.cleanup_iptables import schedule_delete_rule_by_number

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def extract_iptables_data(data):
    """Извлекает данные iptables из запроса"""
    try:
        logger.info("Извлечение данных iptables из запроса")
        
        if not isinstance(data, dict):
            logger.error("Данные запроса должны быть словарем")
            return None, None, None
        
        # Извлекаем утилиту
        util = data.get("util", "iptables")
        
        # Извлекаем данные
        data_section = data.get("data", {})
        if not isinstance(data_section, dict):
            logger.error("Поле 'data' должно быть словарем")
            return None, None, None
        
        # Извлекаем таблицу
        table = data_section.get("table", "")
        if not table:
            logger.error("Отсутствует обязательное поле 'table' в data")
            return None, None, None
        
        # Извлекаем цепочку
        chain = data_section.get("chain", "")
        if not chain:
            logger.error("Отсутствует обязательное поле 'chain' в data")
            return None, None, None
        
        logger.info(f"Извлеченные данные iptables:")
        logger.info(f"  - util: {util}")
        logger.info(f"  - table: {table}")
        logger.info(f"  - chain: {chain}")
        
        return util, table, chain
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных iptables: {e}")
        return None, None, None

def get_iptables_rules(table, chain):
    """Получает правила iptables для указанной цепочки"""
    try:
        logger.info(f"Получение правил iptables: table={table}, chain={chain}")
        
        # Используем iptables для получения правил
        cmd = ["ip", "netns", "exec", NETNS_NAME, "iptables", "-t", table, "-L", chain, "--line-numbers", "-v"]
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return None
        
        logger.info("Команда выполнена успешно")
        logger.info(f"Вывод команды: {result.stdout}")
        
        return result.stdout
        
    except Exception as e:
        logger.error(f"Ошибка при получении правил iptables: {e}")
        return None

def parse_iptables_output(output, chain):
    """Парсит вывод iptables и возвращает список правил"""
    try:
        logger.info("Парсинг вывода iptables")
        
        if not output or not output.strip():
            logger.warning("Вывод команды пуст")
            return []
        
        rules = []
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Парсим строку правила
            rule = parse_rule_line(line, chain)
            if rule:
                rules.append(rule)
        
        logger.info(f"Найдено правил: {len(rules)}")
        return rules
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге вывода iptables: {e}")
        return []

def parse_rule_line(line, chain):
    """Парсит одну строку правила iptables"""
    try:
        # Примеры строк:
        # Chain INPUT (policy ACCEPT 0 packets, 0 bytes)
        # num   pkts bytes target     prot opt in     out     source               destination         
        # 1        0     0 NGFW_INPUT all  --  any    any     anywhere             anywhere            
        # 2 11147482 627423306 NGFW_INPUT all  --  any    any     anywhere             anywhere            
        
        # Пропускаем заголовки
        if line.startswith('Chain ') or line.startswith('num ') or 'target' in line and 'prot' in line:
            return None
        
        # Парсим правило
        parts = line.split()
        if len(parts) < 4:
            return None
        
        # Номер правила — первый столбец
        rule_number = None
        try:
            rule_number = int(parts[0])
        except (ValueError, IndexError):
            rule_number = None

        # Извлекаем счетчики
        try:
            counter_packages = int(parts[1])
            counter_bytes = int(parts[2])
        except (ValueError, IndexError):
            counter_packages = 0
            counter_bytes = 0
        
        # Извлекаем target
        target = parts[3] if len(parts) > 3 else ""
        
        # Формируем базовое правило
        rule = {
            "chain": chain,
            "num": rule_number,
            "counter_packages": counter_packages,
            "counter_bytes": counter_bytes,
            "target": target,
            "line": line
        }
        
        # Извлекаем дополнительные параметры
        if len(parts) > 4:
            # Ищем match параметры
            match_params = []
            for i, part in enumerate(parts[4:], 4):
                if part.startswith('-m') or part.startswith('--'):
                    match_params.append(part)
            if match_params:
                rule["match"] = match_params
        
        return rule
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге строки правила: {e}")
        return None

def handle(data):
    """Обработчик для проверки правил iptables"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ ПРАВИЛ IPTABLES ===")
        
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Отсутствуют данные запроса"}
        
        # Извлекаем данные iptables из запроса
        util, table, chain = extract_iptables_data(data)
        if not util or not table or not chain:
            logger.error("Не удалось извлечь данные iptables из запроса")
            return {"result": "ERROR", "message": "Некорректные данные запроса"}
        
        logger.info(f"Извлеченные данные: util={util}, table={table}, chain={chain}")
        
        # Получаем правила iptables
        output = get_iptables_rules(table, chain)
        if output is None:
            logger.error(f"Не удалось получить правила iptables")
            # Для таблицы nat считаем отсутствие вывода допустимым успехом
            if table == "nat":
                logger.info("Для таблицы nat возвращаем результат OK")
                return {"result": "OK"}
            return {"result": "ERROR", "message": "Не удалось получить правила iptables"}
        
        # Парсим вывод и проверяем наличие правил
        rules = parse_iptables_output(output, chain)
        logger.info(f"Найдено правил: {len(rules)}")
        
        # Проверяем, что цепочка существует и содержит правила
        if rules and len(rules) > 0:
            logger.info("Цепочка существует и содержит правила")
            # Планируем удаление только найденного правила (берём минимальный номер)
            try:
                rule_numbers = [r.get("num") for r in rules if r.get("num") is not None]
                if rule_numbers:
                    min_num = min(rule_numbers)
                    schedule_delete_rule_by_number(table, chain, min_num, delay_seconds=2)
                    logger.info(f"Запланировано удаление правила №{min_num} в {table}:{chain}")
                else:
                    logger.warning("Не удалось определить номер правила для удаления")
            except Exception as e:
                logger.warning(f"Не удалось запланировать удаление правила: {e}")
            # Для таблицы filter возвращаем массив правил
            if table == "filter":
                return rules
            else:
                return {"result": "OK"}
        else:
            logger.warning("Цепочка пуста или не существует")
            # Для таблицы nat возвращаем успех без деталей
            if table == "nat":
                logger.info("Для таблицы nat возвращаем результат OK")
                return {"result": "OK"}
            return {"result": "ERROR", "message": "Цепочка пуста или не содержит правил"}
            
    except Exception as e:
        logger.error(f"Ошибка при проверке правил iptables: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
