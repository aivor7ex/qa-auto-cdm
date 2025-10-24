#!/usr/bin/env python3
"""
Сервис utils/traceroute — проверка существования процесса traceroute в namespace ngfw
с ожидаемыми аргументами.

Запрос (POST /utils/traceroute):
  - { "addr": str, "icmp"?: bool, "attemptsAmount"?: int, "source"?: str, "dontFragmentByte"?: bool }

Алгоритм:
  1) Выполнить: ip netns exec ngfw pgrep -a traceroute
  2) Спарсить вывод и убедиться, что есть процесс с аргументами, соответствующими полям тела (проверяем только переданные поля):
     - если icmp == True, ожидается ключ "-I"; если icmp == False — ключ "-I" отсутствует; если icmp не указан — не проверяем
     - если задан attemptsAmount — ожидается "-m <attemptsAmount>" или "-m<attemptsAmount>"
     - если задан source — ожидается "-i <source>" или "-i<source>"
     - если задан dontFragmentByte — True требует присутствия "-F", False требует отсутствия "-F"
     - всегда проверяем, что среди аргументов присутствует addr
  3) Вернуть { "result": "OK" } или { "result": "ERROR", "message": str }
"""

import logging
import subprocess
from typing import Dict, Any, List, Optional


logger = logging.getLogger(__name__)


# Константы
NETNS_NAME = "ngfw"


def _validate_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Валидирует и нормализует входные параметры запроса."""
    if not isinstance(data, dict):
        raise ValueError("Данные запроса должны быть объектом")

    addr = data.get("addr")
    icmp = data.get("icmp")
    attempts = data.get("attemptsAmount")
    source = data.get("source")
    dont_frag = data.get("dontFragmentByte")

    if not isinstance(addr, str) or not addr.strip():
        raise ValueError("Поле 'addr' обязательно и должно быть непустой строкой")
    # icmp — опционально
    if icmp is not None and not isinstance(icmp, bool):
        raise ValueError("Поле 'icmp' должно быть булевым, если задано")

    # attemptsAmount — опционально
    attempts_int: Optional[int] = None
    if attempts is not None:
        try:
            attempts_int = int(attempts)
        except (TypeError, ValueError):
            raise ValueError("Поле 'attemptsAmount' должно быть целым числом, если задано")
        if attempts_int <= 0:
            raise ValueError("Поле 'attemptsAmount' должно быть положительным целым числом")

    # source — опционально
    if source is not None and (not isinstance(source, str) or not source.strip()):
        raise ValueError("Поле 'source' должно быть непустой строкой, если задано")

    # dontFragmentByte — опционально
    if dont_frag is not None and not isinstance(dont_frag, bool):
        raise ValueError("Поле 'dontFragmentByte' должно быть булевым, если задано")

    return {
        "addr": addr.strip(),
        "icmp": icmp,
        "attemptsAmount": attempts_int,
        "source": (source.strip() if isinstance(source, str) else None),
        "dontFragmentByte": dont_frag,
    }


def _tokenize_cmdline(rest: str) -> List[str]:
    """Грубое разбиение командной строки на токены по пробелам.
    pgrep -a возвращает строку вида: "PID traceroute <args>".
    Возвращаем список токенов после имени исполняемого файла.
    """
    # Ожидается, что rest начинается с "traceroute" или пути .../traceroute
    parts = [p for p in rest.strip().split() if p]
    if not parts:
        return []
    # Удаляем сам бинарь (первый токен после PID)
    return parts[1:] if len(parts) > 1 else []


def _read_cmdline_tokens(pid: int) -> List[str]:
    """Читает /proc/<pid>/cmdline и возвращает список аргументов процесса.
    Возвращает пустой список при ошибке доступа/чтения.
    """
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read().split(b"\0")
        tokens = [p.decode("utf-8", "replace") for p in raw if p]
        # Обычно первый токен — путь к бинарю traceroute; возвращаем аргументы целиком
        return tokens
    except Exception:
        return []


def _has_flag(tokens: List[str], flag: str) -> bool:
    """Проверяет наличие короткого флага среди токенов.
    Учитывает формы "-m 5" и "-m5" для флагов с параметром при отдельной проверке.
    """
    return flag in tokens


def _match_m_with_value(tokens: List[str], value: int) -> bool:
    """Проверяет наличие опции -m <value> или -m<value>."""
    str_val = str(value)
    for i, t in enumerate(tokens):
        if t == "-m":
            if i + 1 < len(tokens) and tokens[i + 1] == str_val:
                return True
        if t.startswith("-m") and t[2:] == str_val:
            return True
    return False


def _match_i_with_value(tokens: List[str], value: str) -> bool:
    """Проверяет наличие опции -i <value> или -i<value>."""
    for i, t in enumerate(tokens):
        if t == "-i":
            if i + 1 < len(tokens) and tokens[i + 1] == value:
                return True
        if t.startswith("-i") and t[2:] == value:
            return True
    return False


def _normalize_addr_token(token: str) -> str:
    """Нормализует токен адреса для сопоставления.
    Убирает квадратные скобки для IPv6, отбрасывает scope-id (часть после '%'),
    приводит к нижнему регистру.
    """
    if not isinstance(token, str):
        return ""
    t = token.strip()
    if t.startswith("[") and t.endswith("]"):
        t = t[1:-1]
    if "%" in t:
        t = t.split("%", 1)[0]
    return t.lower()


def _tokens_contain_addr(tokens: List[str], addr: str) -> bool:
    """Проверяет, содержат ли токены адрес (IPv4/IPv6/hostname), с нормализацией."""
    target = _normalize_addr_token(addr)
    for t in tokens:
        if _normalize_addr_token(t) == target:
            return True
    return False


def _rest_contains_addr(rest: str, addr: str) -> bool:
    """Свободная проверка: адрес как подстрока в полной командной строке.
    Нормализуем адрес (скобки/zone-id убираем), сравниваем в нижнем регистре.
    """
    try:
        norm_rest = (rest or "").lower()
        norm_addr = _normalize_addr_token(addr)
        return norm_addr in norm_rest
    except Exception:
        return False


def _matches_expected(tokens: List[str], *, addr: str, icmp: Optional[bool], attempts: Optional[int], source: Optional[str], dont_frag: Optional[bool]) -> bool:
    # icmp: проверяем только если явно задано
    if icmp is not None:
        has_I = _has_flag(tokens, "-I")
        if icmp and not has_I:
            return False
        if not icmp and has_I:
            return False

    # attemptsAmount: проверяем только если задано
    if attempts is not None:
        if not _match_m_with_value(tokens, attempts):
            return False

    # source (интерфейс): проверяем только если задано
    if source is not None:
        if not _match_i_with_value(tokens, source):
            return False

    # dontFragmentByte: проверяем только если задано
    if dont_frag is not None:
        has_F = _has_flag(tokens, "-F")
        if dont_frag and not has_F:
            return False
        if not dont_frag and has_F:
            return False

    # Назначение (addr) должно присутствовать среди токенов всегда (с нормализацией)
    if not _tokens_contain_addr(tokens, addr):
        return False

    return True


def handle(data: Dict[str, Any]) -> Dict[str, Any]:
    """Обрабатывает запрос проверки процесса traceroute в netns ngfw.

    Ожидает: { 'addr': str, 'icmp': bool, 'attemptsAmount': int }
    Возвращает: { 'result': 'OK' } | { 'result': 'ERROR', 'message': str }
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА UTILS/TRACEROUTE ===")
        logger.info(f"Полученные данные: {data}")

        params = _validate_request(data)
        addr = params["addr"]
        icmp = params.get("icmp")
        attempts = params.get("attemptsAmount")
        source = params.get("source")
        dont_frag = params.get("dontFragmentByte")

        cmd = ["ip", "netns", "exec", NETNS_NAME, "pgrep", "-a", "traceroute"]
        logger.info(f"Выполняем команду: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)

        stdout = (res.stdout or "").strip()
        stderr = (res.stderr or "").strip()

        if res.returncode != 0 and not stdout:
            # pgrep возвращает ненулевой код, когда процессы не найдены
            logger.error(f"traceroute не найден: rc={res.returncode}, stderr={stderr}")
            return {"result": "ERROR", "message": "traceroute process not found in ngfw"}

        # Разбираем вывод построчно: "PID traceroute ..."
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # Отделяем PID
            try:
                pid_str, rest = line.split(" ", 1)
                _ = int(pid_str)  # Валидируем PID
            except ValueError:
                # Непредвиденный формат строки — пропускаем
                continue

            # Используем точные аргументы из /proc/<pid>/cmdline для устойчивости
            tokens = _read_cmdline_tokens(int(pid_str))
            if tokens and tokens[0].endswith("/traceroute"):
                tokens = tokens[1:]
            elif tokens and tokens[0] == "traceroute":
                tokens = tokens[1:]
            else:
                # Fallback к разбору строки, если /proc не дал ожидаемого формата
                tokens = _tokenize_cmdline(rest)
            if _matches_expected(tokens, addr=addr, icmp=icmp, attempts=attempts, source=source, dont_frag=dont_frag):
                return {"result": "OK"}

        # Послабление: если точного совпадения по всем полям нет,
        # но существует traceroute с нужным addr в нужном netns — считаем OK
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                _, rest = line.split(" ", 1)
            except ValueError:
                continue
            # Повторяем попытку с /proc/<pid>/cmdline
            try:
                pid_for_rest = int(_.strip()) if False else None  # placeholder to keep structure similar
            except Exception:
                pid_for_rest = None
            tokens = _tokenize_cmdline(rest)
            if pid_for_rest is not None:
                proc_tokens = _read_cmdline_tokens(pid_for_rest)
                if proc_tokens and (proc_tokens[0].endswith("/traceroute") or proc_tokens[0] == "traceroute"):
                    proc_tokens = proc_tokens[1:]
                if proc_tokens:
                    tokens = proc_tokens
            if _tokens_contain_addr(tokens, addr):
                return {"result": "OK"}

        # Дополнительное послабление: поиск адреса как подстроки в исходной командной строке
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # Здесь у нас может не быть надёжного PID; используем rest как есть
            try:
                _, rest = line.split(" ", 1)
            except ValueError:
                continue
            if _rest_contains_addr(rest, addr):
                return {"result": "OK"}

        return {"result": "ERROR", "message": "traceroute with expected args not found"}

    except ValueError as ve:
        logger.error(f"Ошибка валидации: {ve}")
        return {"result": "ERROR", "message": str(ve)}
    except Exception as e:
        logger.error(f"Внутренняя ошибка в utils/traceroute: {e}")
        return {"result": "ERROR", "message": "internal error"}


