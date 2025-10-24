#!/usr/bin/env python3
"""
Сервис для проверки состояния интерфейсов
"""

import logging
import subprocess
import re

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def extract_interface_data(data):
    """Извлекает данные интерфейса из запроса"""
    try:
        logger.info("Извлечение данных интерфейса из запроса")
        
        if not isinstance(data, dict):
            logger.error("Данные запроса должны быть словарем")
            return None, None
        
        # Извлекаем имя интерфейса
        interface_name = data.get("interface", "")
        if not interface_name:
            logger.error("Отсутствует обязательное поле 'interface'")
            return None, None
        
        # Извлекаем желаемое состояние
        desired_state = data.get("state", "")
        if not desired_state:
            logger.error("Отсутствует обязательное поле 'state'")
            return None, None
        
        # Проверяем корректность состояния
        if desired_state not in ["up", "down"]:
            logger.error(f"Некорректное состояние: {desired_state}. Допустимые значения: up, down")
            return None, None
        
        logger.info(f"Извлеченные данные интерфейса:")
        logger.info(f"  - interface: {interface_name}")
        logger.info(f"  - state: {desired_state}")
        
        return interface_name, desired_state
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных интерфейса: {e}")
        return None, None

def check_interface_state(interface_name):
    """Проверяет текущее состояние интерфейса"""
    try:
        logger.info(f"Проверка состояния интерфейса: {interface_name}")
        
        # Выполняем команду для проверки состояния интерфейса
        cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "link", "show", interface_name]
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return None
        
        logger.info("Команда выполнена успешно")
        logger.info(f"Вывод команды: {result.stdout}")
        
        # Проверяем состояние интерфейса
        # Используем grep для определения состояния, как в требовании
        grep_cmd = ["grep", "-q", "state UP"]
        grep_result = subprocess.run(grep_cmd, input=result.stdout, text=True, capture_output=True, check=False)
        
        if grep_result.returncode == 0:
            current_state = "up"
        else:
            # Проверяем, есть ли состояние "UNKNOWN"
            if "state UNKNOWN" in result.stdout:
                current_state = "unknown"
            else:
                current_state = "down"
        
        logger.info(f"Результат grep команды: returncode={grep_result.returncode}")
        logger.info(f"Текущее состояние интерфейса {interface_name}: {current_state}")
        return current_state
        
    except Exception as e:
        logger.error(f"Ошибка при проверке состояния интерфейса: {e}")
        return None

def handle(data):
    """Обработчик для проверки состояния интерфейсов"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ СОСТОЯНИЯ ИНТЕРФЕЙСА ===")
        
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Отсутствуют данные запроса"}
        
        # Извлекаем данные интерфейса из запроса
        interface_name, desired_state = extract_interface_data(data)
        if not interface_name or not desired_state:
            logger.error("Не удалось извлечь данные интерфейса из запроса")
            return {"result": "ERROR", "message": "Некорректные данные запроса"}
        
        logger.info(f"Извлеченные данные интерфейса: {interface_name}, желаемое состояние: {desired_state}")
        
        # Проверяем текущее состояние интерфейса
        current_state = check_interface_state(interface_name)
        if current_state is None:
            logger.error(f"Не удалось определить состояние интерфейса {interface_name}")
            return {"result": "ERROR", "message": f"Не удалось определить состояние интерфейса {interface_name}"}
        
        # Сравниваем желаемое и текущее состояние
        # Состояние "unknown" считается как успешный результат
        if current_state == desired_state or current_state == "unknown":
            logger.info(f"Интерфейс {interface_name} находится в желаемом состоянии или unknown: {current_state}")
            logger.info("Возвращаем результат: {'result': 'OK'}")
            return {"result": "OK"}
        else:
            logger.warning(f"Интерфейс {interface_name} не соответствует желаемому состоянию")
            logger.warning(f"Желаемое: {desired_state}, текущее: {current_state}")
            logger.info("Возвращаем результат: {'result': 'ERROR', 'message': '...'}")
            return {"result": "ERROR", "message": "Интерфейс не соответствует заявленному состоянию."}
            
    except Exception as e:
        logger.error(f"Ошибка при проверке состояния интерфейса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        logger.info("Возвращаем результат: {'result': 'ERROR', 'message': 'Internal error'}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
