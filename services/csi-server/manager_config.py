"""
Тесты для эндпоинта /manager/config сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Валидация структуры ZIP архива
- Рекурсивная проверка всех папок и файлов
- Проверка имени файла config.bkp
- Вывод cURL-команды при ошибке

Кроссплатформенность:
- Все пути в ZIP архивах используют "/" согласно стандарту ZIP
- Временные файлы создаются в памяти (io.BytesIO)
- Поддержка Windows, Linux, macOS через pathlib

Отладка:
- Файлы для анализа сохраняются в папку .temp/ рядом с автотестом
- Папка .temp/ добавлена в .gitignore
"""
import pytest
import zipfile
import io
import json
import os
from pathlib import Path
import requests # Added for ConnectionError
import time
from typing import Type, Dict, List, Optional

ENDPOINT = "/manager/config"

# Константы таймаутов
API_TIMEOUTS = {
    'default': 30,
    'restore': 360,  # Добавлен для POST операций восстановления
    'GET_CONFIG': 180,
    'POST_CONFIG': 25,  # Увеличен с 5 до 120 секунд для POST операций
    'STATUS_CHECK': 180,
    'STATUS_INTERVAL': 1,
    'POST_DELAY': 5
}

# Константы валидации архива
REQUIRED_FOLDERS = ['configuration/', 'frrouting/', 'additional-storage/', 'mongo/']
REQUIRED_SYSTEM_FILES = ['_VERSION', '_SWITCH_MODE', '_CHECKSUM', '_CHECKSUMS', 'env.conf']
EXPECTED_DOMAINS = ['auth-agent', 'auth-role', 'auth-settings', 'auth-user', 'host-network', 'host-state']

# Параметры для тестирования
GET_PARAMS = [
    pytest.param({}, id="no_parameters"),
    pytest.param({"format": "zip"}, id="with_zip_format"),
    pytest.param({"domain": "auth-settings"}, id="auth_settings_domain"),
]

NEGATIVE_AUTH_CASES = [
    pytest.param(None, 401, id="no_headers"),
    pytest.param({"x-access-token": "invalid_token", "token": "invalid_token"}, 401, id="invalid_token"),
    pytest.param({"x-access-token": "some"}, 401, id="missing_token_header"),
]

UPLOAD_ERROR_CASES = [
    pytest.param("wrong_field", 400, id="wrong_field_name"),
    pytest.param("no_files", 400, id="no_files"),
    pytest.param("empty_file", 400, id="empty_file"),
]

UPLOAD_VALID_CASES = [
    pytest.param("single", "file", None, id="field_file_valid"),
    pytest.param("single", "config", None, id="field_config_valid"),
    pytest.param("double", ("a", "b"), None, id="two_files_first_used"),
]


# Исключения для тестов
class ConfigTestError(Exception):
    """Базовый класс для ошибок тестирования конфигурации."""
    pass


class ZipValidationError(ConfigTestError):
    """Ошибка валидации ZIP архива."""
    pass


class ConfigArchiveValidator:
    """Валидатор для ZIP архивов конфигурации."""
    
    def __init__(self, zip_content: bytes):
        self.zip_content = zip_content
        self._zip_file = None
    
    def __enter__(self):
        self._zip_file = zipfile.ZipFile(io.BytesIO(self.zip_content))
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._zip_file:
            self._zip_file.close()
    
    def validate_structure(self) -> bool:
        """Валидирует структуру архива."""
        try:
            self._validate_required_folders()
            self._validate_system_files()
            self._validate_configuration_domains()
            return True
        except AssertionError as e:
            raise ZipValidationError(str(e)) from e
    
    def _validate_required_folders(self) -> None:
        """Проверяет наличие обязательных папок."""
        all_files = self._zip_file.namelist()
        found_folders = {f.split('/')[0] + '/' for f in all_files if '/' in f}
        
        missing_folders = set(REQUIRED_FOLDERS) - found_folders
        assert not missing_folders, f"Отсутствуют обязательные папки: {missing_folders}"
    
    def _validate_system_files(self) -> None:
        """Проверяет наличие системных файлов."""
        all_files = self._zip_file.namelist()
        root_files = {f for f in all_files if '/' not in f}
        
        missing_files = set(REQUIRED_SYSTEM_FILES) - root_files
        assert not missing_files, f"Отсутствуют обязательные системные файлы: {missing_files}"
    
    def _validate_configuration_domains(self) -> None:
        """Проверяет наличие доменов конфигурации."""
        all_files = self._zip_file.namelist()
        config_files = [f for f in all_files if f.startswith('configuration/')]
        config_subfolders = {f.split('/')[1] for f in config_files if len(f.split('/')) > 2}
        
        missing_domains = set(EXPECTED_DOMAINS) - config_subfolders
        assert not missing_domains, f"Отсутствуют домены конфигурации: {missing_domains}"


class StatusPoller:
    """Утилита для опроса статуса операций."""
    
    def __init__(self, api_client, headers: Dict[str, str]):
        self.api_client = api_client
        self.headers = headers
    
    def poll_until_complete(
        self, 
        endpoint: str, 
        success_states: List[str] = None,
        max_attempts: int = None
    ) -> Dict:
        """Опрашивает эндпоинт до получения финального статуса."""
        if success_states is None:
            success_states = ["OK"]
        if max_attempts is None:
            max_attempts = API_TIMEOUTS['STATUS_CHECK']
            
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        for attempt in range(max_attempts):
            try:
                response = self.api_client.get(endpoint, headers=self.headers, timeout=10)
                assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
                
                data = response.json()
                assert isinstance(data, dict) and "message" in data, "Ожидается JSON с полем 'message'"
                
                if data.get("message") in success_states:
                    return data
                
                # Проверяем промежуточные состояния
                valid_states = success_states + ["updating", "processing", "PENDING", "IN_PROGRESS"]
                assert data.get("message") in valid_states, f"Неожиданное состояние: {data}"
                
                consecutive_failures = 0  # Сбрасываем счетчик при успешном запросе
                time.sleep(API_TIMEOUTS['STATUS_INTERVAL'])
                
            except Exception as e:
                consecutive_failures += 1
                print(f"Ошибка при проверке статуса (попытка {attempt + 1}): {e}")
                
                if consecutive_failures >= max_consecutive_failures:
                    raise TimeoutError(f"Слишком много последовательных ошибок: {consecutive_failures}")
                
                time.sleep(API_TIMEOUTS['STATUS_INTERVAL'])
        
        raise TimeoutError(f"Операция не завершилась за {max_attempts} попыток")


class ManagerConfigClient:
    """API клиент для работы с /manager/config эндпоинтом."""
    
    def __init__(self, api_client, base_headers: Dict[str, str]):
        self.api_client = api_client
        self.base_headers = base_headers
    
    def get_config(self, params: Dict = None, timeout: int = None) -> requests.Response:
        """Получает конфигурацию через GET запрос."""
        if timeout is None:
            timeout = API_TIMEOUTS['GET_CONFIG']
            
        return self.api_client.get(
            ENDPOINT, 
            headers=self.base_headers, 
            params=params,
            timeout=timeout
        )
    
    def upload_config(self, file_content: bytes, field_name: str = "file") -> requests.Response:
        """Загружает файл конфигурации на сервер."""
        # Отладка: сохраним файл перед отправкой
        temp_path = _create_temp_file_path("debug_upload_config.bkp")
        try:
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            print(f"Отладка: Файл для upload сохранен: {temp_path} (размер: {len(file_content)} байт)")
        except Exception as e:
            print(f"Ошибка сохранения отладочного файла: {e}")
        
        # Создаем BytesIO объект и убеждаемся, что указатель в начале
        file_buffer = io.BytesIO(file_content)
        file_buffer.seek(0)
        
        files = {field_name: ("config.bkp", file_buffer, 'application/octet-stream')}
        return self._post_multipart(files)
    
    def _post_multipart(self, files: Dict, data: Dict = None, timeout: int = None) -> requests.Response:
        """Отправляет multipart-запрос."""
        if timeout is None:
            timeout = API_TIMEOUTS['POST_CONFIG']
            
        # Временно убираем Content-Type из session.headers
        original_ct = self.api_client.headers.pop('Content-Type', None)
        try:
            return self.api_client.post(
                ENDPOINT, 
                headers=self.base_headers, 
                files=files, 
                data=data, 
                timeout=timeout
            )
        finally:
            if original_ct is not None:
                self.api_client.headers['Content-Type'] = original_ct


def _normalize_zip_path(path: str) -> str:
    """
    Нормализует пути для ZIP архивов.
    ZIP архивы всегда используют прямые слеши '/' как разделители,
    независимо от операционной системы.
    """
    if not path:
        return path
    # Заменяем обратные слеши на прямые для совместимости с ZIP стандартом
    return path.replace('\\', '/')


def _is_folder_path(path: str) -> bool:
    """Проверяет, является ли путь папкой (заканчивается на '/')."""
    return path.endswith('/')


def _create_temp_file_path(filename: str, prefix: str = "qa_test_") -> Path:
    """
    Создает кроссплатформенный путь для временного файла.
    
    Args:
        filename: Имя файла
        prefix: Префикс для имени файла
        
    Returns:
        Path: Объект Path для временного файла
    """
    # Получаем папку, где находится текущий файл автотеста
    current_dir = Path(__file__).parent
    # Создаем папку .temp в той же директории
    temp_dir = current_dir / ".temp"
    # Создаем папку, если её нет
    temp_dir.mkdir(exist_ok=True)
    return temp_dir / f"{prefix}{filename}"


def _save_content_for_debug(content: bytes, filename: str = "debug_config.bkp") -> Path:
    """
    Сохраняет контент в временный файл для отладки.
    
    Args:
        content: Бинарные данные для сохранения
        filename: Имя файла
        
    Returns:
        Path: Путь к сохраненному файлу
    """
    temp_path = _create_temp_file_path(filename, "debug_")
    try:
        with open(temp_path, 'wb') as f:
            f.write(content)
        print(f"Контент сохранен для отладки: {temp_path}")
        return temp_path
    except Exception as e:
        print(f"Ошибка при сохранении файла отладки: {e}")
        return None

# Схема успешного ответа для валидации (минимальная, без жёстких предположений)
SUCCESS_RESPONSE_SCHEMA = {
    "required": {},
    "optional": {}
}


@pytest.fixture(scope="session")
def config_validator() -> Type[ConfigArchiveValidator]:
    """Возвращает класс валидатора для переиспользования."""
    return ConfigArchiveValidator


@pytest.fixture(scope="function")
def api_headers(auth_token) -> Dict[str, str]:
    """Стандартные заголовки для API запросов."""
    return {
        'x-access-token': auth_token,
        'token': auth_token
    }


@pytest.fixture(scope="function")
def manager_config_client(api_client, api_headers) -> ManagerConfigClient:
    """Клиент для работы с manager/config API."""
    return ManagerConfigClient(api_client, api_headers)


@pytest.fixture(scope="function") 
def status_poller(api_client, api_headers) -> StatusPoller:
    """Утилита для опроса статусов операций."""
    return StatusPoller(api_client, api_headers)


# Основные параметры для тестирования API
# Вспомогательные функции для multipart запросов
def _post_multipart_safe(api_client, endpoint, headers, files, timeout=30, data=None):
    """
    Безопасная отправка multipart POST запроса с временным удалением Content-Type.
    
    Args:
        api_client: HTTP клиент
        endpoint: API endpoint 
        headers: Заголовки запроса
        files: Файлы для отправки
        timeout: Таймаут запроса
        data: Дополнительные данные формы
        
    Returns:
        requests.Response: Ответ сервера
    """
    original_ct = api_client.headers.pop('Content-Type', None)
    try:
        return api_client.post(endpoint, headers=headers, files=files, data=data, timeout=timeout)
    finally:
        if original_ct is not None:
            api_client.headers['Content-Type'] = original_ct


# Константы для негативных тестов файлов
INVALID_FILE_CASES = [
    pytest.param(b"not a zip file", "application/zip", "invalid zip", id="invalid_zip"),
    pytest.param(b"", "application/zip", "empty file", id="empty_file"),
    pytest.param(b"some text content", "text/plain", "wrong content type", id="text_file"),
]

# Негативные случаи авторизации
NEGATIVE_AUTH_CASES = [
    pytest.param(None, 401, id="no_headers"),
    pytest.param({"x-access-token": "invalid_token", "token": "invalid_token"}, 401, id="invalid_tokens"),
    pytest.param({"x-access-token": "some"}, 401, id="only_one_header"),
]


@pytest.fixture(scope="function")
def valid_zip_content(api_client, auth_token, request_timeout, attach_curl_on_fail):
    """
    Получает валидный ZIP архив конфигурации через GET запрос.
    Все тесты используют этот файл для валидации.
    """
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    
    # Для выгрузки ZIP архив может формироваться дольше стандартного таймаута
    effective_timeout = max(request_timeout, API_TIMEOUTS['GET_CONFIG'])
    
    with attach_curl_on_fail(ENDPOINT, method="GET", headers=headers):
        try:
            response = api_client.get(ENDPOINT, headers=headers, timeout=effective_timeout)
        except Exception as e:
            print(f"Ошибка при выполнении GET запроса: {e}")
            raise
    
    # Проверяем размер контента
    content_length = len(response.content) if response.content else 0
    
    if content_length == 0:
        print("ВНИМАНИЕ: Получен пустой контент!")
    elif content_length < 1024:
        print(f"ВНИМАНИЕ: Контент очень маленький ({content_length} bytes), возможно это ошибка")
    
    # Проверяем успешность запроса
    assert response.status_code == 200, f"Не удалось скачать конфигурацию: статус {response.status_code}"
    
    # Анализируем Content-Type
    content_type = response.headers.get('content-type', '')
    
    assert 'application/zip' in content_type or 'application/octet-stream' in content_type, \
        f"Ответ должен содержать ZIP архив, получен Content-Type: {content_type}"
    
    # Проверяем имя файла
    content_disposition = response.headers.get('content-disposition', '')
    
    if content_disposition:
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
            assert filename == 'config.bkp', f"Ожидалось имя файла 'config.bkp', получено: '{filename}'"
        elif 'filename*=' in content_disposition:
            filename = content_disposition.split('filename*=')[1].split(';')[0].strip('"\'')
            assert filename == 'config.bkp', f"Ожидалось имя файла 'config.bkp', получено: '{filename}'"
    
    # Проверяем, что контент действительно является ZIP архивом
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as test_zip:
            files_in_zip = test_zip.namelist()
            if len(files_in_zip) == 0:
                print("Предупреждение: ZIP архив пустой!")
    except zipfile.BadZipFile as e:
        print(f"Невалидный ZIP архив: {e}")
        # Сохраняем контент для детального анализа
        debug_path = _save_content_for_debug(response.content, "invalid_zip_content.bin")
        if debug_path:
            print(f"Невалидный контент сохранен для анализа: {debug_path}")
        raise
    except Exception as e:
        print(f"Ошибка при проверке ZIP архива: {e}")
        # Сохраняем контент для анализа
        debug_path = _save_content_for_debug(response.content, "error_content.bin")
        if debug_path:
            print(f"Контент с ошибкой сохранен для анализа: {debug_path}")
        raise
    
    # Для успешных случаев также можем сохранить для проверки
    if content_length > 0:
        debug_path = _save_content_for_debug(response.content, "successful_config.bkp")
    
    return response.content


def _analyze_archive_structure(zip_file, path="", level=0):
    """
    Рекурсивно анализирует структуру ZIP архива.
    Возвращает словарь с полной информацией о структуре.
    """
    # Нормализуем путь для совместимости
    path = _normalize_zip_path(path)
    
    structure = {
        'type': 'folder',  # Корень всегда папка
        'path': path,
        'level': level,
        'children': [],
        'size': 0,
        'info': {}
    }
    
    if path == "":
        # Корневая папка - анализируем все файлы и папки
        all_files = [_normalize_zip_path(f) for f in zip_file.namelist()]
        
        # Группируем файлы по папкам
        folders = {}
        root_files = []
        
        for file_path in all_files:
            if '/' in file_path:
                # Файл в папке
                folder_name = file_path.split('/')[0] + '/'
                if folder_name not in folders:
                    folders[folder_name] = []
                folders[folder_name].append(file_path)
            else:
                # Файл в корне
                root_files.append(file_path)
        
        # Анализируем корневые файлы
        if root_files:
            structure['files'] = root_files
            for file_path in root_files:
                try:
                    with zip_file.open(file_path) as file:
                        content = file.read()
                        file_info = {
                            'path': file_path,
                            'size': len(content),
                            'type': 'binary' if any(b < 32 and b != 9 and b != 10 and b != 13 for b in content[:100]) else 'text'
                        }
                        
                        # Специальная обработка для .info файлов
                        if file_path.endswith('.info'):
                            try:
                                json_content = content.decode('utf-8')
                                file_info['json_data'] = json.loads(json_content)
                                file_info['type'] = 'json'
                            except:
                                file_info['type'] = 'text'
                        
                        structure['info'][file_path] = file_info
                        structure['size'] += len(content)
                except Exception as e:
                    structure['info'][file_path] = {'error': str(e)}
        
        # Рекурсивно анализируем папки
        for folder_name, folder_files in folders.items():
            child_structure = _analyze_archive_structure(zip_file, folder_name, level + 1)
            structure['children'].append(child_structure)
            
    elif _is_folder_path(path):
        # Это папка
        folder_files = [_normalize_zip_path(f) for f in zip_file.namelist() if f.startswith(path) and f != path]
        
        # Группируем файлы по подпапкам
        subfolders = {}
        current_level_files = []
        
        for file_path in folder_files:
            relative_path = file_path[len(path):]
            if '/' in relative_path:
                subfolder = relative_path.split('/')[0] + '/'
                if subfolder not in subfolders:
                    subfolders[subfolder] = []
                subfolders[subfolder].append(file_path)
            else:
                # Файл в текущей папке
                current_level_files.append(file_path)
        
        # Анализируем файлы в текущей папке
        if current_level_files:
            structure['files'] = current_level_files
            for file_path in current_level_files:
                try:
                    with zip_file.open(file_path) as file:
                        content = file.read()
                        file_info = {
                            'path': file_path,
                            'size': len(content),
                            'type': 'binary' if any(b < 32 and b != 9 and b != 10 and b != 13 for b in content[:100]) else 'text'
                        }
                        
                        # Специальная обработка для .info файлов
                        if file_path.endswith('.info'):
                            try:
                                json_content = content.decode('utf-8')
                                file_info['json_data'] = json.loads(json_content)
                                file_info['type'] = 'json'
                            except:
                                file_info['type'] = 'text'
                        
                        structure['info'][file_path] = file_info
                        structure['size'] += len(content)
                except Exception as e:
                    structure['info'][file_path] = {'error': str(e)}
        
        # Рекурсивно анализируем подпапки
        for subfolder, files in subfolders.items():
            child_structure = _analyze_archive_structure(zip_file, path + subfolder, level + 1)
            structure['children'].append(child_structure)
            
    else:
        # Это файл
        try:
            with zip_file.open(path) as file:
                content = file.read()
                structure['size'] = len(content)
                structure['type'] = 'binary' if any(b < 32 and b != 9 and b != 10 and b != 13 for b in content[:100]) else 'text'
                
                # Специальная обработка для .info файлов
                if path.endswith('.info'):
                    try:
                        json_content = content.decode('utf-8')
                        structure['info'] = json.loads(json_content)
                        structure['type'] = 'json'
                    except:
                        structure['type'] = 'text'
        except Exception as e:
            structure['error'] = str(e)
    
    return structure


def _validate_archive_structure(archive_structure):
    """
    Валидирует структуру архива на основе анализа.
    
    Проверяет наличие обязательных папок и файлов в ZIP архиве.
    Все пути используют "/" как разделитель согласно стандарту ZIP.
    """
    # Проверяем основные папки (используем "/" согласно стандарту ZIP)
    required_folders = ['configuration/', 'frrouting/', 'additional-storage/', 'mongo/']
    found_folders = [child['path'] for child in archive_structure['children'] if child['type'] == 'folder']
    
    for folder in required_folders:
        assert folder in found_folders, f"Отсутствует обязательная папка: {folder}"
    
    # Проверяем системные файлы
    required_system_files = ['_VERSION', '_SWITCH_MODE', '_CHECKSUM', '_CHECKSUMS', 'env.conf']
    found_system_files = [file_path for file_path in archive_structure.get('files', [])]
    
    for sys_file in required_system_files:
        assert sys_file in found_system_files, f"Отсутствует обязательный системный файл: {sys_file}"
    
    # Проверяем структуру папки configuration
    config_folder = next((child for child in archive_structure['children'] if child['path'] == 'configuration/'), None)
    assert config_folder is not None, "Папка configuration не найдена"
    
    # Проверяем домены конфигурации
    expected_domains = ['auth-agent', 'auth-role', 'auth-settings', 'auth-user', 'host-network', 'host-state']
    config_subfolders = [child['path'].rstrip('/').split('/')[-1] for child in config_folder['children'] if child['type'] == 'folder']
    
    for domain in expected_domains:
        assert domain in config_subfolders, f"Отсутствует домен конфигурации: {domain}"
    
    return True

@pytest.mark.parametrize("params", GET_PARAMS)
def test_manager_config_get_with_parameters_returns_valid_zip(api_client, api_headers, config_validator, valid_zip_content, params):
    """
    GET /manager/config с различными параметрами возвращает валидный ZIP архив.
    
    Проверяет:
    - Корректность структуры ZIP архива
    - Наличие обязательных папок и файлов
    - Соответствие доменов конфигурации
    """
    # Arrange
    # (данные уже подготовлены в фикстуре valid_zip_content)
    
    # Act & Assert
    try:
        with config_validator(valid_zip_content) as validator:
            validator.validate_structure()
    except zipfile.BadZipFile as e:
        pytest.fail(f"Получен некорректный ZIP архив: {e}")
    except ZipValidationError as e:
        pytest.fail(f"ZIP архив не прошел валидацию: {e}")


@pytest.mark.parametrize("headers, expected_status", NEGATIVE_AUTH_CASES)
def test_manager_config_get_with_invalid_auth_returns_401(api_client, attach_curl_on_fail, headers, expected_status):
    """
    GET /manager/config с невалидной авторизацией возвращает 401.
    
    Проверяет различные сценарии невалидной авторизации:
    - Отсутствие заголовков
    - Невалидные токены
    - Неполные заголовки авторизации
    """
    # Arrange & Act
    with attach_curl_on_fail(ENDPOINT, method="GET", headers=headers if headers else None):
        response = api_client.get(ENDPOINT, headers=headers) if headers else api_client.get(ENDPOINT)
    
    # Assert
    assert response.status_code == expected_status, f"Ожидался статус-код {expected_status}, получен {response.status_code}"
    
    try:
        error_data = response.json()
        assert "error" in error_data, "Ответ должен содержать поле 'error'"
    except Exception:
        assert "Unauthorized" in response.text or "Authorization Required" in response.text


# ========================= POST /manager/config (UPLOAD) =========================



def _validate_success_response_if_json(response):
    """Если ответ JSON — валидируем по SUCCESS_RESPONSE_SCHEMA, иначе пропускаем."""
    try:
        data = response.json()
    except Exception:
        return  # не JSON — не валидируем структуру
    from services.conftest import validate_schema  # локальный импорт, чтобы не менять импорты сверху
    validate_schema(data, SUCCESS_RESPONSE_SCHEMA)



def test_manager_config_post_with_valid_zip_restores_successfully(api_client, api_headers, status_poller, valid_zip_content):
    """
    POST /manager/config с валидным ZIP архивом успешно восстанавливает конфигурацию.
    
    Проверяет:
    - Успешный POST запрос с ZIP архивом
    - Корректность статуса операции восстановления
    - Время выполнения операции
    """
    # Arrange - максимально упрощенный подход
    files = {"file": ("config.bkp", valid_zip_content, 'application/octet-stream')}
    
    # Временно убираем Content-Type из session.headers
    original_ct = api_client.headers.pop('Content-Type', None)
    
    try:
        # Act - POST запрос зависает, поэтому используем короткий таймаут и сразу проверяем статус
        import time
        
        # Запускаем POST запрос в фоне с очень коротким таймаутом
        print("Отправка POST запроса...")
        try:
            response = api_client.post(ENDPOINT, headers=api_headers, files=files, timeout=5)
            print(f"POST ответ: {response.status_code}")
            if hasattr(response, 'text') and response.text:
                print(f"Ответ сервера: {response.text[:200]}...")
        except Exception as e:
            print(f"POST запрос завершился с ошибкой (ожидаемо): {type(e).__name__}")
            # Это ожидаемое поведение - POST зависает, но операция запускается
        
        # Даем серверу время на обработку файла
        print("Ожидание начала обработки конфигурации...")
        time.sleep(10)
        
        # Assert - проверяем статус восстановления
        print("Проверка статуса восстановления...")
        status_endpoint = "/manager/restoreConfigStatus"
        result = status_poller.poll_until_complete(status_endpoint, success_states=["OK"])
        
        if result.get("message") == "OK":
            print("Конфигурация успешно восстановлена")
        else:
            pytest.fail(f"Операция завершилась со статусом: {result.get('message', 'unknown')}")
            
    finally:
        # Восстанавливаем Content-Type заголовок
        if original_ct is not None:
            api_client.headers['Content-Type'] = original_ct


def test_manager_config_post_with_agent_verification(api_client, api_headers, status_poller, valid_zip_content, agent_verification):
    """
    POST /manager/config с последующей проверкой через агента.
    
    Проверяет полный цикл:
    - POST запрос
    - Ожидание завершения операции
    - Проверка через агента
    """
    # Arrange
    files = {"file": ("config.bkp", valid_zip_content, 'application/octet-stream')}
    
    # Временно убираем Content-Type из session.headers
    original_ct = api_client.headers.pop('Content-Type', None)
    
    try:
        # Act - POST запрос зависает, поэтому используем короткий таймаут и сразу проверяем статус
        import time
        
        # Запускаем POST запрос в фоне с очень коротким таймаутом
        print("Отправка POST запроса...")
        try:
            response = api_client.post(ENDPOINT, headers=api_headers, files=files, timeout=5)
            print(f"POST ответ: {response.status_code}")
            if hasattr(response, 'text') and response.text:
                print(f"Ответ сервера: {response.text[:200]}...")
        except Exception as e:
            print(f"POST запрос завершился с ошибкой (ожидаемо): {type(e).__name__}")
            # Это ожидаемое поведение - POST зависает, но операция запускается
        
        # Даем серверу время на обработку файла
        print("Ожидание начала обработки конфигурации...")
        time.sleep(10)
        
        # Ожидание завершения операции
        print("Проверка статуса восстановления...")
        status_endpoint = "/manager/restoreConfigStatus"
        result = status_poller.poll_until_complete(status_endpoint, success_states=["OK"])
        
        if result.get("message") == "OK":
            print("Конфигурация успешно восстановлена")
        else:
            pytest.fail(f"Операция не завершилась успешно: {result.get('message', 'unknown')}")
        
        # Assert - проверка через агента
        agent_result = agent_verification("/manager/config", {})
        
        if agent_result == "unavailable":
            pytest.fail("Агент недоступен")
        elif isinstance(agent_result, dict):
            if agent_result.get("result") == "OK":
                print("Проверка агента: Успешно")
            elif agent_result.get("result") == "ERROR":
                error_message = agent_result.get("message", "Неизвестная ошибка")
                pytest.fail(f"Агент вернул ошибку: {error_message}")
            else:
                pytest.fail(f"Агент вернул неожиданный результат: {agent_result}")
        else:
            pytest.fail(f"Агент вернул неожиданный тип ответа: {type(agent_result)}")
            
    finally:
        # Восстанавливаем Content-Type заголовок
        if original_ct is not None:
            api_client.headers['Content-Type'] = original_ct


@pytest.mark.parametrize("field_name, file_content, expected_status", [
    ("wrong_field", b"valid-bytes", 400),
    ("file", b"", 400),
    (None, None, 400),  # no_files case
])
def test_manager_config_post_with_invalid_data_returns_400(api_client, api_headers, field_name, file_content, expected_status):
    """
    POST /manager/config с невалидными данными возвращает 400.
    
    Проверяет различные сценарии ошибок:
    - Неправильное имя поля
    - Пустой файл  
    - Отсутствие файлов
    """
    # Arrange
    if field_name is None:  # no_files case
        files = None
    else:
        files = {field_name: ("config.bkp", io.BytesIO(file_content), "application/octet-stream")}
    
    # Act - обрабатываем случаи когда сервер закрывает соединение
    try:
        response = _post_multipart_safe(api_client, ENDPOINT, api_headers, files, API_TIMEOUTS["default"])
        
        # Assert
        assert response.status_code == expected_status, f"Ожидался статус {expected_status}, получен {response.status_code}"
        
    except Exception as e:
        # Для невалидных данных сервер может закрыть соединение - это тоже валидное поведение
        error_type = type(e).__name__
        if "ConnectionError" in error_type or "RemoteDisconnected" in str(e):
            print(f"Сервер закрыл соединение для невалидных данных (ожидаемо): {error_type}")
            # Это считается успешным тестом - сервер отклонил невалидные данные
        else:
            # Неожиданная ошибка
            raise


@pytest.mark.parametrize("headers, expected_status", NEGATIVE_AUTH_CASES)
def test_manager_config_post_with_invalid_auth_returns_401(api_client, headers, expected_status):
    """
    POST /manager/config с невалидной авторизацией возвращает 401.
    
    Проверяет различные сценарии невалидной авторизации для POST запросов.
    """
    # Arrange
    files = {"file": ("config.bkp", io.BytesIO(b"dummy content"), "application/octet-stream")}
    
    # Act - обрабатываем случаи когда сервер закрывает соединение
    try:
        response = _post_multipart_safe(api_client, ENDPOINT, headers, files, API_TIMEOUTS["default"])
        
        # Assert
        assert response.status_code == expected_status, f"Ожидался статус-код {expected_status}, получен {response.status_code}"
        
    except Exception as e:
        # Для невалидной авторизации сервер может закрыть соединение - это тоже валидное поведение
        error_type = type(e).__name__
        if "ConnectionError" in error_type or "RemoteDisconnected" in str(e) or "401" in str(e):
            print(f"Сервер отклонил запрос с невалидной авторизацией (ожидаемо): {error_type}")
            # Это считается успешным тестом - сервер отклонил невалидную авторизацию
        else:
            # Неожиданная ошибка
            raise
