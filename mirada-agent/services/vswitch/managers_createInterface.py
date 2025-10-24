#!/usr/bin/env python3
"""
Сервис для проверки создания интерфейсов
"""

import json
import os
import logging
import subprocess
import re

logger = logging.getLogger(__name__)

# Утилиты
from .utils import delete_interface

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
        interface_name = data.get("name", "")
        if not interface_name:
            logger.error("Отсутствует обязательное поле 'name'")
            return None, None
        
        # Конвертируем в строку, если это число
        if not isinstance(interface_name, str):
            interface_name = str(interface_name)
            logger.info(f"Конвертировано имя интерфейса в строку: {interface_name}")
        
        # Извлекаем IP и маску (опционально)
        ip_and_mask = data.get("ipAndMask", "")
        
        logger.info(f"Извлеченные данные интерфейса:")
        logger.info(f"  - name: {interface_name}")
        logger.info(f"  - ipAndMask: {ip_and_mask if ip_and_mask else 'None'}")
        
        return interface_name, ip_and_mask
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных интерфейса: {e}")
        return None, None

def get_network_interfaces():
    """Получает список всех сетевых интерфейсов"""
    try:
        logger.info("Получение списка сетевых интерфейсов")
        
        # Выполняем команду для получения всех интерфейсов
        cmd = ["sudo", "ip", "netns", "exec", NETNS_NAME, "ip", "a"]
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            logger.error(f"  - stdout: {result.stdout}")
            return None
        
        logger.info("Команда выполнена успешно")
        logger.info(f"Вывод команды: {result.stdout[:500]}...")  # Показываем первые 500 символов
        return result.stdout
        
    except Exception as e:
        logger.error(f"Ошибка при получении сетевых интерфейсов: {e}")
        return None

def check_interface_exists(interface_name, interfaces_output):
    """Проверяет существование интерфейса в выводе команды"""
    try:
        logger.info(f"Проверка существования интерфейса: {interface_name}")
        
        if not interfaces_output:
            logger.warning("Вывод команды пуст")
            return False
        
        # Ищем интерфейс в выводе команды
        # Формат вывода: "1: dummy0: <BROADCAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000"
        # Также может быть: "9: 12345: <BROADCAST,NOARP,UP,LOWER_UP> mtu 1500 qdisc noqueue state UNKNOWN group default qlen 1000"
        
        # Более гибкий паттерн, который учитывает возможные пробелы
        pattern = rf"\d+:\s*{re.escape(interface_name)}:"
        logger.info(f"Ищем интерфейс с паттерном: {pattern}")
        match = re.search(pattern, interfaces_output)
        
        if match:
            logger.info(f"Интерфейс {interface_name} найден")
            return True
        else:
            logger.warning(f"Интерфейс {interface_name} не найден")
            logger.info(f"Полный вывод команды для отладки:")
            for line in interfaces_output.split('\n'):
                if interface_name in line:
                    logger.info(f"  Найдена строка с интерфейсом: {line}")
            return False
        
    except Exception as e:
        logger.error(f"Ошибка при проверке существования интерфейса: {e}")
        return False

def handle(data):
    """Обработчик для проверки создания интерфейсов"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ СОЗДАНИЯ ИНТЕРФЕЙСА ===")
        
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Empty request data"}
        
        # Извлекаем данные интерфейса из запроса
        interface_name, ip_and_mask = extract_interface_data(data)
        if not interface_name:
            logger.error("Не удалось извлечь данные интерфейса из запроса")
            return {"result": "ERROR", "message": "Failed to extract interface data from request"}
        
        logger.info(f"Извлеченные данные интерфейса: {interface_name} (тип: {type(interface_name)})")
        
        # Получаем список всех интерфейсов
        interfaces_output = get_network_interfaces()
        if not interfaces_output:
            logger.error("Не удалось получить список интерфейсов")
            return {"result": "ERROR", "message": "Failed to get network interfaces list"}
        
        # Проверяем существование интерфейса
        interface_exists = check_interface_exists(interface_name, interfaces_output)
        
        if interface_exists:
            logger.info("Интерфейс создан успешно")
            # Удаляем интерфейс после успешной проверки
            logger.info(f"Пробуем удалить интерфейс {interface_name}")
            deleted = delete_interface(interface_name)
            if deleted:
                logger.info("Интерфейс удалён успешно")
                return {"result": "OK", "message": "Interface found and deleted"}
            else:
                logger.error("Не удалось удалить интерфейс")
                # По требованию: возвращаем OK даже если удаление не удалось
                return {"result": "OK", "message": "Interface found; deletion failed"}
        else:
            logger.warning("Интерфейс не найден")
            logger.info("Возвращаем результат: {'result': 'ERROR', 'message': 'Interface not found'}")
            return {"result": "ERROR", "message": "Interface not found"}
            
    except Exception as e:
        logger.error(f"Ошибка при проверке создания интерфейса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        logger.info("Возвращаем результат: {'result': 'ERROR', 'message': 'Internal error'}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"} 