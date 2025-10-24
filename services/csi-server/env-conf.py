"""
Тесты для эндпоинта /env-conf сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (объект конфигурации)
- Валидация IP адресов и портов
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
import re
import ipaddress
from collections.abc import Mapping, Sequence

ENDPOINT = "/env-conf"

# Схема ответа для конфигурации окружения
ENV_CONF_SCHEMA = {
    "type": "object",
    "properties": {
        "BUS_BLOCK_STANZA": {"type": "string"},
        "BUS_CONTAINER_BLOCK_CHANNEL": {"type": "string"},
        "BUS_SOCKET": {"type": "string"},
        "COMMON_BIND_ADDRESS": {"type": "string"},
        "CONFIGURATION_CHANNEL": {"type": "string"},
        "CONFIGURATION_DB": {"type": "string"},
        "CSI_HOST": {"type": "string"},
        "CSI_NET": {"type": "string"},
        "CSI_PASSWORD": {"type": "string"},
        "CSI_PORT": {"type": "string"},
        "CSI_SSH_TERMINAL_HOST": {"type": "string"},
        "CSI_SSH_TERMINAL_PASSWORD": {"type": "string"},
        "CSI_SSH_TERMINAL_PORT": {"type": "string"},
        "CSI_SSH_TERMINAL_USERNAME": {"type": "string"},
        "CSI_TELNET_TERMINAL_HOST": {"type": "string"},
        "CSI_TELNET_TERMINAL_LOGIN_PROMPT": {"type": "string"},
        "CSI_TELNET_TERMINAL_PASSWORD": {"type": "string"},
        "CSI_TELNET_TERMINAL_PASSWORD_PROMPT": {"type": "string"},
        "CSI_TELNET_TERMINAL_PORT": {"type": "string"},
        "CSI_TELNET_TERMINAL_PROMPT": {"type": "string"},
        "CSI_TELNET_TERMINAL_TIMEOUT": {"type": "string"},
        "CSI_TELNET_TERMINAL_USERNAME": {"type": "string"},
        "DEVICE_NAME": {"type": "string"},
        "DNS_RESOLVERS": {"type": "string"},
        "DOCKER_NET_GW": {"type": "string"},
        "DOCKER_START_POLICY": {"type": "string"},
        "DOCKER_SUBNET": {"type": "string"},
        "DOMAIN_NAME": {"type": "string"},
        "ENABLE_FIREWALL": {"type": "string"},
        "HOST_CHANNEL": {"type": "string"},
        "HOST_IP": {"type": "string"},
        "INTERFACES": {"type": "string"},
        "KIBANA_PORT": {"type": "string"},
        "LINUX_CLUSTER_IF": {"type": "string"},
        "LINUX_DATA_IF": {"type": "string"},
        "LINUX_IDS_IF": {"type": "string"},
        "LINUX_MANAGEMENT_IF": {"type": "string"},
        "LINUX_OF_CONTROLLER_IF": {"type": "string"},
        "LINUX_OF_CONTROLLER_IP": {"type": "string"},
        "LINUX_OF_CONTROLLER_MASK": {"type": "string"},
        "NETNS": {"type": "string"},
        "NETNS_INTERFACES": {"type": "string"},
        "NETWORK_BACKEND": {"type": "string"},
        "NGFW_IP": {"type": "string"},
        "PCI_DEVICES": {"type": "string"},
        "PRODUCT_PATH": {"type": "string"},
        "PROXY_PORT": {"type": "string"},
        "PROXY_PORT_SSL": {"type": "string"},
        "SESSION_TRACKER_CPUS": {"type": "string"},
        "SHARED_NET": {"type": "string"},
        "SQUID_MAX_SCANNING_FILESIZE": {"type": "string"},
        "SQUID_REDIRECT_URL": {"type": "string"},
        "SSL_CERT_FILENAME": {"type": "string"},
        "SSL_CERTIFICATES_PATH": {"type": "string"},
        "SSL_KEY_FILENAME": {"type": "string"},
        "SSL_ROOT_CERT_FILENAME": {"type": "string"},
        "SSL_ROOT_KEY_FILENAME": {"type": "string"},
        "STORAGE_DIRECTORY": {"type": "string"},
        "SWITCH_DATA_PORT": {"type": "string"},
        "SWITCH_IDS_PORT": {"type": "string"},
        "SWITCH_MANAGEMENT_IP": {"type": "string"},
        "SWITCH_MODE": {"type": "string"},
        "SWITCH_PORT_PREFIX": {"type": "string"},
        "SWITCH_RESERVED_PORTS": {"type": "string"},
        "SWITCH_SERIAL_DEVICE": {"type": "string"},
        "SWITCH_SERIAL_SPEED": {"type": "string"},
        "SWITCH_TYPE": {"type": "string"},
        "SYSTEM_IMAGE": {"type": "string"},
        "TLS_BRIDGE_SSL_PORT": {"type": "string"},
        "TLS_BRIDGE_TCP_PORT": {"type": "string"},
        "TLS_PROXY_BRIDGE_SSL_PORT": {"type": "string"},
        "TLS_PROXY_BRIDGE_TCP_PORT": {"type": "string"},
        "UPLOAD_DIRECTORY": {"type": "string"},
        "UPLOAD_USER": {"type": "string"},
        "VOLUME_PATH": {"type": "string"},
        "VPP_ACL_MAX_SESSIONS": {"type": "string"},
        "VPP_ACL_SESSION_TCP_IDLE_TIMEOUT": {"type": "string"},
        "VPP_ACL_SESSION_TCP_TRANSIENT_IDLE_TIMEOUT": {"type": "string"},
        "VPP_ACL_SESSION_UDP_IDLE_TIMEOUT": {"type": "string"},
        "VPP_BRIDGE": {"type": "string"},
        "VPP_DPDK_DEVS": {"type": "string"},
        "VPP_DPDK_DUMMY_DEVS": {"type": "string"},
        "VPP_HEAPSIZE": {"type": "string"},
        "VPP_IP4_CONN_HASH_BUCKETS": {"type": "string"},
        "VPP_IP4_CONN_HASH_MEMORY": {"type": "string"},
        "VPP_PREALLOCATE_ACLS": {"type": "string"},
        "VPP_STATSEG_SIZE": {"type": "string"}
    },
}

def is_valid_ip(ip_string):
    """Проверяет, является ли строка валидным IP адресом."""
    if not isinstance(ip_string, str):
        return False
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False

def is_valid_port(port_string):
    """Проверяет, является ли строка валидным номером порта (мягкая проверка).

    Допускаются форматы:
    - одно число 0..65535
    - список чисел, разделенных запятыми (каждое 0..65535)
    - диапазон чисел в виде start-end (0..65535 и start <= end)
    - спец-значения: auto|none|off|disabled (в некоторых окружениях)
    """
    if not isinstance(port_string, str):
        return False

    s = port_string.strip()
    if s.lower() in {"auto", "none", "off", "disabled"}:
        return True

    def _is_valid_single(p: str) -> bool:
        if not p.isdigit():
            return False
        try:
            v = int(p)
            return 0 <= v <= 65535
        except ValueError:
            return False

    # Разрешаем список элементов, разделенных ',', ';' или пробелами
    tokens = [t for t in re.split(r"[;,\s]+", s) if t]
    if not tokens:
        return False

    def _is_valid_token(token: str) -> bool:
        if "-" in token:
            a, b = token.split("-", 1)
            return _is_valid_single(a.strip()) and _is_valid_single(b.strip()) and int(a) <= int(b)
        return _is_valid_single(token)

    return all(_is_valid_token(t) for t in tokens)

def _check_types_recursive(obj, schema):
    """Рекурсивно проверяет типы данных в объекте на соответствие схеме."""
    if "anyOf" in schema:
        assert any(_try_type(obj, s) for s in schema["anyOf"]), f"Тип {type(obj)} не соответствует ни одной из схем в anyOf"
        return

    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(obj, Mapping), f"Ожидался объект (dict), получено: {type(obj).__name__}"
        for key, prop_schema in schema.get("properties", {}).items():
            if key in obj:
                _check_types_recursive(obj[key], prop_schema)
        for required_key in schema.get("required", []):
            assert required_key in obj, f"Обязательное поле '{required_key}' отсутствует в объекте"
    elif schema_type == "array":
        assert isinstance(obj, Sequence) and not isinstance(obj, str), f"Ожидался список (list/tuple), получено: {type(obj).__name__}"
        for item in obj:
            _check_types_recursive(item, schema["items"])
    elif schema_type == "string":
        assert isinstance(obj, str), f"Поле должно быть строкой (string), получено: {type(obj).__name__}"
        # Проверяем паттерн если он задан
        if "pattern" in schema:
            pattern = schema["pattern"]
            assert re.match(pattern, obj), f"Строка не соответствует паттерну {pattern}: {obj}"
    elif schema_type == "integer":
        assert isinstance(obj, int), f"Поле должно быть целым числом (integer), получено: {type(obj).__name__}"
    elif schema_type == "boolean":
        assert isinstance(obj, bool), f"Поле должно быть булевым (boolean), получено: {type(obj).__name__}"
    elif schema_type == "null":
        assert obj is None, "Поле должно быть null"


def _try_type(obj, schema):
    """Вспомогательная функция для проверки типа в 'anyOf'."""
    try:
        _check_types_recursive(obj, schema)
        return True
    except AssertionError:
        return False


def _format_curl_command(api_client, endpoint, params, auth_token=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    # Базовые заголовки
    headers = getattr(api_client, 'headers', {}).copy()
    
    # Добавляем заголовки авторизации если токен предоставлен
    if auth_token:
        headers['x-access-token'] = auth_token
        headers['token'] = auth_token
    
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl --location '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


# Осмысленная параметризация для тестирования эндпоинта /env-conf
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P03: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P04: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P05: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P06: indent_4"),
    
    # --- Фильтрация по секциям ---
    pytest.param({"section": "network"}, 200, id="P07: section_network"),
    pytest.param({"section": "security"}, 200, id="P08: section_security"),
    pytest.param({"section": "docker"}, 200, id="P09: section_docker"),
    pytest.param({"section": "ssl"}, 200, id="P10: section_ssl"),
    pytest.param({"section": "vpp"}, 200, id="P11: section_vpp"),
    pytest.param({"section": "switch"}, 200, id="P12: section_switch"),
    
    # --- Фильтрация по ключам ---
    pytest.param({"key": "CSI_HOST"}, 200, id="P13: key_csi_host"),
    pytest.param({"key": "CSI_PORT"}, 200, id="P14: key_csi_port"),
    pytest.param({"key": "DEVICE_NAME"}, 200, id="P15: key_device_name"),
    pytest.param({"key": "HOST_IP"}, 200, id="P16: key_host_ip"),
    pytest.param({"key": "NGFW_IP"}, 200, id="P17: key_ngfw_ip"),
    pytest.param({"key": "SWITCH_MANAGEMENT_IP"}, 200, id="P18: key_switch_management_ip"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "CSI"}, 200, id="P19: search_csi"),
    pytest.param({"search": "IP"}, 200, id="P20: search_ip"),
    pytest.param({"search": "PORT"}, 200, id="P21: search_port"),
    pytest.param({"search": "VPP"}, 200, id="P22: search_vpp"),
    pytest.param({"search": "SWITCH"}, 200, id="P23: search_switch"),
    pytest.param({"q": "network"}, 200, id="P24: query_network"),
    pytest.param({"q": "security"}, 200, id="P25: query_security"),
    pytest.param({"q": "docker"}, 200, id="P26: query_docker"),
    
    # --- Фильтрация по значениям ---
    pytest.param({"value": "127.0.0.1"}, 200, id="P27: value_127_0_0_1"),
    pytest.param({"value": "80"}, 200, id="P28: value_80"),
    pytest.param({"value": "admin"}, 200, id="P29: value_admin"),
    pytest.param({"value": "true"}, 200, id="P30: value_true"),
    pytest.param({"value": "false"}, 200, id="P31: value_false"),
    
    # --- Комбинированные фильтры ---
    pytest.param({"section": "network", "search": "IP"}, 200, id="P32: section_network_search_ip"),
    pytest.param({"section": "security", "key": "CSI_PASSWORD"}, 200, id="P33: section_security_key_password"),
    pytest.param({"search": "CSI", "value": "127.0.0.1"}, 200, id="P34: search_csi_value_localhost"),
    pytest.param({"key": "CSI_HOST", "pretty": "true"}, 200, id="P35: key_host_pretty"),
    
    # --- Специальные параметры ---
    pytest.param({"include_sensitive": "true"}, 200, id="P36: include_sensitive_true"),
    pytest.param({"include_sensitive": "false"}, 200, id="P37: include_sensitive_false"),
    pytest.param({"exclude_empty": "true"}, 200, id="P38: exclude_empty_true"),
    pytest.param({"exclude_empty": "false"}, 200, id="P39: exclude_empty_false"),
    pytest.param({"sort": "key"}, 200, id="P40: sort_by_key"),
    pytest.param({"sort": "value"}, 200, id="P41: sort_by_value"),
    pytest.param({"sort": "-key"}, 200, id="P42: sort_by_key_desc"),
    pytest.param({"sort": "-value"}, 200, id="P43: sort_by_value_desc"),
]


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_env_conf_parametrized(api_client, auth_token, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /env-conf.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        headers = {"x-access-token": auth_token, "token": auth_token}
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            # Проверяем структуру конфигурации
            _check_types_recursive(data, ENV_CONF_SCHEMA)

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params, auth_token)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_env_conf_basic(api_client, auth_token):
    """
    Базовый тест для эндпоинта /env-conf без параметров.
    Проверяет основную функциональность и структуру ответа.
    """
    try:
        headers = {"x-access-token": auth_token, "token": auth_token}
        response = api_client.get(ENDPOINT, headers=headers)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
        
        # Проверяем структуру конфигурации
        _check_types_recursive(data, ENV_CONF_SCHEMA)
        
    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nБазовый тест упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_env_conf_ip_validation(api_client, auth_token):
    """
    Тест для валидации IP адресов в конфигурации.
    Проверяет, что все IP адреса в ответе являются валидными.
    """
    try:
        headers = {"x-access-token": auth_token, "token": auth_token}
        response = api_client.get(ENDPOINT, headers=headers)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"
        
        data = response.json()
        
        # Список полей, которые должны содержать валидные IP адреса
        ip_fields = [
            "CSI_HOST", "HOST_IP", "NGFW_IP", "SWITCH_MANAGEMENT_IP", 
            "LINUX_OF_CONTROLLER_IP", "DOCKER_NET_GW", "DNS_RESOLVERS"
        ]
        
        for field in ip_fields:
            if field in data and data[field]:
                assert is_valid_ip(data[field]), \
                    f"Поле {field} содержит невалидный IP адрес: {data[field]}"
        
    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nТест валидации IP адресов упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)


def test_env_conf_port_validation(api_client, auth_token):
    """
    Тест для валидации портов в конфигурации.
    Проверяет, что все порты в ответе являются валидными.
    """
    try:
        headers = {"x-access-token": auth_token, "token": auth_token}
        response = api_client.get(ENDPOINT, headers=headers)
        
        assert response.status_code == 200, \
            f"Ожидался статус-код 200, получен {response.status_code}. Ответ: {response.text}"
        
        data = response.json()
        
        # Список полей, которые должны содержать валидные порты
        port_fields = [
            "CSI_PORT", "CSI_SSH_TERMINAL_PORT", "CSI_TELNET_TERMINAL_PORT",
            "KIBANA_PORT", "PROXY_PORT", "PROXY_PORT_SSL", "SWITCH_DATA_PORT",
            "SWITCH_IDS_PORT", "TLS_BRIDGE_SSL_PORT", "TLS_BRIDGE_TCP_PORT",
            "TLS_PROXY_BRIDGE_SSL_PORT", "TLS_PROXY_BRIDGE_TCP_PORT"
        ]
        
        for field in port_fields:
            if field in data and data[field]:
                assert is_valid_port(data[field]), \
                    f"Поле {field} содержит невалидный порт: {data[field]}"
        
    except (AssertionError, json.JSONDecodeError) as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, {}, auth_token)
        
        error_message = (
            f"\nТест валидации портов упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
