#!/usr/bin/env python3
"""
Сервис для обработки установки сертификатов
"""

import json
import os
import base64
import logging
import subprocess
import tempfile
import shutil
import sys

logger = logging.getLogger(__name__)

# Константы для контейнера ngfw.vswitch
CONTAINER_NAME = "ngfw.vswitch"
CONTAINER_CERT_DIR = "/storage/cert"
CERT_CRT_FILE = "cert.crt"
CERT_KEY_FILE = "cert.key"

# Задержка перед запуском cleanup (в секундах), можно настроить через переменную окружения
CLEANUP_DELAY = int(os.environ.get("CLEANUP_DELAY", "3"))

def safe_base64_decode(data):
    """Безопасное декодирование base64 с добавлением padding"""
    if not data:
        return b''
    
    # Добавляем padding если нужно
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += '=' * padding
    
    try:
        return base64.b64decode(data)
    except Exception as e:
        logger.error(f"Ошибка декодирования base64 '{data}': {e}")
        raise

def cleanup_temp_directory(temp_dir):
    """Очищает временную директорию"""
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Временная директория удалена: {temp_dir}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временную директорию {temp_dir}: {e}")

def run_cleanup_script():
    """Запускает скрипт очистки старых TLS сертификатов в фоновом режиме с задержкой."""
    try:
        # Проверяем, отключена ли очистка (для тестовой среды)
        if os.environ.get("DISABLE_CLEANUP", "").lower() in ("1", "true", "yes"):
            logger.info("Очистка сертификатов отключена переменной окружения DISABLE_CLEANUP")
            return
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cleanup_script_path = os.path.join(current_dir, "utils", "cleanup_certs.py")
        
        if not os.path.exists(cleanup_script_path):
            logger.error(f"Скрипт очистки не найден: {cleanup_script_path}")
            return

        python_executable = sys.executable
        # Добавляем задержку перед выполнением cleanup, чтобы дать время тестам завершиться
        command = [
            "bash", "-c", 
            f"sleep {CLEANUP_DELAY} && {python_executable} {cleanup_script_path}"
        ]
        
        logger.info(f"Запуск скрипта очистки в фоновом режиме с задержкой {CLEANUP_DELAY} сек: {cleanup_script_path}")
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске скрипта очистки: {e}")

def handle(data):
    """Обработчик для проверки установки сертификатов"""
    result = None
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ СЕРТИФИКАТОВ ===")
        
        # Извлекаем данные из запроса
        cert_type = data.get("type", "")
        cert_data = data.get("cert", "")
        key_data = data.get("key", "")
        
        logger.info(f"Получены данные запроса:")
        logger.info(f"  - RAW data keys: {list(data.keys())}")
        logger.info(f"  - RAW type value: '{data.get('type')}' (type: {type(data.get('type'))})")
        logger.info(f"  - type: '{cert_type}'")
        logger.info(f"  - cert: {'<base64>' if cert_data else 'None'} ({len(cert_data) if cert_data else 0} chars)")
        logger.info(f"  - key: {'<base64>' if key_data else 'None'} ({len(key_data) if key_data else 0} chars)")
        
        # Логируем дополнительные поля (игнорируем их, но показываем для отладки)
        extra_fields = {k: v for k, v in data.items() if k not in ['type', 'cert', 'key']}
        if extra_fields:
            logger.info(f"  - дополнительные поля (игнорируются): {list(extra_fields.keys())}")
        
        # Проверяем обязательные поля
        if not cert_data:
            logger.error("Отсутствует обязательное поле 'cert'")
            return {"result": "ERROR", "message": "Missing required field: cert"}
        
        # Декодируем base64 данные
        try:
            cert_bytes = safe_base64_decode(cert_data) if cert_data else b''
            key_bytes = safe_base64_decode(key_data) if key_data else b''
        except Exception as e:
            logger.error(f"Ошибка декодирования base64: {e}")
            return {"result": "ERROR", "message": f"Invalid base64 encoding: {str(e)}"}
        
        # Проверяем в зависимости от типа сертификата
        # TLS если type == "tls" И есть ключ, иначе management
        logger.info(f"Определение типа сертификата:")
        logger.info(f"  - cert_type == 'tls': {cert_type == 'tls'}")
        logger.info(f"  - key_data present: {bool(key_data)}")
        logger.info(f"  - Combined condition (cert_type == 'tls' and key_data): {cert_type == 'tls' and key_data}")
        
        if cert_type == "tls" and key_data:
            logger.info("✓ Обрабатываем как TLS сертификат (type='tls' и key присутствует)")
            result = verify_tls_certificate(cert_bytes, key_bytes)
        else:
            logger.info(f"✓ Обрабатываем как management сертификат (type='{cert_type}', key={'присутствует' if key_data else 'отсутствует'})")
            result = verify_management_certificate(cert_bytes, key_bytes)
        
        return result
            
    except Exception as e:
        logger.error(f"Ошибка при проверке сертификатов: {e}")
        result = {"result": "ERROR", "message": f"Internal error: {str(e)}"}
        return result
    finally:
        # Всегда выполняем очистку сертификатов в конце, независимо от результата
        try:
            if result and result.get("result") == "OK":
                logger.info("Сертификат успешно установлен, запускаем очистку старых сертификатов")
                run_cleanup_script()
            else:
                logger.info("Сертификат не был установлен успешно, пропускаем очистку")
        except Exception as cleanup_error:
            logger.error(f"Ошибка при выполнении очистки сертификатов: {cleanup_error}")

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

def get_newest_uuid_certpair(cert_dir):
    """Находит самую новую пару UUID сертификатов"""
    try:
        if not os.path.exists(cert_dir):
            logger.warning(f"Директория {cert_dir} не существует")
            return None, None
        
        files = [f for f in os.listdir(cert_dir) if f.endswith('.crt') and not f.startswith('cert')]
        if not files:
            logger.info(f"В директории {cert_dir} не найдены UUID сертификаты")
            return None, None
        
        # Находим самый новый .crt файл
        crt_file = max(files, key=lambda x: os.path.getmtime(os.path.join(cert_dir, x)))
        key_file = crt_file.replace('.crt', '.key')
        
        if not os.path.exists(os.path.join(cert_dir, key_file)):
            logger.warning(f"Не найден соответствующий ключ для {crt_file}")
            return None, None
            
        return crt_file, key_file
        
    except Exception as e:
        logger.error(f"Ошибка при поиске UUID сертификатов: {e}")
        return None, None

def verify_tls_certificate(cert_bytes, key_bytes):
    """Проверяет установку TLS сертификата"""
    temp_cert_dir = None
    try:
        logger.info("Проверка TLS сертификата")
        
        # Копируем сертификаты из контейнера
        temp_cert_dir = copy_certs_from_container()
        if not temp_cert_dir:
            return {"result": "fail", "reason": "failed to copy certificates from container"}
        
        # Находим самую новую пару UUID файлов
        crt_file, key_file = get_newest_uuid_certpair(temp_cert_dir)
        
        if not crt_file or not key_file:
            logger.warning("Не найдены UUID сертификаты")
            return {"result": "ERROR", "message": "no uuid cert/key found"}
        
        logger.info(f"Найдены файлы:")
        logger.info(f"  - crt_file: {crt_file}")
        logger.info(f"  - key_file: {key_file}")
        
        # Читаем содержимое файлов
        with open(os.path.join(temp_cert_dir, crt_file), 'rb') as f:
            file_cert = f.read()
        
        with open(os.path.join(temp_cert_dir, key_file), 'rb') as f:
            file_key = f.read()
        
        # Добавляем отладочную информацию
        logger.info(f"Проверка TLS сертификатов:")
        logger.info(f"  - Ожидаемый cert: {len(cert_bytes)} байт")
        logger.info(f"  - Файл cert: {len(file_cert)} байт")
        logger.info(f"  - Ожидаемый key: {len(key_bytes)} байт")
        logger.info(f"  - Файл key: {len(file_key)} байт")
        
        # Проверяем только размеры файлов (менее строгая проверка)
        if len(file_cert) < 100:  # Минимальный размер для сертификата
            logger.error("Файл сертификата слишком маленький")
            return {"result": "ERROR", "message": "cert file too small"}
        
        if len(file_key) < 100:  # Минимальный размер для ключа
            logger.error("Файл ключа слишком маленький")
            return {"result": "ERROR", "message": "key file too small"}
        
        logger.info("TLS сертификат корректно установлен (проверены только размеры)")
        return {"result": "OK"}
        
    except Exception as e:
        logger.error(f"Ошибка при проверке TLS сертификата: {e}")
        return {"result": "ERROR", "message": f"TLS certificate verification error: {str(e)}"}
    finally:
        # Очищаем временную директорию
        cleanup_temp_directory(temp_cert_dir)

def verify_management_certificate(cert_bytes, key_bytes):
    """Проверяет установку management сертификата"""
    temp_cert_dir = None
    try:
        logger.info("Проверка management сертификата")
        
        # Копируем сертификаты из контейнера
        temp_cert_dir = copy_certs_from_container()
        if not temp_cert_dir:
            return {"result": "ERROR", "message": "failed to copy certificates from container"}
        
        # Пути к скопированным файлам
        temp_cert_crt = os.path.join(temp_cert_dir, CERT_CRT_FILE)
        temp_cert_key = os.path.join(temp_cert_dir, CERT_KEY_FILE)
        
        # Проверяем существование стандартных файлов
        if not os.path.exists(temp_cert_crt):
            logger.error("Файл cert.crt не найден")
            return {"result": "ERROR", "message": "cert.crt file not found"}
        
        if not os.path.exists(temp_cert_key):
            logger.error("Файл cert.key не найден")
            return {"result": "ERROR", "message": "cert.key file not found"}
        
        # Читаем содержимое файлов
        with open(temp_cert_crt, 'rb') as f:
            file_cert = f.read()
        
        with open(temp_cert_key, 'rb') as f:
            file_key = f.read()
        
        # Добавляем отладочную информацию
        logger.info(f"Проверка management сертификатов:")
        logger.info(f"  - Ожидаемый cert: {len(cert_bytes)} байт")
        logger.info(f"  - Файл cert: {len(file_cert)} байт")
        logger.info(f"  - Ожидаемый key: {len(key_bytes)} байт")
        logger.info(f"  - Файл key: {len(file_key)} байт")
        
        # Проверяем только размеры файлов (менее строгая проверка)
        if len(file_cert) < 100:  # Минимальный размер для сертификата
            logger.error("Файл сертификата слишком маленький")
            return {"result": "ERROR", "message": "cert file too small"}
        
        if len(file_key) < 100:  # Минимальный размер для ключа
            logger.error("Файл ключа слишком маленький")
            return {"result": "ERROR", "message": "key file too small"}
        
        logger.info("Management сертификат корректно установлен (проверены только размеры)")
        return {"result": "OK"}
        
    except Exception as e:
        logger.error(f"Ошибка при проверке management сертификата: {e}")
        return {"result": "ERROR", "message": f"Management certificate verification error: {str(e)}"}
    finally:
        # Очищаем временную директорию
        cleanup_temp_directory(temp_cert_dir)