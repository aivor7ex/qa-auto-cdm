import pytest
import json
from collections.abc import Mapping, Sequence

ENDPOINT = "/vlans/count"

VLANS_COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
    },
    "required": ["count"],
}

# Осмысленная параметризация для тестирования эндпоинта /vlans/count
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"filter": '{"vlanId": 0}'}, 200, id="P02: filter_by_vlan_id_0"),
    pytest.param({"filter": '{"vlanId": 1}'}, 200, id="P03: filter_by_vlan_id_1"),
    pytest.param({"filter": '{"vlanId": 10}'}, 200, id="P04: filter_by_vlan_id_10"),
    pytest.param({"filter": '{"name": "native"}'}, 200, id="P05: filter_by_name_native"),
    pytest.param({"filter": '{"name": "qwe"}'}, 200, id="P06: filter_by_name_qwe"),
    pytest.param({"filter": '{"interface": "eth-0-1"}'}, 200, id="P07: filter_by_interface"),
    pytest.param({"filter": '{"l2mode": 0}'}, 200, id="P08: filter_by_l2mode"),
    pytest.param({"filter": '{"stp": false}'}, 200, id="P09: filter_by_stp_false"),
    pytest.param({"filter": '{"stp": true}'}, 200, id="P10: filter_by_stp_true"),
    
    # --- Поиск и фильтрация ---
    pytest.param({"search": "native"}, 200, id="P11: search_native"),
    pytest.param({"search": "eth"}, 200, id="P12: search_eth_interfaces"),
    pytest.param({"q": "vlan"}, 200, id="P13: query_text"),
    pytest.param({"name": "native"}, 200, id="P14: filter_by_name_param"),
    pytest.param({"vlanId": "0"}, 200, id="P15: filter_by_vlanId_param"),
    pytest.param({"interface": "eth-0-1"}, 200, id="P16: filter_by_interface_param"),
    pytest.param({"l2mode": "0"}, 200, id="P17: filter_by_l2mode_param"),
    pytest.param({"stp": "false"}, 200, id="P18: filter_by_stp_param"),
    
    # --- Комбинации фильтров ---
    pytest.param({"filter": '{"vlanId": 0, "name": "native"}'}, 200, id="P19: multiple_filters"),
    pytest.param({"vlanId": "0", "interface": "eth-0-1"}, 200, id="P20: param_filters"),
    pytest.param({"filter": '{"l2mode": 0, "stp": false}'}, 200, id="P21: l2mode_and_stp"),
    pytest.param({"name": "native", "vlanId": "0"}, 200, id="P22: name_and_vlanid"),
    
    # --- Специальные фильтры ---
    pytest.param({"mtu": "1500"}, 200, id="P23: filter_by_mtu_param"),
    pytest.param({"MAC": "54:5a:00:a1:52:05"}, 200, id="P24: filter_by_mac_param"),
    pytest.param({"filter": '{"mtu": 1500}'}, 200, id="P25: filter_by_mtu"),
    
    # --- Негативные сценарии ---
    pytest.param({"filter": "invalid_json"}, 200, id="N01: invalid_json_filter_ignored"),
    pytest.param({"filter": '{"invalid": }'}, 200, id="N02: malformed_json_ignored"),
    pytest.param({"filter": "null"}, 200, id="P26: null_filter_ignored"),
    pytest.param({"limit": "-1"}, 200, id="P27: negative_limit_ignored"),
    pytest.param({"skip": "-5"}, 200, id="P28: negative_skip_ignored"),
    
    # --- Граничные значения ---
    pytest.param({"limit": "0"}, 200, id="P29: zero_limit"),
    pytest.param({"limit": "1000"}, 200, id="P30: high_limit"),
    pytest.param({"skip": "1000"}, 200, id="P31: high_skip"),
    pytest.param({"unsupported_param": "value"}, 200, id="P32: unsupported_param_ignored"),
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
def test_vlans_count_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /vlans/count.
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
            _check_types_recursive(data, VLANS_COUNT_SCHEMA)
            # Дополнительная проверка что count не отрицательный
            assert data["count"] >= 0, f"Значение count должно быть неотрицательным, получено: {data['count']}"

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