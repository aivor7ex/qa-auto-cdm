#!/usr/bin/env python3
"""
Обработчик для эндпоинта /notifications/delete-all

Требования:
- Принимает токен доступа (x-access-token) из разных источников: заголовок, query, тело JSON
- Подключается к MongoDB с использованием существующей логики из config.py
- Удаляет все уведомления из коллекции notification (детерминированно)
- Возвращает JSON: {"result":"OK"} или {"result":"ERROR","message":"..."}
"""

from typing import Any, Dict, Optional
import logging
import importlib.util
import os


logger = logging.getLogger(__name__)


def _extract_token(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Извлекает токен из возможных полей тела запроса.

    Поддерживаемые ключи:
    - "x-access-token"
    - "access_token"
    """
    if not isinstance(data, dict):
        return None
    token = data.get("x-access-token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def handle(body: Optional[Dict[str, Any]] = None, *,
           header_token: Optional[str] = None,
           query_token: Optional[str] = None) -> Dict[str, Any]:
    """Основной обработчик удаления всех уведомлений.

    Параметры:
      - body: тело JSON запроса (опционально)
      - header_token: значение заголовка x-access-token (если было передано маршрутом)
      - query_token: значение параметра access_token из query (если было передано маршрутом)
    """
    try:
        # 1) Аутентификация (минимальная проверка на присутствие токена без его декодирования)
        token = header_token or query_token or _extract_token(body)
        if not token:
            return {"result": "ERROR", "message": "Authorization Required"}

        # 2) Подключение к MongoDB и удаление уведомлений (динамический импорт config._get_db)
        config_path = os.path.join(os.path.dirname(__file__), "config.py")
        spec = importlib.util.spec_from_file_location("csi_config", config_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Config module not found"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _get_db = getattr(mod, "_get_db", None)
        if _get_db is None:
            return {"result": "ERROR", "message": "_get_db not found in config"}

        db = _get_db()
        collection = db.get_collection("notification")
        delete_result = collection.delete_many({})
        logger.info("Удалено уведомлений: %s", getattr(delete_result, "deleted_count", 0))

        # 3) Возвращаем детерминированный ответ
        return {"result": "OK"}
    except Exception as e:
        logger.error("Ошибка при удалении уведомлений: %s", e, exc_info=True)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


