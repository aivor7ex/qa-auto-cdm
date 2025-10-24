#!/usr/bin/env python3
"""
Сервис utils/ping — проверка существования процесса ping в namespace ngfw
с ожидаемыми аргументами и запуск нового процесса, если соответствующий не найден.

Запрос (POST /utils/ping):
  - { "addr": str, "packetsAmount"?: int, "timeout"?: int, "payloadSize"?: int, "source"?: str, "period"?: float, "pmtuDefinition"?: str }

Алгоритм:
  1) Выполнить: ip netns exec ngfw ps aux | grep ping
  2) Спарсить вывод и убедиться, что есть процесс с аргументами, соответствующими полям тела (проверяем только переданные поля):
     - addr всегда должен присутствовать в аргументах команды
     - если задан packetsAmount — ожидается "-c <packetsAmount>" или "-c<packetsAmount>"
     - если задан timeout — ожидается "-W <timeout>" или "-W<timeout>"
     - если задан payloadSize — ожидается "-s <payloadSize>" или "-s<payloadSize>"
     - если задан source — ожидается "-I <source>" или "-I<source>"
     - если задан period — ожидается "-i <period>" или "-i<period>"
     - если задан pmtuDefinition — ожидается "-M <pmtuDefinition>" или "-M<pmtuDefinition>"
  3) Если соответствующий процесс не найден, запустить новый процесс ping с указанными параметрами
  4) Вернуть { "result": "OK" } или { "result": "ERROR", "message": str }
"""

import logging
import subprocess
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Константы
NETNS_NAME = "ngfw"

def _validate_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Валидирует и нормализует входные параметры запроса."""
    if not isinstance(data, dict):
        raise ValueError("Данные запроса должны быть объектом")

    addr = data.get("addr")
    packets_amount = data.get("packetsAmount")
    timeout = data.get("timeout")
    payload_size = data.get("payloadSize")
    source = data.get("source")
    period = data.get("period")
    pmtu_definition = data.get("pmtuDefinition")

    # Валидация addr (обязательное поле)
    if not isinstance(addr, str) or not addr.strip():
        raise ValueError("Поле 'addr' обязательно и должно быть непустой строкой")
    
    # Валидация длинной строки для addr
    if len(addr.strip()) > 253:  # RFC максимальная длина FQDN
        raise ValueError("Поле 'addr' слишком длинное")
    
    # Валидация addr на недопустимые символы (базовая проверка)
    if not re.match(r'^[a-zA-Z0-9\.\-:]+$', addr.strip()):
        raise ValueError("Поле 'addr' содержит недопустимые символы")

    # Валидация packetsAmount
    packets_amount_int: Optional[int] = None
    if packets_amount is not None:
        try:
            packets_amount_int = int(packets_amount)
        except (TypeError, ValueError):
            raise ValueError("Поле 'packetsAmount' должно быть целым числом, если задано")
        if packets_amount_int <= 0 or packets_amount_int > 65535:
            raise ValueError("Поле 'packetsAmount' должно быть в диапазоне 1-65535")

    # Валидация timeout
    timeout_int: Optional[int] = None
    if timeout is not None:
        try:
            timeout_int = int(timeout)
        except (TypeError, ValueError):
            raise ValueError("Поле 'timeout' должно быть целым числом, если задано")
        if timeout_int <= 0:
            raise ValueError("Поле 'timeout' должно быть положительным числом")

    # Валидация payloadSize
    payload_size_int: Optional[int] = None
    if payload_size is not None:
        try:
            payload_size_int = int(payload_size)
        except (TypeError, ValueError):
            raise ValueError("Поле 'payloadSize' должно быть целым числом, если задано")
        if payload_size_int < 0:
            raise ValueError("Поле 'payloadSize' не может быть отрицательным")

    # Валидация source
    if source is not None:
        if not isinstance(source, str):
            raise ValueError("Поле 'source' должно быть строкой, если задано")
        if source == "":
            raise ValueError("Поле 'source' не может быть пустой строкой")
        # Проверка на недопустимые символы в имени интерфейса
        if not re.match(r'^[a-zA-Z0-9\.\-_]+$', source):
            raise ValueError("Поле 'source' содержит недопустимые символы")

    # Валидация period
    period_float: Optional[float] = None
    if period is not None:
        try:
            period_float = float(period)
        except (TypeError, ValueError):
            raise ValueError("Поле 'period' должно быть числом, если задано")
        if period_float <= 0:
            raise ValueError("Поле 'period' должно быть положительным числом")

    # Валидация pmtuDefinition
    if pmtu_definition is not None:
        if not isinstance(pmtu_definition, str):
            raise ValueError("Поле 'pmtuDefinition' должно быть строкой, если задано")
        if pmtu_definition not in ["do", "want", "dont"]:
            raise ValueError("Поле 'pmtuDefinition' должно быть одним из: do, want, dont")

    # Проверка на неизвестные параметры (игнорируем их для совместимости)
    known_params = {"addr", "packetsAmount", "timeout", "payloadSize", "source", "period", "pmtuDefinition"}
    unknown_params = set(data.keys()) - known_params
    if unknown_params:
        logger.warning(f"Игнорируются неизвестные параметры: {unknown_params}")

    return {
        "addr": addr.strip(),
        "packetsAmount": packets_amount_int,
        "timeout": timeout_int,
        "payloadSize": payload_size_int,
        "source": source,
        "period": period_float,
        "pmtuDefinition": pmtu_definition,
    }

def _parse_ps_line(line: str) -> List[str]:
    """Парсит строку из вывода ps aux и извлекает аргументы команды ping."""
    # Формат ps aux: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
    # Нам нужна только часть COMMAND
    parts = line.strip().split(None, 10)  # Разбиваем на максимум 11 частей
    if len(parts) < 11:
        return []
    
    command_line = parts[10]  # Последняя часть - командная строка
    
    # Разбиваем командную строку на аргументы
    cmd_parts = command_line.split()
    
    # Находим ping в командной строке
    ping_index = -1
    for i, part in enumerate(cmd_parts):
        if part.endswith("ping") or part == "ping":
            ping_index = i
            break
    
    if ping_index == -1:
        return []
    
    # Возвращаем аргументы после ping (исключая сам ping)
    return cmd_parts[ping_index + 1:]

def _match_flag_with_value(args: List[str], flag: str, expected_value: str) -> bool:
    """Проверяет наличие флага с ожидаемым значением в формате -flag value или -flagvalue."""
    for i, arg in enumerate(args):
        if arg == flag:
            # Формат: -flag value
            if i + 1 < len(args) and args[i + 1] == expected_value:
                return True
        elif arg.startswith(flag) and len(arg) > len(flag):
            # Формат: -flagvalue
            if arg[len(flag):] == expected_value:
                return True
    return False

def _contains_addr(args: List[str], addr: str) -> bool:
    """Проверяет, содержится ли адрес среди аргументов."""
    addr_lower = addr.lower()
    for arg in args:
        if arg.lower() == addr_lower:
            return True
    return False

def _matches_expected_ping_args(args: List[str], params: Dict[str, Any]) -> bool:
    """Проверяет, соответствуют ли аргументы ping ожидаемым параметрам."""
    addr = params["addr"]
    packets_amount = params.get("packetsAmount")
    timeout = params.get("timeout")
    payload_size = params.get("payloadSize")
    source = params.get("source")
    period = params.get("period")
    pmtu_definition = params.get("pmtuDefinition")

    # Адрес должен обязательно присутствовать
    if not _contains_addr(args, addr):
        return False

    # Проверка packetsAmount (-c)
    if packets_amount is not None:
        if not _match_flag_with_value(args, "-c", str(packets_amount)):
            return False

    # Проверка timeout (-W)
    if timeout is not None:
        if not _match_flag_with_value(args, "-W", str(timeout)):
            return False

    # Проверка payloadSize (-s)
    if payload_size is not None:
        if not _match_flag_with_value(args, "-s", str(payload_size)):
            return False

    # Проверка source (-I)
    if source is not None:
        if not _match_flag_with_value(args, "-I", source):
            return False

    # Проверка period (-i)
    if period is not None:
        if not _match_flag_with_value(args, "-i", str(period)):
            return False

    # Проверка pmtuDefinition (-M)
    if pmtu_definition is not None:
        if not _match_flag_with_value(args, "-M", pmtu_definition):
            return False

    return True

def handle(data: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает запрос проверки процесса ping в netns ngfw.

    Ожидает: { 'addr': str, 'packetsAmount': int, 'timeout': int, 'payloadSize': int, ... }
    Возвращает: { 'result': 'OK' } | { 'result': 'ERROR', 'message': str }
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА UTILS/PING ===")
        logger.info(f"Полученные данные: {data}")

        params = _validate_request(data)
        logger.info(f"Валидированные параметры: {params}")

        # Выполняем команду для поиска процессов ping
        cmd = ["ip", "netns", "exec", NETNS_NAME, "ps", "aux"]
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды: rc={result.returncode}, stderr={result.stderr}")
            return {"result": "ERROR", "message": "Failed to execute ps command in ngfw namespace"}

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        
        if not stdout:
            logger.info("Нет вывода от команды ps")
            return {"result": "ERROR", "message": "ping process not found in ngfw"}

        # Фильтруем строки, содержащие ping
        ping_lines = []
        for line in stdout.splitlines():
            if "ping" in line and "grep" not in line:  # Исключаем сам grep
                ping_lines.append(line)

        if not ping_lines:
            logger.info("Не найдено процессов ping")
            return {"result": "ERROR", "message": "ping process not found in ngfw"}

        logger.info(f"Найдено {len(ping_lines)} процессов ping")
        
        # Проверяем каждый найденный процесс ping
        for line in ping_lines:
            logger.info(f"Анализируем строку: {line}")
            args = _parse_ps_line(line)
            logger.info(f"Извлеченные аргументы: {args}")
            
            if _matches_expected_ping_args(args, params):
                logger.info("Найден соответствующий процесс ping")
                return {"result": "OK"}

        # Если соответствующий процесс не найден, запускаем новый
        logger.info("Не найдено процесса ping с ожидаемыми аргументами, запускаем новый")
        
        # Формируем команду ping
        ping_cmd = ["ip", "netns", "exec", NETNS_NAME, "ping"]
        
        # Добавляем параметры
        if params.get("packetsAmount"):
            ping_cmd.extend(["-c", str(params["packetsAmount"])])
        
        if params.get("timeout"):
            ping_cmd.extend(["-W", str(params["timeout"])])
        
        if params.get("payloadSize"):
            ping_cmd.extend(["-s", str(params["payloadSize"])])
        
        if params.get("source"):
            ping_cmd.extend(["-I", params["source"]])
        
        if params.get("period"):
            ping_cmd.extend(["-i", str(params["period"])])
        
        if params.get("pmtuDefinition"):
            ping_cmd.extend(["-M", params["pmtuDefinition"]])
        
        # Добавляем адрес
        ping_cmd.append(params["addr"])
        
        logger.info(f"Запускаем команду: {' '.join(ping_cmd)}")
        
        # Запускаем ping в фоновом режиме
        try:
            subprocess.Popen(ping_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Процесс ping запущен успешно")
            return {"result": "OK"}
        except Exception as e:
            logger.error(f"Ошибка запуска ping: {e}")
            return {"result": "ERROR", "message": f"Failed to start ping process: {e}"}

    except ValueError as ve:
        logger.error(f"Ошибка валидации: {ve}")
        return {"result": "ERROR", "message": str(ve)}
    except Exception as e:
        logger.error(f"Внутренняя ошибка в utils/ping: {e}")
        return {"result": "ERROR", "message": "internal error"}
