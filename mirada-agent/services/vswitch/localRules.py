#!/usr/bin/env python3
"""
Сервис для проверки создания правил локального файрвола
"""

import logging
import subprocess
import re

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def normalize_data(data):
    """Нормализует данные запроса, устанавливая значения по умолчанию"""
    normalized = {}
    
    # Порт обязателен
    normalized['port'] = int(data.get('port', 8080))
    
    # Интерфейс - по умолчанию eth0
    interface = data.get('interface')
    if interface is None or interface == "":
        normalized['interface'] = "eth0"
    else:
        normalized['interface'] = str(interface)
    
    # Тип - по умолчанию default
    rule_type = data.get('type')
    if rule_type is None or rule_type == "":
        normalized['type'] = "default"
    else:
        normalized['type'] = str(rule_type)
    
    # Описание - по умолчанию Rule for port {port}
    description = data.get('description')
    if description is None or description == "":
        normalized['description'] = f"Rule for port {normalized['port']}"
    else:
        normalized['description'] = str(description)
    
    return normalized

def check_rule_exists(port, interface):
    """Проверяет существование правила в iptables"""
    try:
        logger.info(f"Проверка существования правила: порт {port}, интерфейс {interface}")
        
        cmd = [
            "ip", "netns", "exec", NETNS_NAME,
            "iptables", "-L", "NGFW_INPUT", "-n", "-v"
        ]
        
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка получения списка правил:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return False, f"Failed to check iptables rules: {result.stderr}"
        
        # Ищем правило в выводе
        # Сначала ищем по конкретному интерфейсу
        pattern = rf"{interface}.*dpt:{port}"
        lines = result.stdout.split('\n')
        matching_lines = [line for line in lines if re.search(pattern, line)]
        
        # Если не найдено, ищем по любому интерфейсу (*) для данного порта
        if not matching_lines:
            pattern = rf"\*.*dpt:{port}"
            matching_lines = [line for line in lines if re.search(pattern, line)]
        
        logger.info(f"Найдено совпадающих строк: {len(matching_lines)}")
        for line in matching_lines:
            logger.info(f"  - {line.strip()}")
        
        return len(matching_lines) > 0, None
        
    except Exception as e:
        logger.error(f"Ошибка при проверке правила: {e}")
        return False, f"Internal error checking rule: {str(e)}"

def count_rule_duplicates(port, interface):
    """Подсчитывает количество дублирующих правил"""
    try:
        logger.info(f"Подсчет дубликатов правила: порт {port}, интерфейс {interface}")
        
        cmd = [
            "ip", "netns", "exec", NETNS_NAME, "bash", "-c",
            f"iptables -L NGFW_INPUT -n -v | grep -E '({interface}|\\*).*dpt:{port}' | wc -l"
        ]
        
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка подсчета дубликатов:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return 0, f"Failed to count rule duplicates: {result.stderr}"
        
        try:
            count = int(result.stdout.strip())
            logger.info(f"Количество дубликатов: {count}")
            return count, None
        except ValueError:
            logger.error(f"Некорректный вывод команды подсчета: '{result.stdout}'")
            return 0, f"Invalid count output: {result.stdout}"
        
    except Exception as e:
        logger.error(f"Ошибка при подсчете дубликатов: {e}")
        return 0, f"Internal error counting duplicates: {str(e)}"

def remove_iptables_rule(port, interface):
    """Удаляет правило iptables"""
    try:
        logger.info(f"Удаление правила iptables: порт {port}, интерфейс {interface}")
        
        # Сначала пытаемся удалить правило с конкретным интерфейсом
        cmd = [
            "ip", "netns", "exec", NETNS_NAME,
            "iptables", "-D", "NGFW_INPUT",
            "-p", "tcp", "-i", interface,
            "--dport", str(port), "-j", "ACCEPT"
        ]
        
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info("Правило успешно удалено")
            return True, None
        
        # Если не удалось удалить с конкретным интерфейсом, 
        # пытаемся удалить правило с любым интерфейсом (*)
        logger.info("Попытка удаления правила с любым интерфейсом")
        cmd = [
            "ip", "netns", "exec", NETNS_NAME,
            "iptables", "-D", "NGFW_INPUT",
            "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"
        ]
        
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info("Правило успешно удалено")
            return True, None
        
        logger.error(f"Ошибка удаления правила:")
        logger.error(f"  - returncode: {result.returncode}")
        logger.error(f"  - stderr: {result.stderr}")
        return False, f"Failed to remove iptables rule: {result.stderr}"
        
    except Exception as e:
        logger.error(f"Ошибка при удалении правила iptables: {e}")
        return False, f"Internal error removing rule: {str(e)}"

def handle(data):
    """Обработчик для проверки создания правил локального файрвола"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ СОЗДАНИЯ ПРАВИЛА ЛОКАЛЬНОГО ФАЙРВОЛА ===")
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Отсутствуют данные запроса"}
        
        # Нормализуем данные запроса
        normalized_data = normalize_data(data)
        
        logger.info(f"Нормализованные параметры:")
        logger.info(f"  - port: {normalized_data['port']}")
        logger.info(f"  - interface: {normalized_data['interface']}")
        logger.info(f"  - type: {normalized_data['type']}")
        logger.info(f"  - description: {normalized_data['description']}")
        
        validated_port = normalized_data['port']
        validated_interface = normalized_data['interface']
        validated_type = normalized_data['type']
        validated_description = normalized_data['description']
        
        # Алгоритм проверки согласно требованиям
        logger.info("=== АЛГОРИТМ ПРОВЕРКИ ===")
        
        # Шаг 1: Проверяем, что правило появилось
        logger.info("Шаг 1: Проверка появления правила")
        rule_exists, error_msg = check_rule_exists(validated_port, validated_interface)
        if error_msg:
            logger.error(f"Ошибка при проверке правила: {error_msg}")
            return {"result": "ERROR", "message": error_msg}
        
        if not rule_exists:
            logger.error("Правило не найдено")
            return {"result": "ERROR", "message": "Rule not found"}
        
        # Шаг 2: Проверяем количество дубликатов
        logger.info("Шаг 2: Проверка дубликатов")
        duplicate_count, error_msg = count_rule_duplicates(validated_port, validated_interface)
        if error_msg:
            logger.error(f"Ошибка при подсчете дубликатов: {error_msg}")
            return {"result": "ERROR", "message": error_msg}
        
        if duplicate_count != 1:
            logger.error(f"Неожиданное количество дубликатов: {duplicate_count}")
            return {"result": "ERROR", "message": f"Unexpected duplicate count: {duplicate_count}"}
        
        # Шаг 3: Удаляем правило
        logger.info("Шаг 3: Удаление правила")
        success, error_msg = remove_iptables_rule(validated_port, validated_interface)
        if not success:
            logger.error(f"Не удалось удалить правило: {error_msg}")
            return {"result": "ERROR", "message": error_msg}
        
        logger.info("=== ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО ===")
        return {"result": "OK"}
        
    except Exception as e:
        logger.error(f"Ошибка при проверке создания правила локального файрвола: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
