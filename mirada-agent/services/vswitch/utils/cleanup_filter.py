#!/usr/bin/env python3
"""
Утилита для удаления правил фильтрации из базы данных
"""

import sqlite3
import logging
import threading
import time

logger = logging.getLogger(__name__)

def delete_filter_rules_async(found_rule_ids, delay_seconds=2):
    """
    Асинхронно удаляет правила фильтрации с задержкой
    
    Args:
        found_rule_ids (list): Список ID найденных правил для удаления
        delay_seconds (int): Задержка перед удалением в секундах
    """
    def delayed_cleanup():
        try:
            logger.info(f"Запуск отложенной очистки правил через {delay_seconds} секунд...")
            time.sleep(delay_seconds)
            
            if not found_rule_ids:
                logger.warning("Нет правил для удаления")
                return
            
            result = delete_filter_rules(found_rule_ids)
            if result:
                logger.info(f"Успешно удалено {len(found_rule_ids)} правил фильтрации")
            else:
                logger.error("Ошибка при удалении правил фильтрации")
                
        except Exception as e:
            logger.error(f"Ошибка в отложенной очистке правил: {e}")
    
    # Запускаем очистку в отдельном потоке
    cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info(f"Запущена отложенная очистка {len(found_rule_ids)} правил через {delay_seconds} секунд")

def delete_filter_rules(rule_ids):
    """
    Удаляет правила фильтрации по их ID из базы данных
    
    Args:
        rule_ids (list): Список ID правил для удаления
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    if not rule_ids:
        logger.warning("Пустой список ID правил для удаления")
        return False
    
    db_path = "/opt/cdm-data/objects/database"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем строку с placeholders для IN условия
        placeholders = ','.join('?' * len(rule_ids))
        
        # SQL-запрос для удаления правил
        query = f"""
        DELETE FROM external 
        WHERE id IN ({placeholders})
        """
        
        logger.info(f"Выполнение запроса удаления для {len(rule_ids)} правил")
        logger.debug(f"SQL запрос: {query}")
        logger.debug(f"Параметры: {rule_ids}")
        
        cursor.execute(query, rule_ids)
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Удалено {deleted_count} правил из БД")
        
        if deleted_count > 0:
            return True
        else:
            logger.warning("Не удалось удалить правила (возможно, они уже отсутствуют)")
            return False
            
    except sqlite3.Error as e:
        logger.error(f"Ошибка SQLite при удалении правил: {e}")
        return False
    except Exception as e:
        logger.error(f"Общая ошибка при удалении правил: {e}")
        return False

def get_rule_details(rule_ids):
    """
    Получает детали правил перед удалением для логирования
    
    Args:
        rule_ids (list): Список ID правил
    
    Returns:
        list: Список кортежей (id, contents) или пустой список при ошибке
    """
    if not rule_ids:
        return []
    
    db_path = "/opt/cdm-data/objects/database"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Создаем строку с placeholders для IN условия
        placeholders = ','.join('?' * len(rule_ids))
        
        query = f"""
        SELECT id, substr(contents, 1, 200)
        FROM external 
        WHERE id IN ({placeholders})
        """
        
        cursor.execute(query, rule_ids)
        rows = cursor.fetchall()
        
        conn.close()
        
        return rows
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка SQLite при получении деталей правил: {e}")
        return []
    except Exception as e:
        logger.error(f"Общая ошибка при получении деталей правил: {e}")
        return []
