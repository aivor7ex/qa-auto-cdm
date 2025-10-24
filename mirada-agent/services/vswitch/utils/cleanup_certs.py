import os
import re
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Директория, в которой хранятся сертификаты на хост-системе
CERTS_DIR = "/opt/cdm-data/certs"
# Сколько последних пар сертификатов нужно оставить
VERSIONS_TO_KEEP = 1

def cleanup_old_certs():
    """
    Находит и удаляет старые TLS-сертификаты, оставляя только заданное
    количество последних версий.
    """
    logging.info(f"Начинаем очистку в директории: {CERTS_DIR}")

    if not os.path.isdir(CERTS_DIR):
        logging.error(f"Директория не найдена: {CERTS_DIR}")
        return

    # Паттерн для поиска UUID-имен сертификатов
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.crt$')
    
    cert_files = [f for f in os.listdir(CERTS_DIR) if uuid_pattern.match(f)]
    
    if not cert_files:
        logging.info("Не найдены сертификаты для очистки (с UUID в имени).")
        return

    # Сортируем файлы по дате их изменения (от новых к старым)
    cert_files.sort(key=lambda f: os.path.getmtime(os.path.join(CERTS_DIR, f)), reverse=True)

    # Определяем, какие файлы нужно удалить
    certs_to_delete = cert_files[VERSIONS_TO_KEEP:]

    if not certs_to_delete:
        logging.info("Нет старых сертификатов для удаления.")
        return

    logging.info(f"Найдено {len(certs_to_delete)} старых пар сертификатов для удаления.")

    for cert_file in certs_to_delete:
        key_file = cert_file.replace('.crt', '.key')
        cert_path = os.path.join(CERTS_DIR, cert_file)
        key_path = os.path.join(CERTS_DIR, key_file)

        # Удаляем .crt файл
        try:
            os.remove(cert_path)
            logging.info(f"Удален файл: {cert_path}")
        except OSError as e:
            logging.error(f"Ошибка при удалении файла {cert_path}: {e}")

        # Удаляем соответствующий .key файл
        if os.path.exists(key_path):
            try:
                os.remove(key_path)
                logging.info(f"Удален файл: {key_path}")
            except OSError as e:
                logging.error(f"Ошибка при удалении файла {key_path}: {e}")
        else:
            logging.warning(f"Не найден соответствующий ключ для {cert_file}: {key_path}")

    logging.info("Очистка старых сертификатов завершена.")

if __name__ == "__main__":
    cleanup_old_certs()
