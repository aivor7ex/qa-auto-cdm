import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/router/ospf/config"

OSPF_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "level": {"type": "integer"},
        "items": {
            "type": "array",
            "items": {
                "type": "object"
            }
        },
        "str": {"type": "string"}
    },
    "required": ["id", "level", "items"],
}

# Осмысленная параметризация для тестирования эндпоинта /router/ospf/config
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"format": "text"}, 200, id="P03: format_text"),
    pytest.param({"format": "xml"}, 200, id="P04: format_xml"),
    pytest.param({"format": "yaml"}, 200, id="P05: format_yaml"),
    pytest.param({"verbose": "true"}, 200, id="P06: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P07: verbose_false"),
    pytest.param({"detailed": "true"}, 200, id="P08: detailed_true"),
    pytest.param({"detailed": "false"}, 200, id="P09: detailed_false"),
    pytest.param({"expand": "true"}, 200, id="P10: expand_true"),
    
    # --- Фильтрация по секциям ---
    pytest.param({"section": "router"}, 200, id="P11: section_router"),
    pytest.param({"section": "area"}, 200, id="P12: section_area"),
    pytest.param({"section": "interface"}, 200, id="P13: section_interface"),
    pytest.param({"section": "network"}, 200, id="P14: section_network"),
    pytest.param({"section": "redistribute"}, 200, id="P15: section_redistribute"),
    pytest.param({"section": "neighbor"}, 200, id="P16: section_neighbor"),
    pytest.param({"section": "passive-interface"}, 200, id="P17: section_passive_interface"),
    pytest.param({"section": "summary"}, 200, id="P18: section_summary"),
    pytest.param({"section": "default-information"}, 200, id="P19: section_default_information"),
    pytest.param({"section": "timers"}, 200, id="P20: section_timers"),
    
    # --- Комбинированные параметры ---
    pytest.param({"format": "json", "verbose": "true"}, 200, id="P21: json_verbose"),
    pytest.param({"format": "text", "detailed": "true"}, 200, id="P22: text_detailed"),
    pytest.param({"section": "router", "verbose": "true"}, 200, id="P23: router_section_verbose"),
    pytest.param({"section": "area", "format": "json"}, 200, id="P24: area_section_json"),
    pytest.param({"expand": "true", "detailed": "true"}, 200, id="P25: expand_detailed"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "ospf"}, 200, id="P26: search_ospf"),
    pytest.param({"search": "router"}, 200, id="P27: search_router"),
    pytest.param({"search": "area"}, 200, id="P28: search_area"),
    pytest.param({"q": "config"}, 200, id="P29: query_config"),
    pytest.param({"filter": "ospf"}, 200, id="P30: filter_ospf"),
    pytest.param({"filter": "interface"}, 200, id="P31: filter_interface"),
    
    # --- Специальные параметры ---
    pytest.param({"level": "0"}, 200, id="P32: level_0"),
    pytest.param({"level": "1"}, 200, id="P33: level_1"),
    pytest.param({"level": "2"}, 200, id="P34: level_2"),
    pytest.param({"depth": "1"}, 200, id="P35: depth_1"),
    pytest.param({"depth": "3"}, 200, id="P36: depth_3"),
    pytest.param({"depth": "5"}, 200, id="P37: depth_5"),
    pytest.param({"include": "all"}, 200, id="P38: include_all"),
    pytest.param({"include": "basic"}, 200, id="P39: include_basic"),
    pytest.param({"include": "advanced"}, 200, id="P40: include_advanced"),
    pytest.param({"exclude": "comments"}, 200, id="P41: exclude_comments"),
    pytest.param({"exclude": "defaults"}, 200, id="P42: exclude_defaults"),
    
    # --- Дополнительные системные параметры ---
    pytest.param({"sort": "name"}, 200, id="P43: sort_name"),
    pytest.param({"limit": "100"}, 200, id="P44: limit_100"),
    pytest.param({"offset": "10"}, 200, id="P45: offset_10"),
    pytest.param({"order": "asc"}, 200, id="P46: order_asc"),
    pytest.param({"order": "desc"}, 200, id="P47: order_desc"),
    
    # --- Специальные форматы вывода ---
    pytest.param({"output": "structured"}, 200, id="P48: output_structured"),
    pytest.param({"output": "flat"}, 200, id="P49: output_flat"),
    pytest.param({"output": "tree"}, 200, id="P50: output_tree"),
    pytest.param({"compact": "true"}, 200, id="P51: compact_true"),
    pytest.param({"pretty": "true"}, 200, id="P52: pretty_true"),
    pytest.param({"indent": "2"}, 200, id="P53: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P54: indent_4"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P55: unsupported_param_ignored"),
]


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


def _format_curl_command(api_client, endpoint, params):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1")
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    # Формируем строку параметров
    param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    if param_str:
        full_url += f"?{param_str}"

    headers = getattr(api_client, 'headers', {})
    headers_str = " \\\n  ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
    
    curl_command = f"curl -X GET '{full_url}'"
    if headers_str:
        curl_command += f" \\\n  {headers_str}"
        
    return curl_command


@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_router_ospf_config_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /router/ospf/config.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    try:
        response = api_client.get(ENDPOINT, params=params)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), f"Тело ответа не является объектом JSON, получено: {type(data).__name__}"
            _check_types_recursive(data, OSPF_CONFIG_SCHEMA)

    except (AssertionError, json.JSONDecodeError) as e:
        # 3. Формирование и вывод детального отчета об ошибке
        curl_command = _format_curl_command(api_client, ENDPOINT, params)
        
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False) 