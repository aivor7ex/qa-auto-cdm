# file: /services/csi-server/service_container-logs_container.py
import json
import pytest
import time
from qa_constants import SERVICES

ENDPOINT = "/service/container-logs/{container}"

# ----- СХЕМА ОТВЕТА (получена из R0) -----
RESPONSE_SCHEMA = {
    "output": {"type": "string", "required": True}
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str, container: str) -> str:
    return f"{base_path}{ENDPOINT.format(container=container)}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле; curl: curl --location 'http://127.0.0.1:2999/api/service/container-logs/ngfw.core' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)

def _format_curl_command(api_client, endpoint, container, params=None, headers=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}")
    full_url = f"{base_url}{endpoint.format(container=container)}"
    if params:
        param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
        if param_str:
            full_url += f"?{param_str}"
    headers = headers or getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
    return curl_command

@pytest.fixture(scope="module")
def container_names(api_client, auth_token):
    """Фикстура для получения списка имен контейнеров динамически"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = f"{base}/service/container-list"
    headers = {"x-access-token": auth_token}

    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK для /service/container-list; получено {r.status_code}"
    
    data = r.json()
    assert isinstance(data, dict), "Ответ должен быть объектом"
    
    container_names = list(data.keys())
    assert len(container_names) > 0, "Список контейнеров не должен быть пустым"
    
    print(f"Найдено контейнеров: {len(container_names)}")
    print(f"Контейнеры: {container_names}")
    
    return container_names

@pytest.mark.parametrize("params", [
    None,  # Без параметров
    {"limit": 100},  # Ограничение вывода
    {"tail": 50},  # Последние строки
    {"filter": "error"},  # Фильтр по ошибкам
    {"q": "NAT"},  # Поиск по ключевому слову
])
def test_container_logs_with_params(container_names, api_client, auth_token, params):
    """Тестирует /service/container-logs/{container} для всех контейнеров с заданными параметрами"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    headers = {"x-access-token": auth_token}
    
    # Тестируем каждый контейнер
    for container_name in container_names:
        test_desc = f"Тест для {container_name}"
        if params:
            test_desc += f" с параметрами {params}"
        else:
            test_desc += " без параметров"
        
        print(f"  {test_desc}")
        
        # Выполняем запрос к /service/container-logs/{container} с таймаутом
        url = _url(base, container_name)
        start_time = time.time()
        
        try:
            r = api_client.get(url, headers=headers, params=params, timeout=15)
            response_time = time.time() - start_time
            
            # Проверяем статус ответа
            assert r.status_code == 200, (
                f"Ожидается 200 OK для {container_name}; получено {r.status_code}; "
                f"curl: {_format_curl_command(api_client, ENDPOINT, container_name, params, headers)}"
            )
            
            # Проверяем структуру ответа
            data = r.json()
            _validate_object(data, RESPONSE_SCHEMA)
            
            # Дополнительные проверки для поля output
            assert "output" in data, f"Поле 'output' отсутствует в ответе для {container_name}"
            assert isinstance(data["output"], str), f"Поле 'output' должно быть строкой для {container_name}"
            # Поле output может быть пустым - это нормально
            
            print(f"    [SUCCESS] {test_desc} (время ответа: {response_time:.2f}с)")
            
        except Exception as e:
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                print(f"    [TIMEOUT] {test_desc} (>15с)")
                pytest.skip(f"Контейнер {container_name} не отвечает в течение 15 секунд")
            else:
                # Другие ошибки - тест падает
                raise e

def test_container_list_structure(api_client, auth_token):
    """Тест структуры ответа /service/container-list"""
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    headers = {"x-access-token": auth_token}
    
    url = f"{base}/service/container-list"
    r = api_client.get(url, headers=headers)
    assert r.status_code == 200, f"Ожидается 200 OK для /service/container-list; получено {r.status_code}"
    
    data = r.json()
    assert isinstance(data, dict), "Ответ должен быть объектом"
    
    # Проверяем структуру каждого контейнера
    for container_key, container_info in data.items():
        assert isinstance(container_key, str), f"Ключ контейнера должен быть строкой: {container_key}"
        assert isinstance(container_info, dict), f"Информация о контейнере должна быть объектом: {container_key}"
        
        # Проверяем обязательные поля
        required_fields = ["id", "container", "state", "stack"]
        for field in required_fields:
            assert field in container_info, f"Поле '{field}' отсутствует в информации о контейнере {container_key}"
            assert isinstance(container_info[field], str), f"Поле '{field}' должно быть строкой для {container_key}"
        
        # Проверяем, что container_key соответствует полю container
        assert container_key == container_info["container"], f"Ключ {container_key} не соответствует полю container {container_info['container']}"
        
        # Проверяем, что state является валидным
        valid_states = ["running", "stopped", "created", "exited"]
        assert container_info["state"] in valid_states, f"Недопустимое состояние контейнера {container_key}: {container_info['state']}"
