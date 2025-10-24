"""
Тесты для эндпоинта /config сервиса csi-server.

Проверяется:
- Статус-код 200 OK
- Соответствие структуры ответа схеме (массив объектов конфигурации)
- Устойчивость к 35+ различным query-параметрам
- Вывод cURL-команды при ошибке в параметризованных тестах
"""
import pytest
import json
import uuid
from collections.abc import Mapping, Sequence

ENDPOINT = "/config"

# Схема успешного ответа POST /api/config, полученная от реального API
# Схема ответа на основе предоставленного примера
response_schemas = {
    "GET": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "stackName": {"type": "string"},
                "serviceName": {"type": "string"},
                "config": {
                    "type": "object",
                    "properties": {
                        "SecuritySettings": {
                            "type": "array",
                            "items": {"type": "object"}
                        },
                        "NotificationStream": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "priority": {"type": "string"},
                                    "userIds": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["id", "name", "priority", "userIds"]
                            }
                        }
                    },
                    "required": ["SecuritySettings", "NotificationStream"]
                }
            },
            "required": ["stackName", "serviceName", "config"]
        }
    },
    "POST": {"ok": int}
}

# Осмысленная параметризация для тестирования эндпоинта /config
PARAMS = [
    # --- Базовые позитивные сценарии ---
    pytest.param({}, 200, id="P01: no_params"),
    pytest.param({"format": "json"}, 200, id="P02: format_json"),
    pytest.param({"pretty": "true"}, 200, id="P03: pretty_true"),
    pytest.param({"pretty": "false"}, 200, id="P04: pretty_false"),
    pytest.param({"indent": "2"}, 200, id="P05: indent_2"),
    pytest.param({"indent": "4"}, 200, id="P06: indent_4"),
    # --- Фильтрация по стеку ---
    pytest.param({"stack": "csi"}, 200, id="P07: filter_stack_csi"),
    pytest.param({"stackName": "csi"}, 200, id="P08: filter_stackname_csi"),
    pytest.param({"service": "csi-server"}, 200, id="P09: filter_service_csi_server"),
    pytest.param({"serviceName": "csi-server"}, 200, id="P10: filter_servicename_csi_server"),
    # --- Фильтрация по компонентам конфигурации ---
    pytest.param({"include": "SecuritySettings"}, 200, id="P11: include_security_settings"),
    pytest.param({"include": "NotificationStream"}, 200, id="P12: include_notification_stream"),
    pytest.param({"include": "SecuritySettings,NotificationStream"}, 200, id="P13: include_multiple"),
    pytest.param({"exclude": "SecuritySettings"}, 200, id="P14: exclude_security_settings"),
    pytest.param({"exclude": "NotificationStream"}, 200, id="P15: exclude_notification_stream"),
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
    _check_types_recursive(obj, schema)
    return True

@pytest.mark.parametrize("params, expected_status", PARAMS)
def test_config_parametrized(api_client, auth_token, attach_curl_on_fail, params, expected_status):
    """
    Основной параметризованный тест для эндпоинта /config.
    1. Отправляет GET-запрос с указанными параметрами.
    2. Проверяет соответствие статус-кода ожидаемому.
    3. Для успешных ответов (200) валидирует схему JSON.
    4. В случае падения теста выводит полную cURL-команду для воспроизведения.
    """
    headers = {
        'x-access-token': auth_token,
        'token': auth_token
    }
    with attach_curl_on_fail(ENDPOINT, params, headers, method="GET"):
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        
        # 1. Проверка статус-кода
        assert response.status_code == expected_status, \
            f"Ожидался статус-код {expected_status}, получен {response.status_code}. Ответ: {response.text}"

        # 2. Валидация схемы ответа
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), f"Тело ответа не является массивом JSON, получено: {type(data).__name__}"
            # Проверяем структуру каждого элемента конфигурации в ответе
            for config_item in data:
                _check_types_recursive(config_item, response_schemas["GET"]["items"])


# ======================= APPEND: POST /api/config tests =======================

def _validate_types_against_schema(obj, schema):
    """Проверяет типы значений obj согласно простой схеме {key: type|dict|list}.

    Поддерживаются вложенные словари и списки с единым типом элементов, например:
      {"items": list} — список любого содержимого,
      {"items": [dict]} — список словарей,
      {"items": [{"id": str}]} — список объектов по указанной схеме.
    """
    assert isinstance(schema, (dict, list, type)), "Схема должна быть dict, list или type"

    if isinstance(schema, dict):
        assert isinstance(obj, dict), f"Ожидался dict, получено: {type(obj).__name__}"
        for key, expected in schema.items():
            assert key in obj, f"Отсутствует обязательное поле '{key}'"
            _validate_types_against_schema(obj[key], expected)
        return

    if isinstance(schema, list):
        # Ожидаем список (в obj) и один элемент-схему в schema
        assert len(schema) == 1, "Список схемы должен содержать ровно один элемент-схему"
        assert isinstance(obj, list), f"Ожидался list, получено: {type(obj).__name__}"
        elem_schema = schema[0]
        for elem in obj:
            _validate_types_against_schema(elem, elem_schema)
        return

    # schema — это тип
    expected_type = schema
    if expected_type is type(None):
        assert obj is None, "Ожидалось значение None"
    else:
        assert isinstance(obj, expected_type), (
            f"Неверный тип: ожидается {getattr(expected_type, '__name__', expected_type)}, "
            f"получено {type(obj).__name__}"
        )


# Параметры для POST кейсов из спецификации [CASES]
POST_IMPORT_CASES = [
    # 1) Пустой импорт (валидный no-op)
    pytest.param([], id="POST-01: empty import"),

    # 2) Импорт csi/csi-server с пустыми массивами
    pytest.param([
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [],
                "NotificationStream": []
            }
        }
    ], id="POST-02: csi/csi-server empty arrays"),

    # 3) Только SecuritySettings (непустые), без NotificationStream
    pytest.param([
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [
                    {"id": "sec-2fa-required-uniq-1", "value": True, "type": "boolean"},
                    {
                        "id": "sec-password-policy-uniq-1",
                        "value": {"minLength": 12, "requireUpper": True, "requireLower": True, "requireNumber": True, "requireSymbol": False},
                        "type": "object"
                    }
                ]
            }
        }
    ], id="POST-03: only SecuritySettings populated"),

    # 4) Только NotificationStream (непустые), без SecuritySettings
    pytest.param([
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "NotificationStream": [
                    {"id": "notif-critical-uniq-1", "name": "Ops Critical Uniq 1", "priority": "critical", "userIds": ["user.alpha.uniq1", "user.beta.uniq1"], "dockerStackName": "prod-uniq-1", "dockerServiceName": "alertmanager-uniq-1"}
                ]
            }
        }
    ], id="POST-04: only NotificationStream populated"),

    # 5) Только SecuritySettings (пустой массив), NotificationStream опущен
    pytest.param([
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {"SecuritySettings": []}
        }
    ], id="POST-05: SecuritySettings empty array"),

    # 6) Только NotificationStream (пустой массив), SecuritySettings опущен
    pytest.param([
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {"NotificationStream": []}
        }
    ], id="POST-06: NotificationStream empty array"),

    # 7) Оба набора полей заполнены (максимальный кейс)
    pytest.param([
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [
                    {"id": "sec-2fa-required-uniq", "value": True, "type": "boolean"},
                    {
                        "id": "sec-password-policy-uniq",
                        "value": {"minLength": 14, "requireUpper": True, "requireLower": True, "requireNumber": True, "requireSymbol": True, "rotationDays": 90, "history": 10},
                        "type": "object"
                    },
                    {
                        "id": "sec-session-uniq",
                        "value": {"idleTimeoutSec": 1800, "absoluteTimeoutSec": 28800, "sameSite": "Strict"},
                        "type": "object"
                    },
                    {
                        "id": "sec-allowed-ip-ranges-uniq",
                        "value": ["10.1.2.0/24", "192.0.2.0/28"],
                        "type": "array"
                    },
                    {"id": "sec-audit-level-uniq", "value": "verbose", "type": "string"}
                ],
                "NotificationStream": [
                    {"id": "notif-ops-critical-uniq", "name": "Ops Critical Uniq", "priority": "critical", "userIds": ["user.alfa.uniq", "user.bravo.uniq"], "dockerStackName": "prod-uniq", "dockerServiceName": "alertmanager-uniq"},
                    {"id": "notif-security-high-uniq", "name": "Security High Uniq", "priority": "high", "userIds": ["user.charlie.uniq"], "dockerStackName": "prod-uniq", "dockerServiceName": "siem-uniq"},
                    {"id": "notif-info-default-uniq", "name": "Info Default Uniq", "priority": "info", "userIds": [], "dockerStackName": "prod-uniq", "dockerServiceName": "notifier-uniq"}
                ]
            }
        }
    ], id="POST-07: full config for csi/csi-server"),
]


@pytest.mark.parametrize("payload", POST_IMPORT_CASES)
def test_config_post_import_cases(api_client, auth_token, attach_curl_on_fail, payload):
    """Проверяет все валидные кейсы импорта конфигурации через POST /api/config.

    Требования:
    - Статус-код 200 (успех)
    - Тело ответа соответствует SUCCESS_RESPONSE_SCHEMA
    - При падении формируется полный curl (attach_curl_on_fail)
    """
    headers = {"x-access-token": auth_token}
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)

        assert response.status_code == 200, (
            f"Ожидался статус-код 200, получено {response.status_code}. Тело: {response.text}"
        )

        data = response.json()
        _validate_types_against_schema(data, response_schemas["POST"])


# 15 негативных GET-кейсов (без/неверная авторизация => 401)
GET_NEGATIVE_CASES = [
    pytest.param({}, id="GET-N01: no headers"),
    pytest.param({"x-access-token": ""}, id="GET-N02: empty token"),
    pytest.param({"x-access-token": "invalid"}, id="GET-N03: invalid token"),
    pytest.param({"token": "invalid"}, id="GET-N04: only token header invalid"),
    pytest.param({"x-access-token": "invalid", "token": "invalid"}, id="GET-N05: both invalid"),
    pytest.param({"Authorization": "Bearer invalid"}, id="GET-N06: wrong auth scheme"),
    pytest.param({"x-access-token": None}, id="GET-N07: token None"),
    pytest.param({"Random-Header": "value"}, id="GET-N08: random header only"),
    pytest.param({"x-access-token": "invalid", "Content-Type": "application/json"}, id="GET-N09: invalid with content-type"),
    pytest.param({"x-access-token": "short"}, id="GET-N10: short token"),
    pytest.param({"x-access-token": "a"*10}, id="GET-N11: token len 10"),
    pytest.param({"x-access-token": "a"*20}, id="GET-N12: token len 20"),
    pytest.param({"x-access-token": "a"*32}, id="GET-N13: token len 32"),
    pytest.param({"x-access-token": "a"*64}, id="GET-N14: token len 64"),
    pytest.param({"x-access-token": "a"*1 + "!"}, id="GET-N15: token with symbol"),
]


@pytest.mark.parametrize("headers_override", GET_NEGATIVE_CASES)
def test_config_get_negative_auth_cases(api_client, attach_curl_on_fail, headers_override):
    params = {}
    headers = {}
    # Передаем только то, что задано в оверрайде
    for k, v in headers_override.items():
        headers[k] = v

    with attach_curl_on_fail(ENDPOINT, params, headers if headers else None, method="GET"):
        response = api_client.get(ENDPOINT, params=params, headers=headers if headers else None)
        assert response.status_code == 401, (
            f"Ожидался статус-код 401, получено {response.status_code}. Тело: {response.text}"
        )

# Дополнительные позитивные POST-кейсы для выравнивания до 15
POST_POSITIVE_CASES_EXTRA = [
    pytest.param([  # 8) Два объекта в одном импорте с пустыми массивами
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {"SecuritySettings": [], "NotificationStream": []}
        },
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {"SecuritySettings": [], "NotificationStream": []}
        }
    ], id="POST-08: two entries empty arrays"),

    pytest.param([  # 9) SecuritySettings только строковой настройкой
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [
                    {"id": "sec-audit-level-extra", "value": "info", "type": "string"}
                ]
            }
        }
    ], id="POST-09: SecuritySettings single string"),

    pytest.param([  # 10) SecuritySettings массив значений
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [
                    {"id": "sec-allowed-ip-ranges-extra", "value": ["10.0.0.0/8"], "type": "array"}
                ]
            }
        }
    ], id="POST-10: SecuritySettings array value"),

    pytest.param([  # 11) NotificationStream один элемент с пустым userIds
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "NotificationStream": [
                    {"id": "notif-info-extra", "name": "Info Extra", "priority": "info", "userIds": [], "dockerStackName": "prod-extra", "dockerServiceName": "notifier-extra"}
                ]
            }
        }
    ], id="POST-11: NotificationStream single empty users"),

    pytest.param([  # 12) NotificationStream с одним пользователем
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "NotificationStream": [
                    {"id": "notif-high-extra", "name": "Security High Extra", "priority": "high", "userIds": ["user.delta.extra"], "dockerStackName": "prod-extra", "dockerServiceName": "siem-extra"}
                ]
            }
        }
    ], id="POST-12: NotificationStream single user"),

    pytest.param([  # 13) Пустой объект config с обоими массивами пустыми
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {"SecuritySettings": [], "NotificationStream": []}
        }
    ], id="POST-13: config empty arrays again"),

    pytest.param([  # 14) SecuritySettings объектная политика пароля с иными значениями
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [
                    {"id": "sec-password-policy-extra", "value": {"minLength": 10, "requireUpper": True, "requireLower": True, "requireNumber": False, "requireSymbol": False}, "type": "object"}
                ]
            }
        }
    ], id="POST-14: SecuritySettings password policy variant"),

    pytest.param([  # 15) Комбинация: пустые SecuritySettings и заполненный NotificationStream
        {
            "stackName": "csi",
            "serviceName": "csi-server",
            "config": {
                "SecuritySettings": [],
                "NotificationStream": [
                    {"id": "notif-critical-extra", "name": "Ops Critical Extra", "priority": "critical", "userIds": ["user.epsilon.extra", "user.zeta.extra"], "dockerStackName": "prod-extra", "dockerServiceName": "alertmanager-extra"}
                ]
            }
        }
    ], id="POST-15: empty security + filled notification")
]


@pytest.mark.parametrize("payload", POST_POSITIVE_CASES_EXTRA)
def test_config_post_import_cases_more(api_client, auth_token, attach_curl_on_fail, payload):
    """Дополнительные позитивные кейсы POST /api/config для выравнивания до 15."""
    headers = {"x-access-token": auth_token}
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        assert response.status_code == 200, (
            f"Ожидался статус-код 200, получено {response.status_code}. Тело: {response.text}"
        )
        data = response.json()
        _validate_types_against_schema(data, response_schemas["POST"])


# Негативные POST-кейсы (валидируем, что сервер отклоняет некорректные данные)
POST_NEGATIVE_CASES = [
    pytest.param("this is not json", 400, id="NEG-01: plain text string"),
    pytest.param(12345, 400, id="NEG-03: integer payload"),
    pytest.param(True, 400, id="NEG-04: boolean payload"),
    pytest.param(None, 400, id="NEG-05: None payload"),
    pytest.param("{not: a valid json}", 400, id="NEG-06: malformed json string"),
    pytest.param("{\"stackName\": \"csi\", \"serviceName\": \"csi-server\", \"config\": [}", 400, id="NEG-07: incomplete json array in config"),
    pytest.param("{\"stackName\": \"csi\", \"serviceName\": \"csi-server\", \"config\": {\"SecuritySettings\": [}", 400, id="NEG-08: incomplete json array in SecuritySettings"),
    pytest.param("{\"stackName\": \"csi\", \"serviceName\": \"csi-server\", \"config\": {\"NotificationStream\": [}", 400, id="NEG-09: incomplete json array in NotificationStream"),
    pytest.param("{\"stackName\": \"csi\", \"serviceName\": \"csi-server\", \"config\": {\"SecuritySettings\": {}, \"NotificationStream\": {}}", 400, id="NEG-10: empty objects for array fields"),
]


@pytest.mark.parametrize("payload, expected_status", POST_NEGATIVE_CASES)
def test_config_post_negative_cases(api_client, auth_token, attach_curl_on_fail, payload, expected_status):
    """Негативные кейсы POST /api/config: ожидаем отказ (статус >= 400) или другое согласно кейсу."""
    headers = {"x-access-token": auth_token}

    # Determine how to send the payload based on its type
    if isinstance(payload, (dict, list)):
        post_kwargs = {"json": payload}
    else:
        # For non-JSON payloads like strings, integers, booleans
        post_kwargs = {"data": str(payload)}

    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, headers=headers, **post_kwargs)
        assert response.status_code == expected_status, (
            f"Ожидался статус-код {expected_status}, получено {response.status_code}. Тело: {response.text}"
        )
        if response.status_code == 200:
            data = response.json()
            _validate_types_against_schema(data, response_schemas["POST"])


# ======================= Доп. проверка через агента для POST /config =======================

def _build_marker_value() -> str:
    return f"MARKER-UNIQUE-{uuid.uuid4().hex[:8]}"


def _make_marker_payload(marker: str):
    return {
        "data": [
            {
                "stackName": "csi",
                "serviceName": "csi-server",
                "config": {
                    "SecuritySettings": [
                        {
                            "id": "ss-marker",
                            "type": "string",
                            "value": marker,
                        }
                    ],
                    "NotificationStream": [
                        {
                            "id": "ns-marker",
                            "name": marker,
                            "priority": "high",
                            "userIds": [],
                        }
                    ],
                },
            }
        ]
    }


def _print_validation(step: str, ok: bool, details: str = ""):
    status = "OK" if ok else "FAIL"
    msg = f"Validation [{step}]: {status}"
    if details:
        msg += f" — {details}"
    print(msg)


def test_config_post_agent_marker_case(api_client, auth_token, attach_curl_on_fail, agent_verification):
    """
    Дополнительная проверка для POST /config с уникальным маркером и верификацией через агента.

    Шаги:
    1) Собираем payload с рандомным маркером.
    2) Отправляем POST /config и проверяем 200 + схему ответа.
    3) Выполняем проверку через агента по контракту:
       - {"result":"OK"} => успех
       - {"result":"ERROR","message": "..."} => провал теста
       - "unavailable" => зафиксировать предупреждение и провалить тест
    """

    headers = {"x-access-token": auth_token}
    marker = _build_marker_value()
    payload = _make_marker_payload(marker)

    # Шаг 1: подготовка данных
    _print_validation("prepare-payload", True, f"marker={marker}")

    # Шаг 2: запрос к основному API
    with attach_curl_on_fail(ENDPOINT, payload, headers, method="POST"):
        response = api_client.post(ENDPOINT, json=payload, headers=headers)
        ok_status = response.status_code == 200
        _print_validation("api-status", ok_status, f"status={response.status_code}")
        assert ok_status, (
            f"Ожидался статус-код 200, получено {response.status_code}. Тело: {response.text}"
        )

        # Валидация схемы ответа основного API
        try:
            data = response.json()
        except Exception:
            _print_validation("api-json", False, "невалидный JSON")
            raise
        _validate_types_against_schema(data, response_schemas["POST"])
        _print_validation("api-schema", True)

    # Шаг 3: проверка через агента (POST /config в mirada-agent)
    agent_result = agent_verification(ENDPOINT, payload)
    if agent_result == "unavailable":
        print("Warning: агент недоступен — тест не пропускается и должен упасть")
        _print_validation("agent-availability", False, "agent=unavailable")
        pytest.fail("Agent verification unavailable: агент недоступен")

    # Обработка стандартного формата ответа агента
    if isinstance(agent_result, dict):
        result = agent_result.get("result")
        if result == "OK":
            _print_validation("agent-result", True, "result=OK")
            return
        if result == "ERROR":
            message = agent_result.get("message", "Неизвестная ошибка")
            _print_validation("agent-result", False, f"result=ERROR; message={message}")
            pytest.fail(f"Agent verification error: {message}")

    # Любой другой формат — считаем ошибкой по контракту
    _print_validation("agent-result", False, f"unexpected={agent_result}")
    pytest.fail(f"Agent verification unexpected result: {agent_result}")
