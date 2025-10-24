#!/usr/bin/env python3
"""
Сервис для обработки правил фильтрации
"""

import json
import sqlite3
import logging
from .utils.cleanup_filter import delete_filter_rules_async, get_rule_details

logger = logging.getLogger(__name__)

def handle(data):
    """Обработчик для проверки наличия правил фильтрации в БД"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ ФИЛЬТРА ===")
        
        # Извлекаем данные из запроса
        overwrite = data.get("overwrite", False)
        filter_data = data.get("data", [])
        
        logger.info(f"Получены данные запроса:")
        logger.info(f"  - overwrite: {overwrite}")
        logger.info(f"  - data: {filter_data}")
        
        if not filter_data:
            logger.warning("Пустой список правил фильтрации")
            return {"result": "ERROR", "message": "Empty filter rules list"}
        
        # Проверяем каждое правило в БД и собираем ID найденных правил
        found_rule_ids = []
        for rule in filter_data:
            rule_ids = check_rule_exists(rule)
            if rule_ids:
                found_rule_ids.extend(rule_ids)
                logger.info(f"Правило найдено в БД, ID: {rule_ids}")
        
        if found_rule_ids:
            logger.info(f"Найдено {len(found_rule_ids)} правил фильтрации в БД")
            
            # Получаем детали правил для логирования перед удалением
            rule_details = get_rule_details(found_rule_ids)
            if rule_details:
                logger.info("Детали найденных правил перед удалением:")
                for rule_id, content in rule_details:
                    logger.info(f"  - ID {rule_id}: {content[:100]}...")
            
            # Запускаем асинхронное удаление с задержкой в 2 секунды
            delete_filter_rules_async(found_rule_ids, delay_seconds=2)
            
            return {"result": "OK", "found_rules_count": len(found_rule_ids)}
        else:
            logger.warning("Правила не найдены в БД")
            return {"result": "ERROR", "message": "Filter rules not found in database"}
            
    except Exception as e:
        logger.error(f"Ошибка при проверке фильтра: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

def check_rule_exists(rule):
    """Проверяет наличие правила фильтрации в базе данных и возвращает список ID найденных правил"""
    try:
        # Извлекаем ключевые параметры из правила
        source_ips = []
        dest_ips = []
        dest_ports = []
        
        # Ищем source IPs
        if "source" in rule and isinstance(rule["source"], list) and len(rule["source"]) > 1:
            for i in range(1, len(rule["source"])):
                source_item = rule["source"][i]
                if isinstance(source_item, str):
                    if "/" in source_item:
                        source_ips.append(source_item.split("/")[0])
                    else:
                        source_ips.append(source_item)
        
        # Ищем destination IPs
        if "destination" in rule and isinstance(rule["destination"], list) and len(rule["destination"]) > 1:
            for i in range(1, len(rule["destination"])):
                dest_item = rule["destination"][i]
                if isinstance(dest_item, str):
                    if "/" in dest_item:
                        dest_ips.append(dest_item.split("/")[0])
                    else:
                        dest_ips.append(dest_item)
        
        # Ищем destination ports
        if "service" in rule and isinstance(rule["service"], list) and len(rule["service"]) > 1:
            service_config = rule["service"][1]
            if isinstance(service_config, dict):
                if "destination_ports" in service_config:
                    ports = service_config["destination_ports"]
                    if isinstance(ports, list):
                        for port in ports:
                            if isinstance(port, (int, str)):
                                dest_ports.append(str(port))
                            elif isinstance(port, list) and len(port) > 2 and port[0] == "range":
                                # Обработка диапазона портов
                                start_port = port[1]
                                end_port = port[2]
                                dest_ports.append(f"{start_port}-{end_port}")
        
        logger.info(f"Ищем правило с параметрами:")
        logger.info(f"  - source_ips: {source_ips}")
        logger.info(f"  - dest_ips: {dest_ips}")
        logger.info(f"  - dest_ports: {dest_ports}")
        
        if not source_ips or not dest_ips:
            logger.warning("Не удалось извлечь source_ips или dest_ips из правила")
            return []
        
        # Подключаемся к SQLite базе данных
        db_path = "/opt/cdm-data/objects/database"
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # SQL-запрос для поиска правила
            # Строим условия для поиска
            conditions = []
            params = []
            
            # Добавляем условия для source IPs
            for source_ip in source_ips:
                conditions.append("contents LIKE ?")
                params.append(f"%{source_ip}%")
            
            # Добавляем условия для destination IPs
            for dest_ip in dest_ips:
                conditions.append("contents LIKE ?")
                params.append(f"%{dest_ip}%")
            
            # Добавляем условия для destination ports
            for dest_port in dest_ports:
                conditions.append("contents LIKE ?")
                params.append(f"%{dest_port}%")
            
            # Строим SQL запрос
            if conditions:
                query = f"""
                SELECT id, substr(contents, 1, 300)
                FROM external
                WHERE {' AND '.join(conditions)}
                """
                cursor.execute(query, params)
            else:
                # Если нет условий, возвращаем пустой результат
                return []
            
            rows = cursor.fetchall()
            
            conn.close()
            
            if rows:
                rule_ids = [row[0] for row in rows]
                logger.info(f"Найдено {len(rows)} правил в БД")
                for row in rows:
                    logger.info(f"  - ID: {row[0]}")
                    logger.info(f"  - Contents (первые 300 символов): {row[1]}")
                return rule_ids
            else:
                logger.warning("Правило не найдено в БД")
                return []
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка SQLite при проверке правила: {e}")
            return []
            
    except Exception as e:
        logger.error(f"Ошибка при проверке правила: {e}")
        return [] 