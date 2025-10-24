import pytest
from jsonschema import validate, ValidationError

# 18. Эндпоинт должен быть прописан константой вверху файла.
ENDPOINT = "/vlans/{id}"
VLANS_ALL_ENDPOINT = "/vlans/all"

# 17. Схема ответа (обновлена для нового формата)
VLAN_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "vlanId": {"type": "integer"},
        "interface": {"type": "string"},
        "ip": {"type": "array"},
        "ipv6": {"type": "array"},
        "mtu": {"type": "integer"},
        "MAC": {"type": "string"},
        "id": {"type": "string"},
        "l2mode": {"type": "integer"},
        "stp": {"type": "boolean"}
    },
    "required": ["name", "vlanId", "interface", "id"]
}

# Добавляем схему для списка VLAN (когда возвращается массив)
VLAN_LIST_SCHEMA = {
    "type": "array",
    "items": VLAN_ITEM_SCHEMA
}

@pytest.fixture(scope="module")
def valid_interface_id(api_client):
    """
    Получает валидный interface.id через GET /vlans/all. Если список пуст — pytest.skip.
    """
    resp = api_client.get(VLANS_ALL_ENDPOINT)
    try:
        data = resp.json()
    except Exception:
        pytest.skip("/vlans/all не вернул валидный JSON, interface.id получить невозможно")
    if not isinstance(data, list) or not data:
        pytest.skip("/vlans/all вернул пустой список, interface.id получить невозможно")
    
    # Ищем первый VLAN с интерфейсами
    for vlan in data:
        interfaces = vlan.get("interfaces", [])
        if interfaces and len(interfaces) > 0:
            return interfaces[0]["id"]
    
    pytest.skip("В /vlans/all не найдено интерфейсов с валидными id")

# Базовый тест с валидным id
def test_vlans_id_success(api_client, valid_interface_id, attach_curl_on_fail):
    """
    Проверяет успешный сценарий для /vlans/{id} с валидным interface.id.
    """
    url = ENDPOINT.replace("{id}", valid_interface_id)
    with attach_curl_on_fail(url, method="GET"):
        response = api_client.get(url)
        assert response.status_code == 200
        validate(instance=response.json(), schema=VLAN_ITEM_SCHEMA)

# Параметры для проверки устойчивости
PARAMS = [
    # ПОЗИТИВНЫЕ КЕЙСЫ (200)
    ("valid", None, 200, "Валидный interface.id (из /vlans/all)"),
    ("empty", "", 200, "Пустой id (возвращает список всех VLAN)"),
    ("none", None, 200, "None как id (возвращает список всех VLAN)"),
    ("tab", "\t", 200, "Табуляция как id (возвращает список всех VLAN)"),
    ("newline", "\n", 200, "Перевод строки как id (возвращает список всех VLAN)"),
    ("slash", "/", 200, "Слэш как id (возвращает список всех VLAN)"),
    ("dot", ".", 200, "Точка как id (возвращает список всех VLAN)"),
    ("double_slash", "//", 200, "Двойной слэш как id (возвращает список всех VLAN)"),
    ("root_path", "./", 200, "Корневой путь как id (возвращает список всех VLAN)"),
    
    # НЕГАТИВНЫЕ КЕЙСЫ для некорректных значений (404)
    ("space", " ", 404, "Пробел как id"),
    ("nonexistent", "nonexistent123", 404, "Несуществующий id"),
    ("short", "a", 404, "Короткий id"),
    ("numeric", "12345", 404, "Числовой id"),
    
    # НЕГАТИВНЫЕ КЕЙСЫ для атак и некорректных данных (404)
    ("null", "null", 400, "id = 'null'"),
    ("long_string", "a"*1000, 404, "Экстремально длинный id (1000 символов)"),
    ("sql_injection", "'; DROP TABLE vlans; --", 404, "SQL-инъекция"),
    ("xss_attack", "<script>alert('xss')</script>", 404, "XSS-атака"),
    ("path_traversal", "../../../etc/passwd", 404, "Path traversal атака"),
    ("unicode_exploit", "\u0000\u0001\u0002", 404, "Unicode control characters"),
    ("binary_data", "\x00\x01\x02\x03", 404, "Бинарные данные"),
]

@pytest.mark.parametrize("case,id_value,expected_status,desc", PARAMS)
def test_vlans_id_parametrized(api_client, valid_interface_id, case, id_value, expected_status, desc, attach_curl_on_fail):
    """
    Проверяет устойчивость /vlans/{id} к различным значениям id.
    Валидный interface.id берётся из /vlans/all, остальные — из параметров.
    """
    if case == "valid":
        test_id = valid_interface_id
    elif id_value is None:
        test_id = ""
    else:
        test_id = str(id_value)
    url = ENDPOINT.replace("{id}", test_id)
    with attach_curl_on_fail(url, method="GET"):
        response = api_client.get(url)
        assert response.status_code == expected_status
        if response.status_code == 200:
            # Проверяем формат ответа: для empty/none/whitespace возвращается список, для valid - объект
            if case in ("empty", "none", "tab", "newline", "slash", "dot", "double_slash", "root_path"):
                validate(instance=response.json(), schema=VLAN_LIST_SCHEMA)
            else:
                validate(instance=response.json(), schema=VLAN_ITEM_SCHEMA) 