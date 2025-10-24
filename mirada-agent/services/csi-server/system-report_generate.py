import logging
import os
import time
import subprocess
from datetime import datetime
from marshmallow import Schema, fields, INCLUDE, ValidationError

logger = logging.getLogger(__name__)

# Настройки через переменные окружения, с безопасными дефолтами
LOG_DIR = os.environ.get("SYSTEM_REPORT_LOGS_DIR", "/opt/cdm-data/mirada-logs")
REPORT_FILE_NAME = os.environ.get("SYSTEM_REPORT_FILE", "system-report.log.zip")
REPORT_FILE_PATH = os.path.join(LOG_DIR, REPORT_FILE_NAME)
# Окно стабильности размера файла (секунд подряд без изменений)
STABLE_WINDOW_SECONDS = int(os.environ.get("SYSTEM_REPORT_STABLE_SECONDS", "10"))

class SystemReportGenerateRequestSchema(Schema):
    status = fields.Str(required=True, metadata={"description": "Статус генерации отчета: GENERATION_STARTED"})
    class Meta:
        unknown = INCLUDE

class SystemReportGenerateResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

def _file_exists(file_path: str) -> bool:
    try:
        proc = subprocess.run(["test", "-f", file_path], check=False)
        return proc.returncode == 0
    except Exception:
        return False

def _get_file_size(file_path: str) -> int:
    try:
        return os.path.getsize(file_path)
    except Exception:
        return -1

def handle():
    logger.info("Начата обработка запроса на генерацию системного отчета.")

    status = "GENERATION_STARTED" # Статус всегда "GENERATION_STARTED", так как тело запроса не ожидается
    # Удалена проверка статуса, так как он теперь всегда "GENERATION_STARTED"

    # 0) Если файла нет — это ошибка
    if not _file_exists(REPORT_FILE_PATH):
        logger.error(f"Файл {REPORT_FILE_NAME} не найден по пути {LOG_DIR}.")
        return {"result": "ERROR", "message": f"{REPORT_FILE_NAME} not found at {LOG_DIR}"}

    logger.info(f"Обнаружен {REPORT_FILE_NAME}. Начинаем наблюдение стабильности размера: окно={STABLE_WINDOW_SECONDS}с (без общего таймаута)")

    last_size = _get_file_size(REPORT_FILE_PATH)
    if last_size < 0:
        logger.error("Не удалось получить размер файла.")
        return {"result": "ERROR", "message": "unable to stat report file"}

    consecutive_stable_seconds = 0

    while True:
        time.sleep(1)

        # Файл мог исчезнуть в процессе
        if not _file_exists(REPORT_FILE_PATH):
            logger.error("Файл отчета исчез во время наблюдения.")
            return {"result": "ERROR", "message": "report file disappeared during observation"}

        current_size = _get_file_size(REPORT_FILE_PATH)
        logger.debug(f"Размер {REPORT_FILE_NAME}: текущий={current_size}, предыдущий={last_size}, стабильных секунд={consecutive_stable_seconds}")

        if current_size == last_size:
            consecutive_stable_seconds += 1
            if consecutive_stable_seconds >= STABLE_WINDOW_SECONDS:
                logger.info("Размер файла стабилен в течение требуемого окна. Отчет сформирован.")
                # Возвращаем размер файла в ответе для внешней проверки
                return {"result": "OK", "size": current_size}
        else:
            # Размер изменился — сбрасываем счетчик и продолжаем наблюдение
            consecutive_stable_seconds = 0
            last_size = current_size
