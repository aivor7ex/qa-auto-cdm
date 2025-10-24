#!/usr/bin/env python3
"""
Сервис для проверки генерации сертификатов
"""

import json
import os
import logging
import subprocess
import tempfile
import shutil
import re
import threading
import time

logger = logging.getLogger(__name__)

# Константы для контейнера ngfw.vswitch
CONTAINER_NAME = "ngfw.vswitch"
CONTAINER_CERT_DIR = "/storage/cert"

def cleanup_temp_directory(temp_dir):
    """Очищает временную директорию"""
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Временная директория удалена: {temp_dir}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временную директорию {temp_dir}: {e}")

def run_cleanup_certs_delayed():
    """Запускает скрипт cleanup_certs.py с задержкой 3 секунды"""
    def delayed_cleanup():
        try:
            logger.info("Ожидание 3 секунды перед запуском cleanup_certs.py")
            time.sleep(3)
            
            cleanup_script_path = os.path.join(os.path.dirname(__file__), "utils", "cleanup_certs.py")
            logger.info(f"Запуск скрипта очистки сертификатов: {cleanup_script_path}")
            
            result = subprocess.run(
                ["python3", cleanup_script_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Скрипт очистки сертификатов выполнен успешно")
                if result.stdout:
                    logger.info(f"Вывод cleanup_certs.py: {result.stdout}")
            else:
                logger.warning(f"Скрипт очистки сертификатов завершился с ошибкой (код {result.returncode})")
                if result.stderr:
                    logger.warning(f"Ошибка cleanup_certs.py: {result.stderr}")
                    
        except Exception as e:
            logger.error(f"Ошибка при запуске скрипта очистки сертификатов: {e}")
    
    # Запускаем в отдельном потоке, чтобы не блокировать основной ответ
    thread = threading.Thread(target=delayed_cleanup, daemon=True)
    thread.start()
    logger.info("Запущена отложенная очистка сертификатов в фоновом режиме")

def run_cleanup_old_certs():
    """Импортирует и запускает функцию cleanup_old_certs из модуля cleanup_certs"""
    def delayed_cleanup_old_certs():
        try:
            logger.info("Ожидание 3 секунды перед запуском cleanup_old_certs")
            time.sleep(3)
            
            # Импортируем функцию cleanup_old_certs из модуля utils.cleanup_certs
            import sys
            utils_path = os.path.join(os.path.dirname(__file__), "utils")
            if utils_path not in sys.path:
                sys.path.append(utils_path)
            
            from utils.cleanup_certs import cleanup_old_certs
            
            logger.info("Запуск функции cleanup_old_certs")
            cleanup_old_certs()
            logger.info("Функция cleanup_old_certs выполнена успешно")
                    
        except Exception as e:
            logger.error(f"Ошибка при запуске функции cleanup_old_certs: {e}")
    
    # Запускаем в отдельном потоке, чтобы не блокировать основной ответ
    thread = threading.Thread(target=delayed_cleanup_old_certs, daemon=True)
    thread.start()
    logger.info("Запущена отложенная очистка старых сертификатов в фоновом режиме")

def extract_certificate_name(data):
    """Извлекает имя сертификата из данных запроса"""
    try:
        logger.info("Извлечение имени сертификата из данных запроса")
        
        if not isinstance(data, list):
            logger.error("Данные запроса должны быть списком")
            return None
        
        # Ищем команды openssl в данных
        for item in data:
            if not isinstance(item, dict):
                continue
                
            cmd = item.get("cmd", "")
            if not cmd:
                continue
            
            # Ищем команду генерации ключа
            if "openssl genrsa" in cmd and "-out" in cmd:
                # Извлекаем путь к файлу ключа
                match = re.search(r'-out\s+([^\s]+)', cmd)
                if match:
                    key_path = match.group(1)
                    # Извлекаем имя файла без расширения
                    key_filename = os.path.basename(key_path)
                    if key_filename.endswith('.key'):
                        cert_name = key_filename[:-4]  # Убираем .key
                        logger.info(f"Найдено имя сертификата: {cert_name}")
                        return cert_name
        
        logger.warning("Не удалось найти команду генерации ключа в данных")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении имени сертификата: {e}")
        return None

def check_openssl_errors(data):
    """Проверяет наличие ошибок в командах openssl"""
    try:
        logger.info("Проверка ошибок в командах openssl")
        
        if not isinstance(data, list):
            logger.warning("Данные не являются списком")
            return False
        
        for i, item in enumerate(data):
            logger.info(f"Проверяем элемент {i}: {item}")
            
            if not isinstance(item, dict):
                logger.warning(f"Элемент {i} не является словарем")
                continue
            
            # Проверяем наличие ошибки в результате
            error = item.get("error", "")
            if error:
                logger.warning(f"Найдена ошибка в команде openssl: {error}")
                logger.info(f"Индекс команды с ошибкой: {item.get('index', 'unknown')}")
                return True
            
            # Проверяем результат команды
            res = item.get("res", "")
            if res and "error" in res.lower():
                logger.warning(f"Найдена ошибка в результате команды: {res}")
                return True
        
        logger.info("Ошибок в командах openssl не найдено")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при проверке ошибок openssl: {e}")
        return False

def copy_certs_from_container():
    """Копирует сертификаты из контейнера ngfw.vswitch во временную директорию"""
    try:
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Создана временная директория: {temp_dir}")
        
        # Копируем директорию сертификатов из контейнера
        copy_cmd = ["docker", "cp", f"{CONTAINER_NAME}:{CONTAINER_CERT_DIR}", temp_dir]
        logger.info(f"Выполняем команду: {' '.join(copy_cmd)}")
        
        result = subprocess.run(copy_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Ошибка копирования сертификатов:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            logger.error(f"  - stdout: {result.stdout}")
            return None
        
        # Путь к скопированной директории
        copied_cert_dir = os.path.join(temp_dir, "cert")
        logger.info(f"Сертификаты скопированы в: {copied_cert_dir}")
        
        return copied_cert_dir
        
    except Exception as e:
        logger.error(f"Ошибка при копировании сертификатов: {e}")
        return None

def check_certificate_exists(cert_name, cert_dir):
    """Проверяет существование сертификата в директории"""
    try:
        if not os.path.exists(cert_dir):
            logger.warning(f"Директория {cert_dir} не существует")
            return False
        
        # Проверяем наличие файлов сертификата
        key_file = f"{cert_name}.key"
        crt_file = f"{cert_name}.crt"
        
        key_path = os.path.join(cert_dir, key_file)
        crt_path = os.path.join(cert_dir, crt_file)
        
        logger.info(f"Проверяем наличие файлов:")
        logger.info(f"  - key_file: {key_path}")
        logger.info(f"  - crt_file: {crt_path}")
        
        key_exists = os.path.exists(key_path)
        crt_exists = os.path.exists(crt_path)
        
        logger.info(f"Результат проверки:")
        logger.info(f"  - key_file exists: {key_exists}")
        logger.info(f"  - crt_file exists: {crt_exists}")
        
        # Проверяем размеры файлов
        if key_exists:
            key_size = os.path.getsize(key_path)
            logger.info(f"  - key_file size: {key_size} bytes")
        
        if crt_exists:
            crt_size = os.path.getsize(crt_path)
            logger.info(f"  - crt_file size: {crt_size} bytes")
        
        # Сертификат считается сгенерированным, если есть хотя бы файл ключа
        if key_exists:
            logger.info("Сертификат найден (есть файл ключа)")
            return True
        else:
            logger.warning("Сертификат не найден (нет файла ключа)")
            return False
        
    except Exception as e:
        logger.error(f"Ошибка при проверке существования сертификата: {e}")
        return False

def handle(data):
    """Обработчик для проверки генерации сертификатов"""
    temp_cert_dir = None
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ ГЕНЕРАЦИИ СЕРТИФИКАТОВ ===")
        
        logger.info(f"Получены данные запроса: {data}")
        
        # Проверяем наличие ошибок в командах openssl
        has_errors = check_openssl_errors(data)
        logger.info(f"Результат проверки ошибок openssl: {has_errors}")
        
        # Извлекаем имя сертификата из данных запроса
        cert_name = extract_certificate_name(data)
        if not cert_name:
            logger.error("Не удалось извлечь имя сертификата из данных запроса")
            return {"result": "ERROR", "message": "Failed to extract certificate name from request data"}
        
        logger.info(f"Извлеченное имя сертификата: {cert_name}")
        
        # Копируем сертификаты из контейнера
        temp_cert_dir = copy_certs_from_container()
        if not temp_cert_dir:
            logger.error("Не удалось скопировать сертификаты из контейнера")
            return {"result": "ERROR", "message": "Failed to copy certificates from container"}
        
        # Проверяем существование сертификата
        cert_exists = check_certificate_exists(cert_name, temp_cert_dir)
        
        # Если сертификат существует, возвращаем "OK" независимо от ошибок openssl
        if cert_exists:
            logger.info("Сертификат найден и сгенерирован")
            logger.info("Возвращаем результат: {'result': 'OK'}")
            return {"result": "OK"}
        else:
            # Если сертификат не существует и есть ошибки openssl, возвращаем "ERROR"
            if has_errors:
                logger.warning("Обнаружены ошибки в командах openssl и сертификат не найден")
                result = {"result": "ERROR", "message": "OpenSSL errors detected and certificate not found"}
                logger.info(f"Возвращаем результат: {result}")
                return result
            else:
                logger.warning("Сертификат не найден")
                logger.info("Возвращаем результат: {'result': 'ERROR', 'message': 'Certificate not found'}")
                return {"result": "ERROR", "message": "Certificate not found"}
        

            
    except Exception as e:
        logger.error(f"Ошибка при проверке генерации сертификатов: {e}")
        logger.info("Возвращаем результат: {'result': 'ERROR', 'message': 'Internal error'}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
    finally:
        # Очищаем временную директорию
        cleanup_temp_directory(temp_cert_dir)
        
        # Запускаем очистку старых сертификатов с задержкой
        run_cleanup_certs_delayed()
        
        # Запускаем функцию cleanup_old_certs
        run_cleanup_old_certs() 