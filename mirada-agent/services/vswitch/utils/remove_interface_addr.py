#!/usr/bin/env python3
"""
Утилита для удаления IP адреса из интерфейса
"""

import logging
import subprocess
import ipaddress

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def execute_command(cmd, description):
    """Выполняет команду и возвращает результат"""
    try:
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info(f"Команда выполнена успешно: {description}")
            return {"res": result.stdout.strip(), "error": None}
        else:
            logger.error(f"Ошибка выполнения команды: {description}")
            logger.error(f"Return code: {result.returncode}")
            logger.error(f"Stderr: {result.stderr}")
            return {"res": None, "error": result.stderr.strip() or f"Command failed with return code {result.returncode}"}
            
    except Exception as e:
        logger.error(f"Исключение при выполнении команды: {e}")
        return {"res": None, "error": str(e)}

def validate_ip_address(address):
    """Валидация IP адреса"""
    try:
        _ = ipaddress.ip_interface(address)
        return True
    except ValueError:
        logger.error(f"Некорректный формат IP адреса с маской: {address}")
        return False

def check_interface_exists(interface_name):
    """Проверяет существование интерфейса"""
    try:
        logger.info(f"Проверка существования интерфейса {interface_name}")
        
        cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "link", "show", interface_name]
        result = execute_command(cmd, "проверка существования интерфейса")
        
        if result["error"]:
            logger.error(f"Интерфейс {interface_name} не существует")
            return False
        
        logger.info(f"Интерфейс {interface_name} существует")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке существования интерфейса: {e}")
        return False

def check_interface_address_exists(interface_name, address):
    """Проверяет, что IP адрес существует на интерфейсе"""
    try:
        logger.info(f"Проверка наличия IP адреса {address} на интерфейсе {interface_name}")
        
        cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "addr", "show", interface_name]
        result = execute_command(cmd, "проверка IP адресов интерфейса")
        
        if result["error"]:
            logger.error(f"Ошибка при проверке IP адреса: {result['error']}")
            return False
        
        output = result["res"]
        logger.debug(f"Вывод команды ip addr show: {output}")
        
        # Проверяем наличие ожидаемого IP адреса
        if address in output:
            logger.info(f"IP адрес {address} найден на интерфейсе {interface_name}")
            return True
        else:
            logger.warning(f"IP адрес {address} не найден на интерфейсе {interface_name}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке IP адреса интерфейса: {e}")
        return False

def remove_interface_address(interface_name, address):
    """Удаляет IP адрес из интерфейса"""
    try:
        logger.info(f"Удаление IP адреса {address} из интерфейса {interface_name}")
        
        # Команда для удаления IP адреса
        cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "addr", "del", address, "dev", interface_name]
        result = execute_command(cmd, "удаление IP адреса из интерфейса")
        
        if result["error"]:
            # Проверяем, не является ли ошибка связанной с тем, что адрес уже отсутствует
            if "Cannot assign requested address" in result["error"] or "No such device" in result["error"]:
                logger.warning(f"IP адрес {address} уже отсутствует на интерфейсе {interface_name}")
                return True
            else:
                logger.error(f"Ошибка при удалении IP адреса: {result['error']}")
                return False
        
        logger.info(f"IP адрес {address} успешно удален из интерфейса {interface_name}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при удалении IP адреса: {e}")
        return False

def get_interface_addresses(interface_name):
    """Получает список всех IP адресов интерфейса"""
    try:
        logger.info(f"Получение списка IP адресов интерфейса {interface_name}")
        
        cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "addr", "show", interface_name]
        result = execute_command(cmd, "получение IP адресов интерфейса")
        
        if result["error"]:
            logger.error(f"Ошибка при получении IP адресов: {result['error']}")
            return []
        
        output = result["res"]
        addresses = []
        
        # Парсим вывод для извлечения IP адресов
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('inet ') or line.startswith('inet6 '):
                # Извлекаем IP адрес с маской
                parts = line.split()
                if len(parts) >= 2:
                    ip_with_mask = parts[1]
                    addresses.append(ip_with_mask)
        
        logger.info(f"Найдено IP адресов на интерфейсе {interface_name}: {addresses}")
        return addresses
        
    except Exception as e:
        logger.error(f"Ошибка при получении IP адресов интерфейса: {e}")
        return []

def remove_interface_addr_handler(data):
    """Основной обработчик для удаления IP адреса из интерфейса"""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА УДАЛЕНИЯ IP АДРЕСА ===")
        logger.info(f"Полученные данные: {data}")
        
        # Проверяем формат данных
        if not isinstance(data, dict):
            logger.error("Данные запроса должны быть словарем")
            return {"result": "ERROR", "message": "Неверный формат данных запроса"}
        
        # Извлекаем поля
        interface_name = data.get("interface", "")
        address = data.get("address", "")
        
        # Проверяем наличие обязательных полей
        if not interface_name:
            logger.error("Отсутствует обязательное поле 'interface'")
            return {"result": "ERROR", "message": "Отсутствует обязательное поле 'interface'"}
        
        if not address:
            logger.error("Отсутствует обязательное поле 'address'")
            return {"result": "ERROR", "message": "Отсутствует обязательное поле 'address'"}
        
        # Валидация IP адреса
        if not validate_ip_address(address):
            return {"result": "ERROR", "message": f"Некорректный формат IP адреса: {address}"}
        
        # Проверяем существование интерфейса
        if not check_interface_exists(interface_name):
            return {"result": "ERROR", "message": f"Интерфейс {interface_name} не существует"}
        
        # Проверяем, существует ли IP адрес на интерфейсе
        if not check_interface_address_exists(interface_name, address):
            logger.info(f"IP адрес {address} уже отсутствует на интерфейсе {interface_name}")
            return {"result": "OK", "message": f"IP адрес {address} отсутствует на интерфейсе {interface_name}"}
        
        # Удаляем IP адрес
        if remove_interface_address(interface_name, address):
            # Проверяем результат удаления
            if not check_interface_address_exists(interface_name, address):
                logger.info(f"IP адрес {address} успешно удален из интерфейса {interface_name}")
                return {"result": "OK", "message": f"IP адрес {address} успешно удален из интерфейса {interface_name}"}
            else:
                logger.error(f"IP адрес {address} не был удален из интерфейса {interface_name}")
                return {"result": "ERROR", "message": "IP адрес не был удален из интерфейса"}
        else:
            logger.error(f"Не удалось удалить IP адрес {address} из интерфейса {interface_name}")
            return {"result": "ERROR", "message": "Не удалось удалить IP адрес из интерфейса"}
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса удаления IP адреса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Внутренняя ошибка: {str(e)}"}

def remove_all_interface_addresses(interface_name, exclude_addresses=None):
    """Удаляет все IP адреса с интерфейса, кроме исключенных"""
    try:
        logger.info(f"Удаление всех IP адресов с интерфейса {interface_name}")
        
        if exclude_addresses is None:
            exclude_addresses = []
        
        # Получаем все адреса интерфейса
        addresses = get_interface_addresses(interface_name)
        
        if not addresses:
            logger.info(f"На интерфейсе {interface_name} нет IP адресов")
            return {"result": "OK", "message": "На интерфейсе нет IP адресов"}
        
        removed_addresses = []
        failed_addresses = []
        
        for address in addresses:
            # Пропускаем исключенные адреса
            if address in exclude_addresses:
                logger.info(f"Пропускаем исключенный адрес: {address}")
                continue
            
            # Удаляем адрес
            if remove_interface_address(interface_name, address):
                removed_addresses.append(address)
            else:
                failed_addresses.append(address)
        
        if failed_addresses:
            logger.error(f"Не удалось удалить адреса: {failed_addresses}")
            return {
                "result": "PARTIAL", 
                "message": f"Удалены: {removed_addresses}, Ошибки: {failed_addresses}",
                "removed": removed_addresses,
                "failed": failed_addresses
            }
        else:
            logger.info(f"Все IP адреса успешно удалены: {removed_addresses}")
            return {
                "result": "OK", 
                "message": f"Все IP адреса успешно удалены: {removed_addresses}",
                "removed": removed_addresses
            }
            
    except Exception as e:
        logger.error(f"Ошибка при удалении всех IP адресов: {e}")
        return {"result": "ERROR", "message": f"Внутренняя ошибка: {str(e)}"}
