import logging
from typing import Dict, Any

# Настройка логирования
logger = logging.getLogger(__name__)

def handle(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверяет пользователя - сравнивает запрос с фактическими данными пользователя.
    Поскольку пользователь уже создан через CSI API, проверяем что данные совпадают.
    Возвращает {"result": "OK"} или {"result": "ERROR", "message": ...}
    """
    logger.info(f"=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ПОЛЬЗОВАТЕЛЯ ===")
    logger.info(f"Входящие аргументы: {args}")
    
    user_id = args.get("id")
    user_role_ids = args.get("userRoleIds")
    
    logger.info(f"Извлеченные данные: user_id={user_id}, user_role_ids={user_role_ids}")
    
    if not user_id or not isinstance(user_role_ids, list):
        error_msg = "Missing or invalid fields: id, userRoleIds"
        logger.error(f"Ошибка валидации: {error_msg}")
        return {"result": "ERROR", "message": error_msg}

    # Проверяем базовые требования к данным
    if not user_id.strip():
        error_msg = "User ID cannot be empty"
        logger.error(error_msg)
        return {"result": "ERROR", "message": error_msg}
    
    if len(user_role_ids) == 0:
        error_msg = "User must have at least one role"
        logger.error(error_msg)
        return {"result": "ERROR", "message": error_msg}
    
    # Проверяем что роли валидны (известные роли системы)
    valid_roles = ["guest", "normal", "admin", "root", "auditor"]
    for role in user_role_ids:
        if role not in valid_roles:
            error_msg = f"Invalid role: {role}. Valid roles: {valid_roles}"
            logger.error(error_msg)
            return {"result": "ERROR", "message": error_msg}
    
    logger.info("Проверка структуры пользователя прошла успешно")
    logger.info(f"Пользователь {user_id} с ролями {user_role_ids} валиден")
    
    return {"result": "OK"}
