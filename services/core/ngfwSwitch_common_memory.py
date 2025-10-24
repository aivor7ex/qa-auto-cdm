"""Tests for the /ngfwSwitch/common/memory endpoint."""
import pytest
import json
from collections.abc import Mapping, Sequence
import time

ENDPOINT = "/ngfwSwitch/common/memory"

MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "total": {"type": "string"},
        "used": {"type": "string"},
        "free": {"type": "string"},
        "buffer": {"type": "string"},
        "utilization": {"type": "string"}
    },
    "required": [],
}

# Автофикстура для задержки между каждым тестом
@pytest.fixture(autouse=True)
def pause_between_tests():
    yield
    time.sleep(1)

# Осмысленная параметризация для тестирования эндпоинта /ngfwSwitch/common/memory
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"format": "xml"}, 200, id="P03: format_xml"),
    pytest.param({"format": "text"}, 200, id="P04: format_text"),
    pytest.param({"format": "yaml"}, 200, id="P05: format_yaml"),
    pytest.param({"format": "csv"}, 200, id="P06: format_csv"),
    pytest.param({"verbose": "true"}, 200, id="P07: verbose_true"),
    pytest.param({"verbose": "false"}, 200, id="P08: verbose_false"),
    pytest.param({"detailed": "true"}, 200, id="P09: detailed_true"),
    pytest.param({"detailed": "false"}, 200, id="P10: detailed_false"),
    
    # --- Единицы измерения ---
    pytest.param({"units": "bytes"}, 200, id="P11: units_bytes"),
    pytest.param({"units": "kb"}, 200, id="P12: units_kilobytes"),
    pytest.param({"units": "mb"}, 200, id="P13: units_megabytes"),
    pytest.param({"units": "gb"}, 200, id="P14: units_gigabytes"),
    pytest.param({"units": "auto"}, 200, id="P15: units_auto"),
    pytest.param({"scale": "1024"}, 200, id="P16: scale_1024"),
    pytest.param({"scale": "1000"}, 200, id="P17: scale_1000"),
    pytest.param({"scale": "auto"}, 200, id="P18: scale_auto"),
    
    # --- Фильтрация типов памяти ---
    pytest.param({"include": "total"}, 200, id="P19: include_total"),
    pytest.param({"include": "used"}, 200, id="P20: include_used"),
    pytest.param({"include": "free"}, 200, id="P21: include_free"),
    pytest.param({"include": "buffer"}, 200, id="P22: include_buffer"),
    pytest.param({"include": "utilization"}, 200, id="P23: include_utilization"),
    pytest.param({"include": "all"}, 200, id="P24: include_all"),
    pytest.param({"exclude": "buffer"}, 200, id="P25: exclude_buffer"),
    pytest.param({"exclude": "utilization"}, 200, id="P26: exclude_utilization"),
    pytest.param({"show": "summary"}, 200, id="P27: show_summary"),
    pytest.param({"show": "details"}, 200, id="P28: show_details"),
    
    # --- Комбинированные параметры ---
    pytest.param({"format": "json", "verbose": "true"}, 200, id="P29: json_verbose"),
    pytest.param({"units": "mb", "detailed": "true"}, 200, id="P30: mb_detailed"),
    pytest.param({"scale": "1024", "format": "text"}, 200, id="P31: scale_text"),
    pytest.param({"include": "used", "units": "gb"}, 200, id="P32: used_gb"),
    pytest.param({"verbose": "true", "detailed": "true"}, 200, id="P33: verbose_detailed"),
    
    # --- Специальные параметры ---
    pytest.param({"refresh": "true"}, 200, id="P34: refresh_data"),
    pytest.param({"refresh": "false"}, 200, id="P35: no_refresh"),
    pytest.param({"cache": "true"}, 200, id="P36: use_cache"),
    pytest.param({"cache": "false"}, 200, id="P37: no_cache"),
    pytest.param({"realtime": "true"}, 200, id="P38: realtime_data"),
    pytest.param({"realtime": "false"}, 200, id="P39: cached_data"),
    pytest.param({"precision": "2"}, 200, id="P40: precision_2"),
    pytest.param({"precision": "4"}, 200, id="P41: precision_4"),
    pytest.param({"precision": "0"}, 200, id="P42: precision_0"),
    pytest.param({"round": "true"}, 200, id="P43: round_values"),
    pytest.param({"round": "false"}, 200, id="P44: exact_values"),
    
    # --- Мониторинг и диагностика ---
    pytest.param({"monitoring": "true"}, 200, id="P45: monitoring_enabled"),
    pytest.param({"monitoring": "false"}, 200, id="P46: monitoring_disabled"),
    pytest.param({"debug": "true"}, 200, id="P47: debug_enabled"),
    pytest.param({"debug": "false"}, 200, id="P48: debug_disabled"),
    pytest.param({"stats": "true"}, 200, id="P49: include_stats"),
    pytest.param({"stats": "false"}, 200, id="P50: exclude_stats"),
    pytest.param({"history": "true"}, 200, id="P51: include_history"),
    pytest.param({"history": "false"}, 200, id="P52: exclude_history"),
    pytest.param({"trend": "true"}, 200, id="P53: include_trend"),
    pytest.param({"trend": "false"}, 200, id="P54: exclude_trend"),
    
    # --- Временные параметры ---
    pytest.param({"interval": "1"}, 200, id="P55: interval_1_sec"),
    pytest.param({"interval": "5"}, 200, id="P56: interval_5_sec"),
    pytest.param({"interval": "10"}, 200, id="P57: interval_10_sec"),
    pytest.param({"timeout": "5"}, 200, id="P58: timeout_5_sec"),
    pytest.param({"timeout": "10"}, 200, id="P59: timeout_10_sec"),
    pytest.param({"timestamp": "true"}, 200, id="P60: include_timestamp"),
    pytest.param({"timestamp": "false"}, 200, id="P61: exclude_timestamp"),
    
    # --- Пороговые значения ---
    pytest.param({"threshold": "80"}, 200, id="P62: threshold_80_percent"),
    pytest.param({"threshold": "90"}, 200, id="P63: threshold_90_percent"),
    pytest.param({"alert": "true"}, 200, id="P64: alert_enabled"),
    pytest.param({"alert": "false"}, 200, id="P65: alert_disabled"),
    pytest.param({"warning": "true"}, 200, id="P66: warning_enabled"),
    pytest.param({"warning": "false"}, 200, id="P67: warning_disabled"),
    
    # --- Граничные значения ---
    pytest.param({"unsupported_param": "value"}, 200, id="P68: unsupported_param_ignored"),
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
def test_ngfw_switch_common_memory_parametrized(api_client, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /ngfwSwitch/common/memory.
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
            _check_types_recursive(data, MEMORY_SCHEMA)
            
            # Дополнительная проверка что все значения памяти - строки с числами
            for field in ["total", "used", "free", "buffer"]:
                if field in data:
                    assert isinstance(data[field], str), f"Поле '{field}' должно быть строкой"
                    assert data[field].isdigit(), f"Поле '{field}' должно содержать только цифры"
            
            # Проверка что utilization содержит проценты
            if "utilization" in data:
                assert isinstance(data["utilization"], str), "Поле 'utilization' должно быть строкой"
                # Может содержать точку для десятичных процентов
                util_clean = data["utilization"].replace(".", "")
                assert util_clean.isdigit(), "Поле 'utilization' должно содержать числовое значение процентов"

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