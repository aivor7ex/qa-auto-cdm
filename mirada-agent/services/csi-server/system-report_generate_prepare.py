import logging
import os
import subprocess
from marshmallow import Schema, fields, INCLUDE

logger = logging.getLogger(__name__)

# Путь к файлу отчета
SYSTEM_REPORT_PATH = "/opt/cdm-data/mirada-logs/system-report.log.zip"

class SystemReportGeneratePrepareRequestSchema(Schema):
    # Этот эндпоинт не требует тела запроса, но для совместимости Flask-Smorest может потребоваться пустая схема
    class Meta:
        unknown = INCLUDE

class SystemReportGeneratePrepareResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

def handle():
    logger.info(f"Начата обработка запроса на подготовку системного отчета: удаление {SYSTEM_REPORT_PATH}")
    
    cmd = ["rm", "-rf", SYSTEM_REPORT_PATH]
    logger.info("Выполняется команда: %s", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info(f"Файл {SYSTEM_REPORT_PATH} успешно удален (или не существовал).")
            return {"result": "OK"}
        else:
            error_message = result.stderr.strip() or "Неизвестная ошибка при удалении файла."
            logger.error(f"Ошибка при удалении файла {SYSTEM_REPORT_PATH}: rc={result.returncode}, stderr={error_message}")
            return {"result": "ERROR", "message": error_message}
    except Exception as e:
        logger.error(f"Исключение при выполнении команды удаления файла: {e}")
        return {"result": "ERROR", "message": f"Внутренняя ошибка: {str(e)}"}
