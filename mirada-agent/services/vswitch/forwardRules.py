#!/usr/bin/env python3
"""
Сервис для проверки создания правил перенаправления трафика
"""

import logging
import subprocess
import re
import requests
import json

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"

def normalize_data(data):
    """Нормализует данные запроса, устанавливая значения по умолчанию"""
    normalized = {}
    
    # Проверяем, что есть хотя бы один из srcNets или dstNets
    if ('srcNets' not in data or not data['srcNets']) and ('dstNets' not in data or not data['dstNets']):
        raise ValueError("Должен быть указан хотя бы один из srcNets или dstNets")
    
    # srcNets (опционально)
    if 'srcNets' in data and data['srcNets']:
        normalized['srcNets'] = data['srcNets']
    
    # dstNets (опционально)
    if 'dstNets' in data and data['dstNets']:
        normalized['dstNets'] = data['dstNets']
    
    # srcExclude (опционально)
    if 'srcExclude' in data and data['srcExclude']:
        normalized['srcExclude'] = data['srcExclude']
    
    # dstExclude (опционально)
    if 'dstExclude' in data and data['dstExclude']:
        normalized['dstExclude'] = data['dstExclude']
    
    # action (опционально)
    if 'action' in data and data['action']:
        normalized['action'] = data['action']
    
    # config - по умолчанию httpProxy
    config = data.get('config')
    if config is None or config == "":
        normalized['config'] = "httpProxy"
    else:
        normalized['config'] = str(config)
    
    # description - по умолчанию Forward rule
    description = data.get('description')
    if description is None or description == "":
        normalized['description'] = "Forward rule"
    else:
        normalized['description'] = str(description)
    
    # active - по умолчанию true
    active = data.get('active')
    if active is None:
        normalized['active'] = True
    else:
        normalized['active'] = bool(active)
    
    return normalized

def check_forward_rule_exists(net_data, config_type):
    """Проверяет существование правила перенаправления в iptables"""
    try:
        full_addr = net_data['fullAddr']
        port = net_data['port']
        
        logger.info(f"Проверка существования правила перенаправления: сеть {full_addr}, порт {port}, конфигурация {config_type}")
        
        cmd = [
            "ip", "netns", "exec", NETNS_NAME,
            "iptables", "-t", "nat", "-L", "-n", "-v"
        ]
        
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка получения списка правил NAT:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return False, f"Failed to check iptables NAT rules: {result.stderr}"
        
        # Ищем правило в выводе - ищем строку с нужной сетью и портом
        # Для srcNets: сеть в source колонке, для dstNets: сеть в destination колонке
        # REDIRECT находится в колонке target, поэтому ищем просто сеть и порт
        # Для CIDR адресов экранируем только точки, но не слеш
        # Для /32 адресов iptables может показывать как с /32, так и без него
        escaped_addr = full_addr.replace('.', r'\.')
        
        # Если это /32 адрес, ищем оба варианта: с /32 и без него
        if full_addr.endswith('/32'):
            base_ip = full_addr[:-3].replace('.', r'\.')  # Убираем /32 и экранируем точки
            pattern = rf".*({escaped_addr}|{base_ip}).*dpt:{port}"
        else:
            pattern = rf".*{escaped_addr}.*dpt:{port}"
        
        logger.info(f"Ищем паттерн: {pattern}")
        logger.info(f"Полный вывод iptables:")
        logger.info(result.stdout)
        
        lines = result.stdout.split('\n')
        matching_lines = [line for line in lines if re.search(pattern, line)]
        
        logger.info(f"Найдено совпадающих строк: {len(matching_lines)}")
        if matching_lines:
            for line in matching_lines:
                logger.info(f"  - {line.strip()}")
        else:
            logger.info("  (правил не найдено)")
            # Дополнительная диагностика - показываем все правила REDIRECT
            logger.info("Дополнительная диагностика - все правила REDIRECT:")
            for line in lines:
                if "REDIRECT" in line and "dpt:" in line:
                    logger.info(f"  Найдено правило: {line.strip()}")
            
            # Ищем по отдельности сеть и порт
            logger.info(f"Поиск сети '{full_addr}':")
            net_found = False
            search_variants = [full_addr]
            
            # Для /32 адресов добавляем вариант без /32
            if full_addr.endswith('/32'):
                base_ip = full_addr[:-3]
                search_variants.append(base_ip)
                logger.info(f"  Также ищем вариант без /32: '{base_ip}'")
            
            for variant in search_variants:
                for line in lines:
                    if variant in line:
                        logger.info(f"  Найдена строка с сетью '{variant}': {line.strip()}")
                        net_found = True
                        break
                if net_found:
                    break
                    
            if not net_found:
                logger.info("  Сеть не найдена ни в одном из вариантов")
                
            logger.info(f"Поиск порта 'dpt:{port}':")
            port_found = False
            for line in lines:
                if f"dpt:{port}" in line:
                    logger.info(f"  Найдена строка с портом: {line.strip()}")
                    port_found = True
            if not port_found:
                logger.info("  Порт не найден")
        
        return len(matching_lines) > 0, None
        
    except Exception as e:
        logger.error(f"Ошибка при проверке правила перенаправления: {e}")
        return False, f"Internal error checking forward rule: {str(e)}"

def get_redirect_port(config_type):
    """Определяет порт перенаправления на основе типа конфигурации"""
    redirect_ports = {
        'httpProxy': '3128',
        'httpsProxy': '3129', 
        'tlsProxy': '9444',
        'tls': '9443'
    }
    return redirect_ports.get(config_type, '3128')

def remove_forward_rule(net_data, config_type, net_type="src"):
    """Удаляет правило перенаправления из iptables"""
    try:
        full_addr = net_data['fullAddr']
        port = net_data['port']
        
        logger.info(f"Удаление правила перенаправления: сеть {full_addr}, порт {port}, конфигурация {config_type}")
        
        # Сначала находим цепочку, содержащую правило
        # Для /32 адресов учитываем, что iptables может показывать IP без /32
        if full_addr.endswith('/32'):
            base_ip = full_addr[:-3]
            escaped_full = re.escape(full_addr)
            escaped_base = re.escape(base_ip)
            search_pattern = f".*({escaped_full}|{escaped_base}).*dpt:{port}"
        else:
            search_pattern = f".*{re.escape(full_addr)}.*dpt:{port}"
            
        cmd = [
            "ip", "netns", "exec", NETNS_NAME, "bash", "-c",
            f"iptables -t nat -L -n -v | grep '{search_pattern}' | grep -o 'N[^ ]*' | head -1"
        ]
        
        logger.info(f"Выполняем команду поиска цепочки: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0 or not result.stdout.strip():
            logger.error(f"Не удалось найти цепочку для удаления:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stdout: {result.stdout}")
            logger.error(f"  - stderr: {result.stderr}")
            return False, f"Failed to find chain for removal: {result.stderr}"
        
        chain = result.stdout.strip()
        logger.info(f"Найдена цепочка: {chain}")
        
        # Проверяем, сколько правил в цепочке
        cmd = [
            "ip", "netns", "exec", NETNS_NAME, "bash", "-c",
            f"iptables -t nat -L {chain} -n -v | grep -c REDIRECT"
        ]
        
        logger.info(f"Выполняем команду подсчета правил: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка подсчета правил:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            return False, f"Failed to count rules: {result.stderr}"
        
        rule_count = int(result.stdout.strip())
        logger.info(f"Количество правил в цепочке: {rule_count}")
        
        if rule_count == 1:
            # Если только одно правило, удаляем всю цепочку
            logger.info("Удаляем всю цепочку (только одно правило)")
            
            # Удаляем правило из PREROUTING
            cmd = [
                "ip", "netns", "exec", NETNS_NAME,
                "iptables", "-t", "nat", "-D", "PREROUTING", "-j", chain
            ]
            
            logger.info(f"Выполняем команду удаления из PREROUTING: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.error(f"Ошибка удаления из PREROUTING:")
                logger.error(f"  - returncode: {result.returncode}")
                logger.error(f"  - stderr: {result.stderr}")
                return False, f"Failed to remove from PREROUTING: {result.stderr}"
            
            # Очищаем цепочку
            cmd = [
                "ip", "netns", "exec", NETNS_NAME,
                "iptables", "-t", "nat", "-F", chain
            ]
            
            logger.info(f"Выполняем команду очистки цепочки: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.error(f"Ошибка очистки цепочки:")
                logger.error(f"  - returncode: {result.returncode}")
                logger.error(f"  - stderr: {result.stderr}")
                return False, f"Failed to flush chain: {result.stderr}"
            
            # Удаляем цепочку
            cmd = [
                "ip", "netns", "exec", NETNS_NAME,
                "iptables", "-t", "nat", "-X", chain
            ]
            
            logger.info(f"Выполняем команду удаления цепочки: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.error(f"Ошибка удаления цепочки:")
                logger.error(f"  - returncode: {result.returncode}")
                logger.error(f"  - stderr: {result.stderr}")
                return False, f"Failed to delete chain: {result.stderr}"
        else:
            # Если несколько правил, удаляем конкретное правило по тому же паттерну, что и ищем
            logger.info("Удаляем только конкретное правило из цепочки")
            
            # Находим и удаляем правило в один шаг, используя тот же паттерн что и при поиске
            # Ищем строку с нужным правилом и удаляем ее по номеру строки
            cmd_delete = [
                "ip", "netns", "exec", NETNS_NAME, "bash", "-c",
                f"""
                # Получаем номер строки правила (используем тот же паттерн поиска)
                LINE_NUM=$(iptables -t nat -L {chain} -n -v --line-numbers | grep '{search_pattern}' | head -1 | awk '{{print $1}}')
                if [ -n "$LINE_NUM" ]; then
                    echo "Удаляем правило номер $LINE_NUM"
                    iptables -t nat -D {chain} $LINE_NUM
                    echo "Правило удалено"
                else
                    echo "Правило не найдено"
                    exit 1
                fi
                """
            ]
            
            logger.info(f"Выполняем команду удаления правила: удаляем правило с паттерном {full_addr}:dpt:{port}")
            result = subprocess.run(cmd_delete, capture_output=True, text=True, check=False)
            
            logger.info(f"Вывод команды удаления:")
            if result.stdout:
                logger.info(f"  stdout: {result.stdout}")
            if result.stderr:
                logger.info(f"  stderr: {result.stderr}")
            
            if result.returncode != 0:
                logger.error(f"Ошибка удаления правила:")
                logger.error(f"  - returncode: {result.returncode}")
                logger.error(f"  - stderr: {result.stderr}")
                return False, f"Failed to remove rule: {result.stderr}"
        
        # Проверяем, что правило действительно удалено
        logger.info("Проверяем, что правило удалено")
        rule_exists_after, error_msg = check_forward_rule_exists(net_data, config_type)
        if error_msg:
            logger.warning(f"Ошибка при проверке удаления правила: {error_msg}")
        elif rule_exists_after:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Правило все еще существует после попытки удаления!")
            logger.error(f"Проверяем детали:")
            # Дополнительная диагностика
            cmd_diag = [
                "ip", "netns", "exec", NETNS_NAME,
                "iptables", "-t", "nat", "-L", "-n", "-v"
            ]
            diag_result = subprocess.run(cmd_diag, capture_output=True, text=True, check=False)
            logger.error(f"Текущее состояние iptables NAT:")
            for line in diag_result.stdout.split('\n'):
                if full_addr in line and f"dpt:{port}" in line:
                    logger.error(f"  НАЙДЕНО ПРАВИЛО: {line.strip()}")
            return False, "Rule still exists after deletion attempt"
        else:
            logger.info("✓ Правило успешно удалено и больше не существует")
        
        logger.info("Правило перенаправления успешно удалено")
        return True, None
        
    except Exception as e:
        logger.error(f"Ошибка при удалении правила перенаправления: {e}")
        return False, f"Internal error removing forward rule: {str(e)}"

def handle(data):
    """Обработчик для проверки создания правил перенаправления трафика"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ СОЗДАНИЯ ПРАВИЛА ПЕРЕНАПРАВЛЕНИЯ ===")
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Отсутствуют данные запроса"}
        
        # Нормализуем данные запроса
        try:
            normalized_data = normalize_data(data)
        except ValueError as e:
            logger.error(f"Ошибка валидации данных: {e}")
            return {"result": "ERROR", "message": str(e)}
        
        logger.info(f"Нормализованные параметры:")
        if 'srcNets' in normalized_data:
            logger.info(f"  - srcNets: {normalized_data['srcNets']}")
        if 'dstNets' in normalized_data:
            logger.info(f"  - dstNets: {normalized_data['dstNets']}")
        if 'srcExclude' in normalized_data:
            logger.info(f"  - srcExclude: {normalized_data['srcExclude']}")
        if 'dstExclude' in normalized_data:
            logger.info(f"  - dstExclude: {normalized_data['dstExclude']}")
        if 'action' in normalized_data:
            logger.info(f"  - action: {normalized_data['action']}")
        logger.info(f"  - config: {normalized_data['config']}")
        logger.info(f"  - description: {normalized_data['description']}")
        logger.info(f"  - active: {normalized_data['active']}")
        
        # Алгоритм проверки согласно требованиям
        logger.info("=== АЛГОРИТМ ПРОВЕРКИ ===")
        
        config_type = normalized_data['config']
        
        # Проверяем, есть ли сети для проверки
        has_networks = bool(('srcNets' in normalized_data and normalized_data['srcNets']) or \
                           ('dstNets' in normalized_data and normalized_data['dstNets']))
        
        if not has_networks:
            logger.info("=== СПЕЦИАЛЬНЫЙ СЛУЧАЙ: ПРАВИЛО БЕЗ СЕТЕЙ ===")
            logger.info("Правило создано без srcNets и dstNets - это валидный случай")
            logger.info("Не ожидается создание REDIRECT правил в iptables")
            logger.info("Пропускаем проверку iptables и сразу переходим к очистке")
            # Переходим сразу к очистке через API, минуя проверку iptables
        else:
            # Сначала проверяем все правила
            logger.info("=== ШАГ 1: ПРОВЕРКА ВСЕХ ПРАВИЛ ===")
            
            missing_rules = []  # Список не найденных правил
            
            # Обрабатываем srcNets (если есть)
            if 'srcNets' in normalized_data:
                for src_net_data in normalized_data['srcNets']:
                    if not isinstance(src_net_data, dict):
                        logger.error(f"Неверный формат данных сети: {src_net_data}")
                        return {"result": "ERROR", "message": f"Invalid srcNet format: {src_net_data}"}
                    
                    full_addr = src_net_data.get('fullAddr')
                    port = src_net_data.get('port')
                    
                    if not full_addr:
                        logger.error("Отсутствует fullAddr в srcNet")
                        return {"result": "ERROR", "message": "Missing fullAddr in srcNet"}
                    
                    if port is None:
                        logger.error("Отсутствует port в srcNet")
                        return {"result": "ERROR", "message": "Missing port in srcNet"}
                    
                    try:
                        port = int(port)
                    except (ValueError, TypeError):
                        logger.error(f"Неверный формат порта: {port}")
                        return {"result": "ERROR", "message": f"Invalid port format: {port}"}
                    
                    logger.info(f"Проверка srcNet: {full_addr}, порт: {port}")
                    
                    # Проверяем, что правило появилось
                    rule_exists, error_msg = check_forward_rule_exists(src_net_data, config_type)
                    if error_msg:
                        logger.error(f"Ошибка при проверке правила: {error_msg}")
                        return {"result": "ERROR", "message": error_msg}
                    
                    if not rule_exists:
                        logger.error(f"Правило перенаправления не найдено для srcNet {full_addr}:{port}")
                        missing_rules.append(f"srcNet {full_addr}:{port}")
                    else:
                        logger.info(f"✓ Правило найдено для srcNet {full_addr}:{port}")
        
            # Обрабатываем dstNets (если есть)
            if 'dstNets' in normalized_data:
                for dst_net_data in normalized_data['dstNets']:
                    if not isinstance(dst_net_data, dict):
                        logger.error(f"Неверный формат данных сети: {dst_net_data}")
                        return {"result": "ERROR", "message": f"Invalid dstNet format: {dst_net_data}"}
                    
                    full_addr = dst_net_data.get('fullAddr')
                    port = dst_net_data.get('port')
                    
                    if not full_addr:
                        logger.error("Отсутствует fullAddr в dstNet")
                        return {"result": "ERROR", "message": "Missing fullAddr in dstNet"}
                    
                    if port is None:
                        logger.error("Отсутствует port в dstNet")
                        return {"result": "ERROR", "message": "Missing port in dstNet"}
                    
                    try:
                        port = int(port)
                    except (ValueError, TypeError):
                        logger.error(f"Неверный формат порта: {port}")
                        return {"result": "ERROR", "message": f"Invalid port format: {port}"}
                    
                    logger.info(f"Проверка dstNet: {full_addr}, порт: {port}")
                    
                    # Проверяем, что правило появилось
                    rule_exists, error_msg = check_forward_rule_exists(dst_net_data, config_type)
                    if error_msg:
                        logger.error(f"Ошибка при проверке правила: {error_msg}")
                        return {"result": "ERROR", "message": error_msg}
                    
                    if not rule_exists:
                        logger.error(f"Правило перенаправления не найдено для dstNet {full_addr}:{port}")
                        missing_rules.append(f"dstNet {full_addr}:{port}")
                    else:
                        logger.info(f"✓ Правило найдено для dstNet {full_addr}:{port}")
        
            # Если есть не найденные правила, возвращаем ошибку
            if missing_rules:
                error_message = f"Forward rules not found in iptables: {', '.join(missing_rules)}"
                logger.error(error_message)
                return {"result": "ERROR", "message": error_message}
            
            # Удаляем найденные правила через iptables
            logger.info("=== ШАГ 2: УДАЛЕНИЕ НАЙДЕННЫХ ПРАВИЛ ЧЕРЕЗ IPTABLES ===")
        
            # Проверяем и удаляем srcNets (если есть)
            if 'srcNets' in normalized_data:
                for src_net_data in normalized_data['srcNets']:
                    # Проверяем еще раз, что правило существует
                    rule_exists, error_msg = check_forward_rule_exists(src_net_data, config_type)
                    if rule_exists:
                        logger.info(f"Удаление srcNet: {src_net_data['fullAddr']}, порт: {src_net_data['port']}")
                        success, error_msg = remove_forward_rule(src_net_data, config_type, "src")
                        if not success:
                            logger.warning(f"Не удалось удалить правило через iptables: {error_msg}")
                    else:
                        logger.info(f"Пропускаем удаление srcNet {src_net_data['fullAddr']}:{src_net_data['port']} (не найдено в iptables)")
        
            # Проверяем и удаляем dstNets (если есть)
            if 'dstNets' in normalized_data:
                for dst_net_data in normalized_data['dstNets']:
                    # Проверяем еще раз, что правило существует
                    rule_exists, error_msg = check_forward_rule_exists(dst_net_data, config_type)
                    if rule_exists:
                        logger.info(f"Удаление dstNet: {dst_net_data['fullAddr']}, порт: {dst_net_data['port']}")
                        success, error_msg = remove_forward_rule(dst_net_data, config_type, "dst")
                        if not success:
                            logger.warning(f"Не удалось удалить правило через iptables: {error_msg}")
                    else:
                        logger.info(f"Пропускаем удаление dstNet {dst_net_data['fullAddr']}:{dst_net_data['port']} (не найдено в iptables)")
        
        # После успешной проверки удаляем все правила через API
        logger.info("=== ШАГ 3: ОЧИСТКА ПРАВИЛ ЧЕРЕЗ API ===")
        try:
            # Получаем список всех правил
            logger.info("Получаем список всех правил для удаления")
            response = requests.get('http://localhost:7779/api/forwardRules')
            if response.status_code == 200:
                rules = response.json()
                logger.info(f"Найдено правил для удаления: {len(rules)}")
                
                # Удаляем каждое правило
                for rule in rules:
                    rule_id = rule.get('id')
                    if rule_id:
                        logger.info(f"Удаляем правило с ID: {rule_id}")
                        delete_response = requests.delete(
                            f'http://localhost:7779/api/forwardRules/{rule_id}',
                            headers={'Content-Type': 'application/json'}
                        )
                        if delete_response.status_code == 200:
                            result_data = delete_response.json()
                            logger.info(f"  ✓ Правило удалено, count: {result_data.get('count', 'N/A')}")
                        else:
                            logger.warning(f"  ⚠ Ошибка удаления правила {rule_id}: {delete_response.status_code}")
                    else:
                        logger.warning("  ⚠ Правило без ID, пропускаем")
                        
                logger.info("Очистка правил через API завершена")
            else:
                logger.warning(f"Не удалось получить список правил: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Ошибка при очистке правил через API: {e}")
            # Не останавливаем выполнение из-за ошибки очистки
        
        logger.info("=== ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО ===")
        return {"result": "OK"}
        
    except Exception as e:
        logger.error(f"Ошибка при проверке создания правила перенаправления: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

