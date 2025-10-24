#!/usr/bin/env python3
import json
import logging
import os
import time
from typing import Any, Dict, Optional

# Импортируем pymongo лениво внутри функций, чтобы избежать ошибок окружения

# Настройка логирования
logger = logging.getLogger(__name__)


def _safe_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return default
    return value


def _build_mongo_uri() -> str:
    # Приоритетная переменная окружения целиком
    uri = _safe_env("CSI_MONGO_URI") or _safe_env("MONGO_URI")
    if uri:
        return uri

    # Сборка из частей окружения без хардкода
    host = _safe_env("CSI_MONGO_HOST", "127.0.0.1")
    # По требованию: если порт не задан, используем 27018
    port = _safe_env("CSI_MONGO_PORT", "27018")
    db = _safe_env("CSI_MONGO_DB", "csi")
    return f"mongodb://{host}:{port}/{db}"




def _get_db():
    """Создает подключение к MongoDB и возвращает объект БД."""
    uri = _build_mongo_uri()
    logger.info(f"Подключение к MongoDB по URI: {uri}")
    
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, socketTimeoutMS=3000)
    
    # Проверяем доступность сервера
    client.admin.command("ping")
    
    # Получаем базу данных
    db = client.get_default_database()
    if db is None:
        db_name = _safe_env("CSI_MONGO_DB", "csi")
        db = client[db_name]
    
    return db


def _find_one_as_json(collection: str, filter_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    filter_json = json.dumps(filter_obj, ensure_ascii=False)
    logger.info(f"Поиск в коллекции '{collection}' с фильтром: {filter_json}")
    
    db = _get_db()
    doc = db.get_collection(collection).find_one(filter_obj)
    logger.info(f"Результат find_one: {doc}")
    return doc


def _delete_one_from_collection(collection: str, filter_obj: Dict[str, Any]) -> bool:
    """Удаляет один документ из коллекции по фильтру."""
    filter_json = json.dumps(filter_obj, ensure_ascii=False)
    logger.info(f"Удаление из коллекции '{collection}' с фильтром: {filter_json}")
    
    db = _get_db()
    result = db.get_collection(collection).delete_one(filter_obj)
    logger.info(f"Результат удаления: deleted_count={result.deleted_count}")
    return result.deleted_count > 0


def _validate_notification_stream(expected: Dict[str, Any]) -> Optional[str]:
    name = expected.get("name")
    logger.info(f"Валидация NotificationStream: name={name}, expected={expected}")
    
    if not isinstance(name, str) or not name:
        return "Некорректное поле NotificationStream.name"

    found = _find_one_as_json("notificationStream", {"name": name})
    logger.info(f"Найденный документ notificationStream: {found}")
    
    if not isinstance(found, dict):
        return "Объект notificationStream не найден"

    # Проверяем только присутствующие в expected поля
    for key in ("_id", "name", "priority", "userIds"):
        if key in expected:
            expected_val = expected.get(key)
            found_val = found.get(key)
            logger.info(f"Сравнение поля {key}: expected={expected_val}, found={found_val}")
            if found_val != expected_val:
                return f"Несовпадение поля notificationStream.{key}"
    logger.info("Валидация NotificationStream прошла успешно")
    return None


def _validate_security_settings(expected: Dict[str, Any]) -> Optional[str]:
    # Возможные ключи: id, type, value — ищем по value если передан, иначе по id
    filter_obj: Dict[str, Any] = {}
    if isinstance(expected.get("value"), str) and expected.get("value"):
        filter_obj["value"] = expected["value"]
    elif isinstance(expected.get("id"), str) and expected.get("id"):
        filter_obj["_id"] = expected["id"]
    else:
        return "Некорректные поля SecuritySettings для поиска"

    found = _find_one_as_json("securitySettings", filter_obj)
    if not isinstance(found, dict):
        return "Объект securitySettings не найден"

    # Сверяем только переданные поля
    for key, val in expected.items():
        # Для id -> _id
        key_db = "_id" if key == "id" else key
        if key_db in found and found.get(key_db) != val:
            return f"Несовпадение поля securitySettings.{key_db}"
    return None


def handle(body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        logger.info(f"Начало обработки запроса: {body}")
        
        # Извлекаем массив data
        if not isinstance(body, dict) or not isinstance(body.get("data"), list) or not body["data"]:
            return {"result": "ERROR", "message": "Некорректное тело запроса: отсутствует data[]"}

        item = body["data"][0]
        if not isinstance(item, dict):
            return {"result": "ERROR", "message": "Некорректный элемент data[0]"}

        # Проверяем соответствие назначению
        stack = item.get("stackName")
        service = item.get("serviceName")
        logger.info(f"Проверка stackName={stack}, serviceName={service}")
        if stack != "csi" or service != "csi-server":
            return {"result": "ERROR", "message": "Неверные stackName/serviceName"}

        cfg = item.get("config")
        if not isinstance(cfg, dict):
            return {"result": "ERROR", "message": "Отсутствует объект config"}

        logger.info(f"Конфигурация для проверки: {cfg}")

        # Задержка перед проверкой записи в БД (3 секунды)
        logger.info("Ожидание 3 секунды перед проверкой БД...")
        time.sleep(3)

        # Валидации по коллекциям, если присутствуют
        # 1) NotificationStream
        ns_list = cfg.get("NotificationStream")
        logger.info(f"NotificationStream список: {ns_list}")
        if isinstance(ns_list, list) and ns_list:
            ns = ns_list[0] if isinstance(ns_list[0], dict) else None
            if ns is None:
                return {"result": "ERROR", "message": "Некорректный NotificationStream[0]"}
            logger.info(f"Валидация NotificationStream: {ns}")
            err = _validate_notification_stream(ns)
            if err:
                logger.error(f"Ошибка валидации NotificationStream: {err}")
                return {"result": "ERROR", "message": err}

        # 2) SecuritySettings (опционально)
        ss_list = cfg.get("SecuritySettings")
        logger.info(f"SecuritySettings список: {ss_list}")
        if isinstance(ss_list, list) and ss_list:
            ss = ss_list[0] if isinstance(ss_list[0], dict) else None
            if ss is None:
                return {"result": "ERROR", "message": "Некорректный SecuritySettings[0]"}
            logger.info(f"Валидация SecuritySettings: {ss}")
            err = _validate_security_settings(ss)
            if err:
                logger.error(f"Ошибка валидации SecuritySettings: {err}")
                return {"result": "ERROR", "message": err}

        logger.info("Все проверки прошли успешно")
        
        # Удаляем проверенные записи из БД для чистоты тестов
        try:
            # Удаляем NotificationStream
            if isinstance(ns_list, list) and ns_list:
                ns = ns_list[0] if isinstance(ns_list[0], dict) else None
                if ns and isinstance(ns.get("name"), str):
                    _delete_one_from_collection("notificationStream", {"name": ns["name"]})
            
            # Удаляем SecuritySettings
            if isinstance(ss_list, list) and ss_list:
                ss = ss_list[0] if isinstance(ss_list[0], dict) else None
                if ss:
                    # Ищем по value или по _id
                    filter_obj = {}
                    if isinstance(ss.get("value"), str):
                        filter_obj["value"] = ss["value"]
                    elif isinstance(ss.get("id"), str):
                        filter_obj["_id"] = ss["id"]
                    if filter_obj:
                        _delete_one_from_collection("securitySettings", filter_obj)
        except Exception as e:
            logger.warning(f"Ошибка при удалении записей: {e}")
        
        return {"result": "OK"}
    except Exception as e:
        logger.error(f"Исключение в handle: {e}", exc_info=True)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


