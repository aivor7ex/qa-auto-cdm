import os
import subprocess
from datetime import datetime
from typing import Any, Dict

# Настройки через переменные окружения, с безопасными дефолтами
LOG_DIR = os.environ.get("SYSTEM_REPORT_LOGS_DIR", "/opt/cdm-data/mirada-logs")
REPORT_FILE_NAME = os.environ.get("SYSTEM_REPORT_FILE", "system-report.log.zip")
REPORT_FILE_PATH = os.path.join(LOG_DIR, REPORT_FILE_NAME)


def _file_exists(file_path: str) -> bool:
    """Проверка существования файла безопасной системной командой."""
    try:
        proc = subprocess.run(["test", "-f", file_path], check=False)
        return proc.returncode == 0
    except Exception:
        return False


def _get_file_metadata(file_path: str) -> Dict[str, Any]:
    """Получить метаданные файла. Исключения не выбрасывает, а возвращает пустой результат."""
    try:
        st = os.stat(file_path)
        ctime = datetime.fromtimestamp(st.st_ctime).isoformat(timespec="milliseconds") + "Z"
        mtime = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="milliseconds") + "Z"
        return {"ctime": ctime, "mtime": mtime, "size": st.st_size}
    except Exception:
        return {}


def handle(status: str) -> Dict[str, Any]:
    """
    Верификация состояния генерации system-report.log.zip.

    Аргументы:
      status: Один из ["NOT_FOUND", "GENERATION_IN_PROGRESS", "GENERATED"] из тела запроса.

    Возвращает:
      {"result": "OK"} или {"result": "ERROR", "message": str}
    """
    allowed = {"NOT_FOUND", "GENERATION_IN_PROGRESS", "GENERATED"}

    if not isinstance(status, str) or status not in allowed:
        return {"result": "ERROR", "message": "Invalid or unsupported status"}

    exists = _file_exists(REPORT_FILE_PATH)

    if status == "NOT_FOUND":
        if exists:
            return {
                "result": "ERROR",
                "message": f"{REPORT_FILE_NAME} exists but request expected NOT_FOUND"
            }
        return {"result": "OK"}

    if status == "GENERATION_IN_PROGRESS":
        # Файл может как существовать, так и нет — это считается корректным
        return {"result": "OK"}

    # status == "GENERATED"
    if not exists:
        return {
            "result": "ERROR",
            "message": f"{REPORT_FILE_NAME} not found at {LOG_DIR} while status is GENERATED"
        }

    # Опционально: не влияя на контракт, можем проверить метаданные
    _ = _get_file_metadata(REPORT_FILE_PATH)
    return {"result": "OK"}
