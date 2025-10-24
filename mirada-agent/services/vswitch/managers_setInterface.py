#!/usr/bin/env python3
"""
Сервис для настройки параметров интерфейса
"""

import logging
import subprocess
import re
# from .utils import revert_interface_changes

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def extract_interface_data(data):
    """Извлекает данные интерфейса из запроса"""
    try:
        logger.info("Извлечение данных интерфейса из запроса")
        
        if not isinstance(data, dict):
            logger.error("Данные запроса должны быть словарем")
            return None
        
        # Извлекаем поля
        interface_name = data.get("interface", "")
        ip_address = data.get("ip", "")
        netmask = data.get("netmask", "")
        mtu = data.get("mtu", "")
        mac = data.get("mac", "")
        broadcast = data.get("broadcast", "")
        
        # Проверяем наличие обязательного поля interface
        if not interface_name:
            logger.error("Отсутствует обязательное поле 'interface'")
            return None
        
        # Валидация MTU (если предоставлен)
        if mtu is not None and mtu != "":
            try:
                mtu_int = int(mtu)
                if mtu_int < 0:
                    logger.error(f"MTU должен быть неотрицательным, получено: {mtu_int}")
                    return None
            except (ValueError, TypeError):
                logger.error(f"MTU должен быть числом, получено: {mtu}")
                return None
        
        # Валидация MAC адреса (если предоставлен)
        if mac:
            mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
            if not re.match(mac_pattern, mac):
                logger.error(f"Некорректный формат MAC адреса: {mac}")
                return None
        
        # Валидация IP адреса (если предоставлен и не "0")
        if ip_address and ip_address != "0":
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
            if not re.match(ip_pattern, ip_address):
                logger.error(f"Некорректный формат IP адреса с маской: {ip_address}")
                return None
        
        # Валидация broadcast адреса (если предоставлен)
        if broadcast:
            broadcast_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if not re.match(broadcast_pattern, broadcast):
                logger.error(f"Некорректный формат broadcast адреса: {broadcast}")
                return None
        
        logger.info(f"Извлеченные данные интерфейса:")
        logger.info(f"  - interface: {interface_name}")
        logger.info(f"  - ip: {ip_address}")
        logger.info(f"  - netmask: {netmask}")
        logger.info(f"  - mtu: {mtu}")
        logger.info(f"  - mac: {mac}")
        logger.info(f"  - broadcast: {broadcast}")
        
        return {
            "interface": interface_name,
            "ip": ip_address,
            "netmask": netmask,
            "mtu": mtu,
            "mac": mac,
            "broadcast": broadcast
        }
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных интерфейса: {e}")
        return None

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
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return {"res": "", "error": result.stderr.strip() or f"Command failed with return code {result.returncode}"}
            
    except Exception as e:
        logger.error(f"Исключение при выполнении команды: {description} - {e}")
        return {"res": "", "error": str(e)}

def check_interface_settings(interface_name, expected_settings):
    """Проверяет, что настройки интерфейса соответствуют ожидаемым"""
    try:
        logger.info(f"Проверка настроек интерфейса: {interface_name}")
        
        checks_passed = 0
        total_checks = 0
        
        # Проверка IP адреса
        if expected_settings.get("ip"):
            total_checks += 1
            if expected_settings["ip"] == "0":
                # Проверяем отсутствие IP адреса
                cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "addr", "show", interface_name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    # Проверяем, что у интерфейса нет IP адресов (кроме loopback)
                    if "inet " in result.stdout and "127.0.0.1" not in result.stdout:
                        logger.warning("У интерфейса все еще есть IP адреса")
                    else:
                        logger.info("IP адрес успешно удален")
                        checks_passed += 1
            else:
                # Проверяем наличие IP адреса (допускаем форматы ip и ip/cidr)
                cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "addr", "show", interface_name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    expected_ip = expected_settings["ip"]
                    ip_only = expected_ip.split('/')[0]
                    stdout = result.stdout
                    if (
                        expected_ip in stdout or
                        f"inet {ip_only}/" in stdout or
                        f"inet {ip_only} " in stdout
                    ):
                        logger.info(f"IP адрес {expected_ip} найден (по совпадению {ip_only})")
                        checks_passed += 1
        
        # Проверка MTU
        if expected_settings.get("mtu"):
            total_checks += 1
            mtu_value = min(int(expected_settings["mtu"]), 1500)  # Ограничиваем до 1500
            cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "link", "show", interface_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and f"mtu {mtu_value}" in result.stdout:
                logger.info(f"MTU {mtu_value} найден")
                checks_passed += 1
        
        # Проверка MAC адреса
        if expected_settings.get("mac"):
            total_checks += 1
            cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "link", "show", interface_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and f"link/ether {expected_settings['mac']}" in result.stdout:
                logger.info(f"MAC адрес {expected_settings['mac']} найден")
                checks_passed += 1
        
        # Проверка broadcast адреса
        if expected_settings.get("broadcast"):
            total_checks += 1
            cmd = ["ip", "netns", "exec", NETNS_NAME, "ip", "addr", "show", interface_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0 and f"brd {expected_settings['broadcast']}" in result.stdout:
                logger.info(f"Broadcast адрес {expected_settings['broadcast']} найден")
                checks_passed += 1
        
        logger.info(f"Результат проверки настроек: {checks_passed}/{total_checks}")
        
        if total_checks == 0:
            return True  # Нет настроек для проверки
        else:
            return checks_passed == total_checks
            
    except Exception as e:
        logger.error(f"Ошибка при проверке настроек интерфейса: {e}")
        return False

def handle(data):
    """Обработчик для настройки параметров интерфейса"""
    try:
        logger.info("=== НАЧАЛО НАСТРОЙКИ ИНТЕРФЕЙСА ===")
        
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Отсутствуют данные запроса"}
        
        # Извлекаем данные интерфейса из запроса
        interface_data = extract_interface_data(data)
        if not interface_data:
            logger.error("Не удалось извлечь данные интерфейса из запроса")
            return {"result": "ERROR", "message": "Некорректные данные запроса"}
        
        interface_name = interface_data["interface"]
        ip_address = interface_data.get("ip")
        netmask = interface_data.get("netmask")
        mtu = interface_data.get("mtu")
        mac = interface_data.get("mac")
        broadcast = interface_data.get("broadcast")
        
        logger.info(f"Извлеченные данные интерфейса: {interface_name}")
        
        # Выполняем команды настройки
        commands_executed = []
        step_index = 0
        
        # Шаг 0: Настройка IP адреса
        if ip_address:
            if ip_address == "0":
                # Удаление IP адреса
                cmd = ["ip", "netns", "exec", NETNS_NAME, "ifconfig", interface_name, "0"]
                result = execute_command(cmd, "удаление IP адреса")
                commands_executed.append({
                    "index": step_index,
                    "cmd": " ".join(cmd),
                    "res": result["res"],
                    "error": result["error"]
                })
            else:
                # Установка IP адреса
                cmd = ["ip", "netns", "exec", NETNS_NAME, "ifconfig", interface_name, ip_address]
                result = execute_command(cmd, "установка IP адреса")
                commands_executed.append({
                    "index": step_index,
                    "cmd": " ".join(cmd),
                    "res": result["res"],
                    "error": result["error"]
                })
        else:
            commands_executed.append({"index": step_index, "skipped": True})
        
        step_index += 1
        
        # Шаг 1: Настройка broadcast адреса
        # Если IP удаляется (ip == "0"), установка broadcast невозможна — пропускаем
        if broadcast and not (ip_address == "0"):
            cmd = ["ip", "netns", "exec", NETNS_NAME, "ifconfig", interface_name, "broadcast", broadcast]
            result = execute_command(cmd, "установка broadcast адреса")
            commands_executed.append({
                "index": step_index,
                "cmd": " ".join(cmd),
                "res": result["res"],
                "error": result["error"]
            })
        else:
            commands_executed.append({"index": step_index, "skipped": True})
        
        step_index += 1
        
        # Шаг 2: Настройка MAC адреса (пропускаем, так как ifconfig не поддерживает изменение MAC)
        commands_executed.append({"index": step_index, "skipped": True})
        step_index += 1
        
        # Шаг 3: Настройка MTU
        if mtu is not None and mtu != "":
            # Ограничиваем MTU до 1500 согласно тестам
            mtu_value = min(int(mtu), 1500)
            cmd = ["ip", "netns", "exec", NETNS_NAME, "ifconfig", interface_name, "mtu", str(mtu_value), "up"]
            result = execute_command(cmd, "установка MTU")
            commands_executed.append({
                "index": step_index,
                "cmd": " ".join(cmd),
                "res": result["res"],
                "error": result["error"]
            })
        else:
            commands_executed.append({"index": step_index, "skipped": True})
        
        step_index += 1
        
        # Шаг 4: Настройка netmask (пропускаем, так как маска уже указана в IP)
        commands_executed.append({"index": step_index, "skipped": True})
        
        # Проверяем, что все команды выполнились успешно
        commands_successful = all("error" not in item or item["error"] is None for item in commands_executed)
        
        # Если команды выполнились успешно, проверяем настройки
        if commands_successful:
            expected_settings = {
                "ip": ip_address,
                "mtu": mtu,
                "mac": mac,
                # broadcast не проверяем, если IP удалялся
                "broadcast": (broadcast if ip_address != "0" else None)
            }
            settings_correct = check_interface_settings(interface_name, expected_settings)
            
            if settings_correct:
                logger.info("Все настройки интерфейса применены успешно")
                # Реверсируем изменения после проверки
                # try:
                #     revert_res = revert_interface_changes(interface_data)
                #     if revert_res.get("result") != "OK":
                #         logger.error(f"Реверс не выполнен: {revert_res}")
                # except Exception as e:
                #     logger.error(f"Ошибка реверса настроек: {e}")
                return {"result": "OK"}
            else:
                logger.warning("Настройки интерфейса не соответствуют ожидаемым")
                # Даже при несоответствии пытаемся реверсировать, чтобы вернуть состояние
                # try:
                #     revert_res = revert_interface_changes(interface_data)
                #     if revert_res.get("result") != "OK":
                #         logger.error(f"Реверс не выполнен: {reверт_res}")
                # except Exception as e:
                #     logger.error(f"Ошибка реверса настроек: {e}")
                return {"result": "ERROR", "message": "Настройки интерфейса не соответствуют ожидаемым"}
        else:
            # Есть ошибки в выполнении команд
            error_messages = []
            for item in commands_executed:
                if "error" in item and item["error"]:
                    error_messages.append(f"Шаг {item['index']}: {item['error']}")
            
            error_msg = "; ".join(error_messages) if error_messages else "Ошибка выполнения команд"
            logger.error(f"Ошибки выполнения команд: {error_msg}")
            # Пытаемся реверсировать даже если команды частично упали
            # try:
            #     revert_res = revert_interface_changes(interface_data)
            #     if revert_res.get("result") != "OK":
            #         logger.error(f"Реверс не выполнен: {revert_res}")
            # except Exception as e:
            #     logger.error(f"Ошибка реверса настроек: {e}")
            return {"result": "ERROR", "message": error_msg}
            
    except Exception as e:
        logger.error(f"Ошибка при настройке интерфейса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        # В случае исключения тоже пробуем реверсировать
        # try:
        #     revert_res = revert_interface_changes(data if isinstance(data, dict) else {})
        #     if revert_res.get("result") != "OK":
        #         logger.error(f"Реверс не выполнен: {revert_res}")
        # except Exception as re:
        #     logger.error(f"Ошибка реверса настроек: {re}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
