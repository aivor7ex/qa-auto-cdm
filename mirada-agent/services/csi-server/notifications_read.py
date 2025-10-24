#!/usr/bin/env python3
from typing import Any, Dict, List, Optional
import logging
import importlib.util
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _extract_token(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Достает токен из тела запроса (только из поля x-access-token по требованиям).
    Разрешаем только строковые непустые значения.
    """
    if not isinstance(data, dict):
        return None
    token = data.get("x-access-token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def _load_get_db():
    """Лениво импортирует _get_db из локального config.py"""
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    spec = importlib.util.spec_from_file_location("csi_config", config_path)
    if spec is None or spec.loader is None:
        raise ImportError("Config module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _get_db = getattr(mod, "_get_db", None)
    if _get_db is None:
        raise ImportError("_get_db not found in config")
    return _get_db


def _normalize_ids(raw_ids: Any) -> List[str]:
    """Преобразует входное значение ids к списку строковых идентификаторов."""
    if not isinstance(raw_ids, list):
        return []
    result: List[str] = []
    for v in raw_ids:
        if isinstance(v, str) and v.strip():
            result.append(v.strip())
    # Удаляем дубликаты сохраняя порядок
    seen = set()
    unique: List[str] = []
    for v in result:
        if v not in seen:
            seen.add(v)
            unique.append(v)
    return unique


def handle(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Помечает уведомления как прочитанные по списку ids.

    Вход:
      body: {
        "x-access-token": "token",
        "ids": ["n1", "n2"]
      }

    Выход:
      {"result": "OK", "count": <int>} или {"result": "ERROR", "message": "..."}
    """
    try:
        logger.info("/notifications/read: старт обработчика")
        if isinstance(body, dict):
            try:
                sample_keys = ",".join(sorted(list(body.keys())[:10]))
                logger.info("/notifications/read: получено тело JSON; ключи=%s", sample_keys)
            except Exception:
                logger.info("/notifications/read: тело JSON получено (ключи недоступны для логирования)")
        else:
            logger.info("/notifications/read: тело запроса отсутствует или не является dict")

        # 1) Аутентификация: требуется наличие токена (без декодирования)
        token = _extract_token(body)
        logger.info("/notifications/read: результат извлечения токена: %s", "OK" if token else "ABSENT")
        if not token:
            logger.warning("/notifications/read: отсутствует x-access-token в теле запроса")
            return {"result": "ERROR", "message": "Authorization Required"}

        # 2) Валидация входных данных
        raw_ids = (body or {}).get("ids") if isinstance(body, dict) else None
        logger.info("/notifications/read: исходные ids тип=%s", type(raw_ids).__name__)
        ids = _normalize_ids(raw_ids)
        logger.info("/notifications/read: нормализовано ids: count=%d, preview=%s", len(ids), ids[:5])
        if not ids:
            logger.warning("/notifications/read: пустой/невалидный список ids")
            return {"result": "ERROR", "message": "Invalid or empty 'ids'"}

        # 3) Обновление документов в MongoDB
        logger.info("/notifications/read: подключение к MongoDB...")
        _get_db = _load_get_db()
        db = _get_db()
        logger.info("/notifications/read: подключение к MongoDB установлено")
        collection = db.get_collection("notification")

        now_iso = datetime.now(timezone.utc)
        update = {
            "$set": {
                "read": True,
                "modifiedAt": now_iso
            }
        }
        filter_obj = {"_id": {"$in": ids}}
        logger.info("/notifications/read: выполняем update_many; ids_count=%d", len(ids))
        res = collection.update_many(filter_obj, update)
        matched = getattr(res, "matched_count", 0)
        modified = getattr(res, "modified_count", 0)
        logger.info("/notifications/read: update_many завершен: matched=%s, modified=%s", matched, modified)

        logger.info("/notifications/read: успешное завершение")
        return {"result": "OK"}
    except Exception as e:
        logger.error("Ошибка при пометке уведомлений прочитанными: %s", e, exc_info=True)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
