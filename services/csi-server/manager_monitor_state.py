# file: /services/csi-server/manager_monitor_state.py
import json
import pytest
from qa_constants import SERVICES

ENDPOINT = "/manager/monitor/state"

# ----- СХЕМА ОТВЕТА (получена из R0) -----
RESPONSE_SCHEMA = {
    "cpu": {"type": "number", "required": True},
    "ram": {
        "type": "object", 
        "required": True,
        "properties": {
            "memory_used_bytes": {"type": "number", "required": True},
            "memory_total_bytes": {"type": "number", "required": True},
            "swap_used_bytes": {"type": "number", "required": True},
            "swap_total_bytes": {"type": "number", "required": True}
        }
    },
    "block": {
        "type": "object", 
        "required": True,
        "properties": {
            "/dev/sda2": {
                "type": "object",
                "required": False,
                "properties": {
                    "entries": {
                        "type": "list",
                        "required": True,
                        "item_type": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "required": True},
                                "path": {"type": "string", "required": True}
                            }
                        }
                    },
                    "health": {"type": "string", "required": True},
                    "devices": {
                        "type": "list",
                        "required": True,
                        "item_type": {"type": "string", "required": True}
                    },
                    "stats": {
                        "type": "object",
                        "required": True,
                        "properties": {
                            "bytes_total": {"type": "number", "required": True},
                            "bytes_free": {"type": "number", "required": True},
                            "bytes_free_user": {"type": "number", "required": True},
                            "inodes_total": {"type": "number", "required": True},
                            "inodes_free": {"type": "number", "required": True},
                            "inodes_free_user": {"type": "number", "required": True}
                        }
                    }
                }
            }
        }
    },
    "network": {"type": "list", "required": True}
}

# ----- ФИКСТУРЫ (в проекте уже существуют) -----
# api_client(base_url), auth_token() — ИСПОЛЬЗОВАТЬ, НЕ МЕНЯТЬ.

def _url(base_path: str) -> str:
    return f"{base_path}{ENDPOINT}"

def _check_type(name, value, spec):
    t = spec.get("type")
    if t == "string":
        assert isinstance(value, str), f"{name}: ожидается string; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "number":
        assert isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: ожидается number; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "boolean":
        assert isinstance(value, bool), f"{name}: ожидается boolean; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
    elif t == "object":
        assert isinstance(value, dict), f"{name}: ожидается object; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        _validate_object(value, spec.get("properties", {}), name)
    elif t == "list":
        assert isinstance(value, list), f"{name}: ожидается list; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        item_spec = spec.get("item_type")
        if item_spec:
            for i, v in enumerate(value):
                _check_type(f"{name}[{i}]", v, item_spec)
    else:
        assert False, f"{name}: неизвестный тип '{t}'; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"

def _validate_object(obj, properties: dict, prefix: str = "root"):
    for key, prop in properties.items():
        required = prop.get("required", False)
        if required:
            assert key in obj, f"{prefix}.{key}: обязательное поле; curl: curl --location 'http://127.0.0.1:2999/api/manager/monitor/state' --header 'x-access-token: 9wO53O0bTModkbS3Vhc50kOR2bXafRHg3IA2CBcIt84j'"
        if key in obj:
            _check_type(f"{prefix}.{key}", obj[key], prop)

def _format_curl_command(api_client, endpoint, params=None, headers=None):
    """Формирует и возвращает cURL-строку для воспроизведения запроса."""
    base_url = getattr(api_client, "base_url", "http://127.0.0.1:2999")
    full_url = f"{base_url.rstrip('/')}{endpoint}"
    
    # Формируем строку параметров
    param_str = ""
    if params:
        param_str = "&".join([f"{k}={v}" for k, v in params.items() if v is not None])
    
    curl_command = f"curl --location '{full_url}"
    if param_str:
        curl_command += f"?{param_str}"
    curl_command += "'"
    
    if headers:
        for k, v in headers.items():
            curl_command += f" \\\n  -H '{k}: {v}'"
        
    return curl_command

# ---------- ПАРАМЕТРИЗАЦИЯ ----------
# 40 осмысленных кейсов для GET запроса с различными query параметрами
BASE_PARAMS = [
    {"q": None, "desc": "базовый запрос без параметров"},
    {"q": {"format": "json"}, "desc": "формат JSON"},
    {"q": {"pretty": "true"}, "desc": "красивый вывод"},
    {"q": {"pretty": "false"}, "desc": "обычный вывод"},
    {"q": {"indent": "2"}, "desc": "отступ 2 пробела"},
    {"q": {"indent": "4"}, "desc": "отступ 4 пробела"},
    {"q": {"verbose": "true"}, "desc": "подробный вывод"},
    {"q": {"verbose": "false"}, "desc": "краткий вывод"},
    {"q": {"details": "true"}, "desc": "с деталями"},
    {"q": {"details": "false"}, "desc": "без деталей"},
    {"q": {"include": "cpu"}, "desc": "включить CPU"},
    {"q": {"include": "ram"}, "desc": "включить RAM"},
    {"q": {"include": "block"}, "desc": "включить блоки"},
    {"q": {"include": "network"}, "desc": "включить сеть"},
    {"q": {"exclude": "cpu"}, "desc": "исключить CPU"},
    {"q": {"exclude": "ram"}, "desc": "исключить RAM"},
    {"q": {"exclude": "block"}, "desc": "исключить блоки"},
    {"q": {"exclude": "network"}, "desc": "исключить сеть"},
    {"q": {"fields": "cpu,ram"}, "desc": "только CPU и RAM"},
    {"q": {"fields": "block,network"}, "desc": "только блоки и сеть"},
    {"q": {"sort": "cpu"}, "desc": "сортировка по CPU"},
    {"q": {"sort": "-cpu"}, "desc": "сортировка по CPU убыв"},
    {"q": {"sort": "ram.memory_used_bytes"}, "desc": "сортировка по памяти"},
    {"q": {"filter": "cpu>0"}, "desc": "фильтр CPU > 0"},
    {"q": {"filter": "ram.memory_used_bytes>0"}, "desc": "фильтр памяти > 0"},
    {"q": {"limit": "1"}, "desc": "лимит 1"},
    {"q": {"limit": "10"}, "desc": "лимит 10"},
    {"q": {"limit": "100"}, "desc": "лимит 100"},
    {"q": {"offset": "0"}, "desc": "смещение 0"},
    {"q": {"offset": "10"}, "desc": "смещение 10"},
    {"q": {"page": "1"}, "desc": "страница 1"},
    {"q": {"page": "2"}, "desc": "страница 2"},
    {"q": {"count": "true"}, "desc": "счетчик элементов"},
    {"q": {"count": "false"}, "desc": "без счетчика"},
    {"q": {"timestamp": "true"}, "desc": "с временной меткой"},
    {"q": {"timestamp": "false"}, "desc": "без временной метки"},
    {"q": {"refresh": "true"}, "desc": "обновить данные"},
    {"q": {"refresh": "false"}, "desc": "кешированные данные"},
    {"q": {"cache": "true"}, "desc": "использовать кеш"},
    {"q": {"cache": "false"}, "desc": "без кеша"},
    {"q": {"timeout": "30"}, "desc": "таймаут 30 сек"},
    {"q": {"timeout": "60"}, "desc": "таймаут 60 сек"}
]

@pytest.mark.parametrize("case", BASE_PARAMS, ids=lambda c: c["desc"])
def test_get_schema_conforms(api_client, auth_token, case):
    base = f"http://127.0.0.1:{SERVICES['csi-server']['port']}{SERVICES['csi-server']['base_path']}"
    url = _url(base)
    params = case.get("q") or {}
    headers = {'x-access-token': auth_token}
    
    try:
        r = api_client.get(url, headers=headers, params=params)
        assert r.status_code == 200, f"Ожидается 200 OK; получено {r.status_code}"
        data = r.json()
        assert isinstance(data, dict), f"Корень: ожидается object"
        _validate_object(data, RESPONSE_SCHEMA)
        
    except Exception as e:
        curl_command = _format_curl_command(api_client, ENDPOINT, params, headers)
        error_message = (
            f"\nТест с параметрами {params} упал.\n"
            f"Ошибка: {e}\n\n"
            "================= Failed Test Request (cURL) ================\n"
            f"{curl_command}\n"
            "============================================================="
        )
        pytest.fail(error_message, pytrace=False)
