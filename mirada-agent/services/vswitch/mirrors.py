#!/usr/bin/env python3
"""
Сервис для проверки mirror зеркалирования трафика
"""

import logging
import subprocess
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Константы для сетевого пространства имен
NETNS_NAME = "ngfw"


def _validate_request_data(data: Dict[str, Any]) -> Dict[str, str]:
    """Валидирует и извлекает данные из запроса."""
    if not isinstance(data, dict):
        raise ValueError("Данные запроса должны быть объектом")
    
    # Проверяем обязательные поля
    required_fields = ["id", "dev", "target", "type"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Отсутствует обязательное поле '{field}'")
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"Поле '{field}' должно быть непустой строкой")
    
    # Валидируем тип зеркалирования
    mirror_type = data["type"].lower()
    if mirror_type not in ["ingress", "egress", "both"]:
        raise ValueError(f"Неподдерживаемый тип зеркалирования: {mirror_type}. Допустимые: ingress, egress, both")
    
    # Валидируем формат ID
    mirror_id = data["id"]
    if not re.match(r'^[ieb]:\d+$', mirror_id):
        raise ValueError(f"Некорректный формат ID: {mirror_id}. Ожидается формат 'префикс:число' (i:, e:, b:)")
    
    return {
        "id": mirror_id,
        "dev": data["dev"].strip(),
        "target": data["target"].strip(),
        "type": mirror_type
    }


def _extract_preference_from_id(mirror_id: str) -> str:
    """Извлекает preference number из ID mirror."""
    # ID имеет формат "e:49152", нужно извлечь "49152"
    try:
        _, preference = mirror_id.split(":", 1)
        return preference
    except ValueError:
        raise ValueError(f"Некорректный формат ID mirror: {mirror_id}")


def _get_tc_filter_output(dev: str, direction: str) -> Optional[str]:
    """Получает вывод команды tc filter show для указанного устройства и направления."""
    try:
        cmd = ["ip", "netns", "exec", NETNS_NAME, "tc", "filter", "show", "dev", dev, direction]
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения tc filter show:")
            logger.error(f"  - returncode: {result.returncode}")
            logger.error(f"  - stderr: {result.stderr}")
            logger.error(f"  - stdout: {result.stdout}")
            return None
        
        logger.info(f"Команда tc filter show выполнена успешно")
        logger.debug(f"Вывод tc filter show: {result.stdout}")
        return result.stdout
        
    except Exception as e:
        logger.error(f"Исключение при выполнении tc filter show: {e}")
        return None


def _check_mirror_in_output(output: str, target: str, expected_preference: str) -> bool:
    """Проверяет наличие mirror в выводе tc filter show."""
    try:
        logger.info(f"Поиск mirror с target: {target} и preference: {expected_preference}")
        
        if not output or not output.strip():
            logger.warning("Вывод tc filter show пуст")
            return False
        
        # Ищем строки, содержащие target в формате "cdm-ngfw-vswitch:target"
        target_pattern = f"cdm-ngfw-vswitch:{re.escape(target)}"
        logger.info(f"Ищем паттерн target: {target_pattern}")
        
        # Разбираем вывод по строкам
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if target_pattern in line:
                logger.info(f"Найдена строка с target: {line}")
                
                # Извлекаем preference number из строки
                # Формат: "filter protocol all pref 49152 bpf chain 0 handle 0x1 cdm-ngfw-vswitch:dummy5.o:[mirror/ingress] ..."
                pref_match = re.search(r'pref\s+(\d+)', line)
                if pref_match:
                    actual_preference = pref_match.group(1)
                    logger.info(f"Найден preference: {actual_preference}")
                    
                    if actual_preference == expected_preference:
                        logger.info(f"Mirror найден и preference совпадает: {actual_preference}")
                        return True
                    else:
                        logger.warning(f"Mirror найден, но preference не совпадает. Ожидался: {expected_preference}, найден: {actual_preference}")
                        return False
                else:
                    logger.warning(f"Не удалось извлечь preference из строки: {line}")
        
        logger.warning(f"Mirror с target {target} не найден в выводе")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при проверке mirror в выводе: {e}")
        return False


def _verify_mirror(params: Dict[str, str]) -> bool:
    """Проверяет наличие mirror для указанных параметров."""
    try:
        mirror_id = params["id"]
        dev = params["dev"]
        target = params["target"]
        mirror_type = params["type"]
        
        # Извлекаем preference number из ID
        expected_preference = _extract_preference_from_id(mirror_id)
        logger.info(f"Ожидаемый preference: {expected_preference}")
        
        # Определяем направления для проверки на основе типа
        directions = []
        if mirror_type == "ingress":
            directions = ["ingress"]
        elif mirror_type == "egress":
            directions = ["egress"]
        elif mirror_type == "both":
            directions = ["ingress", "egress"]
        
        logger.info(f"Проверяем направления: {directions}")
        
        # Проверяем каждое направление
        for direction in directions:
            logger.info(f"Проверяем направление: {direction}")
            
            # Получаем вывод tc filter show
            tc_output = _get_tc_filter_output(dev, direction)
            if tc_output is None:
                logger.error(f"Не удалось получить вывод tc filter show для {dev} {direction}")
                return False
            
            # Проверяем наличие mirror в выводе
            mirror_found = _check_mirror_in_output(tc_output, target, expected_preference)
            if not mirror_found:
                logger.error(f"Mirror не найден для направления {direction}")
                return False
            
            logger.info(f"Mirror найден для направления {direction}")
        
        logger.info("Все проверки mirror пройдены успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке mirror: {e}")
        return False


def handle(data: Dict[str, Any]) -> Dict[str, Any]:
    """Обработчик для проверки mirror зеркалирования трафика.
    
    Ожидаемые поля:
      - id: ID mirror с префиксом типа (например, "e:49152")
      - dev: имя сетевого интерфейса
      - target: целевой интерфейс для зеркалирования
      - type: тип зеркалирования (ingress, egress, both)
    
    Возвращает:
      - {"result": "OK"} при успехе
      - {"result": "ERROR", "message": "описание ошибки"} при ошибке
    """
    try:
        logger.info("=== НАЧАЛО ПРОВЕРКИ MIRROR ===")
        
        logger.info(f"Получены данные запроса: {data}")
        logger.info(f"Тип данных: {type(data)}")
        
        # Проверяем, что данные не пустые
        if not data:
            logger.error("Получены пустые данные")
            return {"result": "ERROR", "message": "Отсутствуют данные запроса"}
        
        # Валидируем и извлекаем параметры
        try:
            params = _validate_request_data(data)
        except ValueError as e:
            logger.error(f"Ошибка валидации: {e}")
            return {"result": "ERROR", "message": str(e)}
        
        logger.info(f"Извлеченные параметры: {params}")
        
        # Проверяем mirror
        mirror_verified = _verify_mirror(params)
        
        if mirror_verified:
            logger.info("Mirror проверен успешно")
            return {"result": "OK"}
        else:
            logger.warning("Mirror не найден или проверка не пройдена")
            return {"result": "ERROR", "message": "Mirror не найден или не соответствует ожидаемому"}
            
    except Exception as e:
        logger.error(f"Ошибка при проверке mirror: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}
