#!/usr/bin/env python3
"""
Сервис для проверки создания объекта
"""

import json
import sqlite3
import subprocess
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

def handle(data):
    """Обработчик для проверки создания объекта"""
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ ОБЪЕКТА ===")
        
        # Извлекаем данные из запроса
        name = data.get("name")
        obj_type = data.get("type")
        contents = data.get("contents")
        
        # Маппинг типов: строковые типы -> числовые типы в базе данных
        type_mapping = {
            "ip": "2",
            "svc": "1"
        }
        
        # Преобразуем тип в числовой формат для сравнения с базой данных
        db_type_to_find = type_mapping.get(obj_type, obj_type)
        
        logger.info(f"Получены данные запроса:")
        logger.info(f"  - name: {name}")
        logger.info(f"  - type: {obj_type}")
        logger.info(f"  - db_type_to_find: {db_type_to_find}")
        logger.info(f"  - contents: {contents}")
        logger.info(f"  - contents type: {type(contents)}")
        
        if not all([name, obj_type, contents]):
            logger.error("Отсутствуют обязательные поля в запросе")
            logger.error(f"  - name: {name}")
            logger.error(f"  - type: {obj_type}")
            logger.error(f"  - contents: {contents}")
            return {"result": "ERROR", "message": "Missing required fields: name, type, contents"}
        
        # Создаем временный файл для базы данных
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        logger.info(f"Создан временный файл: {temp_db_path}")
        
        try:
            # Копируем базу данных из контейнера
            copy_cmd = ["docker", "cp", "shared.objects:/objects/database", temp_db_path]
            logger.info(f"Выполняем команду: {' '.join(copy_cmd)}")
            
            result = subprocess.run(copy_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Ошибка копирования базы данных:")
                logger.error(f"  - returncode: {result.returncode}")
                logger.error(f"  - stderr: {result.stderr}")
                logger.error(f"  - stdout: {result.stdout}")
                return {"result": "ERROR", "message": "Failed to copy database from container"}
            
            logger.info("База данных успешно скопирована из контейнера")
            
            # Подключаемся к SQLite базе данных
            logger.info("Подключаемся к SQLite базе данных...")
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            
            # Проверяем размер файла базы данных
            import os
            db_size = os.path.getsize(temp_db_path)
            logger.info(f"Размер файла базы данных: {db_size} байт")
            
            # Выполняем запрос к таблице entity
            logger.info("Выполняем запрос: SELECT * FROM entity")
            cursor.execute("SELECT * FROM entity")
            rows = cursor.fetchall()
            
            logger.info(f"Получено {len(rows)} записей из таблицы entity")
            
            # Проверяем структуру первой записи
            if rows:
                first_row = rows[0]
                logger.info(f"Структура первой записи: {len(first_row)} полей")
                logger.info(f"Типы полей: {[type(field) for field in first_row]}")
            
            # Закрываем соединение
            conn.close()
            logger.info("Соединение с базой данных закрыто")
            
            # Проверяем наличие объекта в базе данных
            object_found = False
            checked_count = 0
            
            logger.info("Начинаем поиск объекта в базе данных...")
            
            for i, row in enumerate(rows):
                # Реальная структура: id, None, None, timestamp, name, type, None, contents, type_id, None
                # Индекс 4 - это name, индекс 5 - это type, индекс 7 - это contents
                if len(row) >= 8:
                    db_name = row[4]
                    db_type = row[5]
                    db_contents = row[7]
                    
                    checked_count += 1
                    
                    # Логируем каждую проверяемую запись
                    logger.info(f"Проверяем запись {i+1}: name='{db_name}', type='{db_type}'")
                    
                    # Проверяем совпадение имени и типа
                    if db_name == name and str(db_type) == db_type_to_find:
                        logger.info(f"✓ Найдено совпадение по имени и типу в записи {i+1}")
                        logger.info(f"  - Ищем: name='{name}', type='{obj_type}' (db_type='{db_type_to_find}')")
                        logger.info(f"  - Найдено: name='{db_name}', type='{db_type}'")
                        
                        # Проверяем содержимое (contents)
                        try:
                            # Парсим JSON содержимое из базы данных
                            if isinstance(db_contents, str):
                                db_contents_parsed = json.loads(db_contents)
                                logger.info(f"  - Парсинг JSON содержимого из строки: {db_contents_parsed}")
                            else:
                                db_contents_parsed = db_contents
                                logger.info(f"  - Содержимое уже в нужном формате: {db_contents_parsed}")
                            
                            # Сравниваем содержимое
                            logger.info(f"  - Сравниваем содержимое:")
                            logger.info(f"    Запрошенное: {contents}")
                            logger.info(f"    В базе: {db_contents_parsed}")
                            
                            # Сравниваем как есть (точное совпадение)
                            exact_match = db_contents_parsed == contents
                            logger.info(f"    Точное совпадение: {exact_match}")
                            
                            # Сравниваем без учета порядка (если точное не совпало)
                            if not exact_match:
                                # Сортируем оба массива для сравнения без учета порядка
                                sorted_request = sorted(contents, key=str)
                                sorted_db = sorted(db_contents_parsed, key=str)
                                order_independent_match = sorted_request == sorted_db
                                logger.info(f"    Сравнение без учета порядка: {order_independent_match}")
                                logger.info(f"    Отсортированный запрос: {sorted_request}")
                                logger.info(f"    Отсортированная БД: {sorted_db}")
                            else:
                                order_independent_match = False
                            
                            if exact_match or order_independent_match:
                                object_found = True
                                match_type = "точное" if exact_match else "без учета порядка"
                                logger.info(f"✓ ОБЪЕКТ НАЙДЕН! ({match_type} совпадение)")
                                break
                            else:
                                logger.info("✗ Содержимое не совпадает, продолжаем поиск...")
                                
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Ошибка парсинга содержимого объекта {name} в записи {i+1}: {e}")
                            logger.warning(f"Проблемное содержимое: {db_contents}")
                            continue
                    else:
                        # Логируем причину несовпадения
                        if db_name != name:
                            logger.info(f"  - Имя не совпадает: '{db_name}' != '{name}'")
                        if str(db_type) != db_type_to_find:
                            logger.info(f"  - Тип не совпадает: '{db_type}' != '{db_type_to_find}'")
            
            logger.info(f"Проверено записей: {checked_count}")
            logger.info(f"Найдено совпадений по имени и типу: {sum(1 for i, row in enumerate(rows) if len(row) >= 8 and row[4] == name and str(row[5]) == db_type_to_find)}")
            
            # Возвращаем результат
            if object_found:
                logger.info("=== РЕЗУЛЬТАТ: ОБЪЕКТ НАЙДЕН ===")
                logger.info(f"✓ Успешно найден объект '{name}' типа '{obj_type}'")
                return {"result": "OK"}
            else:
                logger.info("=== РЕЗУЛЬТАТ: ОБЪЕКТ НЕ НАЙДЕН ===")
                logger.info(f"✗ Объект '{name}' типа '{obj_type}' не найден в базе данных")
                return {"result": "ERROR", "message": "Object not found in database"}
                
        finally:
            # Удаляем временный файл
            try:
                os.unlink(temp_db_path)
                logger.info(f"Временный файл {temp_db_path} удален")
            except OSError as e:
                logger.warning(f"Не удалось удалить временный файл {temp_db_path}: {e}")
                
    except Exception as e:
        logger.error(f"Критическая ошибка при проверке объекта: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"} 