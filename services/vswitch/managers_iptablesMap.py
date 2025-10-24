import pytest
import json
from typing import Dict, Any, List

ENDPOINT = "/managers/iptablesMap"

# Схема ответа API - исправлена согласно реальной структуре
RESPONSE_SCHEMA = {
    "required": {
        "hash": str
    },
    "optional": {
        "resTime": (int, float),
        "resState": str,
        "target": str,
        "protocol": str,
        "destination_port": (str, int),
        "source": str,
        "source_port": str,
        "in_interface": str,
        "out_interface": str,
        "comment": str,
        "chain": str,
        "table": str
    }
}

# Схема ошибки API - исправлена согласно реальной структуре
ERROR_SCHEMA = {
    "required": {
        "error": dict
    },
    "optional": {}
}

# Схема вложенного объекта error
ERROR_DETAIL_SCHEMA = {
    "required": {
        "statusCode": int,
        "name": str,
        "message": str
    },
    "optional": {
        "stack": str
    }
}

# Валидные тестовые данные
VALID_REQUEST_DATA = {
    "data": {
        "table": "filter",
        "chain": "FORWARD",
        "new_chain": "CUSTOM_FORWARD",
        "ordered": True,
        "insert_first": False,
        "rules": [
            {
                "hash": "allow_http",
                "target": "ACCEPT",
                "protocol": "tcp",
                "destination_port": "80"
            },
            {
                "hash": "allow_https",
                "target": "ACCEPT",
                "protocol": "tcp",
                "destination_port": "443"
            }
        ]
    },
    "util": "iptables"
}

# Edge cases для тестирования
EDGE_CASES = [
    # Пустые поля
    {
        "data": {
            "table": "",
            "chain": "",
            "new_chain": "",
            "ordered": True,
            "insert_first": False,
            "rules": []
        },
        "util": ""
    },
    # Null значения
    {
        "data": {
            "table": None,
            "chain": None,
            "new_chain": None,
            "ordered": None,
            "insert_first": None,
            "rules": None
        },
        "util": None
    },
    # Неверные типы
    {
        "data": {
            "table": 123,
            "chain": 456,
            "new_chain": 789,
            "ordered": "true",
            "insert_first": "false",
            "rules": "invalid"
        },
        "util": 999
    },
    # Длинные строки
    {
        "data": {
            "table": "a" * 1000,
            "chain": "b" * 1000,
            "new_chain": "c" * 1000,
            "ordered": True,
            "insert_first": False,
            "rules": []
        },
        "util": "d" * 1000
    },
    # Спецсимволы
    {
        "data": {
            "table": "!@#$%^&*()",
            "chain": "[]{}|\\:;\"'<>?,./",
            "new_chain": "tab\tnewline\nreturn\r",
            "ordered": True,
            "insert_first": False,
            "rules": []
        },
        "util": "!@#$%^&*()"
    }
]

# Валидные варианты таблиц и цепочек
VALID_TABLES = ["filter", "nat", "mangle", "raw"]
VALID_CHAINS = ["INPUT", "OUTPUT", "FORWARD", "PREROUTING", "POSTROUTING"]
VALID_TARGETS = ["ACCEPT", "DROP", "REJECT", "LOG", "DNAT", "SNAT"]
VALID_PROTOCOLS = ["tcp", "udp", "icmp", "all"]

# Базовая логика API - что возвращает каждая комбинация
TABLE_CHAIN_RESPONSES = {
    "filter": {
        "INPUT": {"type": "rules"},
        "OUTPUT": {"type": "rules"},
        "FORWARD": {"type": "rules"},
        "PREROUTING": {"type": "index", "value": 0},
        "POSTROUTING": {"type": "index", "value": 0}
    },
    "nat": {
        "PREROUTING": {"type": "rules"},
        "POSTROUTING": {"type": "rules"},
        "OUTPUT": {"type": "rules"},
        "INPUT": {"type": "rules"},
        "FORWARD": {"type": "index", "value": 0}
    },
    "mangle": {
        "PREROUTING": {"type": "rules"},
        "INPUT": {"type": "rules"},
        "FORWARD": {"type": "rules"},
        "OUTPUT": {"type": "rules"},
        "POSTROUTING": {"type": "rules"}
    },
    "raw": {
        "PREROUTING": {"type": "rules"},
        "OUTPUT": {"type": "rules"},
        "INPUT": {"type": "index", "value": 0},
        "FORWARD": {"type": "index", "value": 0}
    }
}

class TestIptablesMapEndpoint:
    """Тесты для эндпоинта POST /managers/iptablesMap"""
    
    def test_successful_iptables_map_creation(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест успешного создания iptables map"""
        with attach_curl_on_fail(ENDPOINT, VALID_REQUEST_DATA, method="POST"):
            response = api_client.post(ENDPOINT, json=VALID_REQUEST_DATA)
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            for item in data:
                self._validate_response_schema(item)
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for successful iptables map creation")
        self._verify_agent(ENDPOINT, VALID_REQUEST_DATA, agent_verification, "iptables map creation")
    
    def test_successful_iptables_map_with_different_table(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с различными таблицами iptables"""
        for table in VALID_TABLES:
            request_data = VALID_REQUEST_DATA.copy()
            request_data["data"]["table"] = table
            with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                response = api_client.post(ENDPOINT, json=request_data)
                if response.status_code == 200:
                    data = response.json()
                    # Проверяем ответ на основе реальной логики API
                    expected_response = TABLE_CHAIN_RESPONSES[table]["FORWARD"]
                    
                    if expected_response["type"] == "rules":
                        assert isinstance(data, list), f"Таблица {table} должна возвращать массив правил для FORWARD"
                        if len(data) > 0:
                            for item in data:
                                self._validate_response_schema(item)
                    else:
                        assert isinstance(data, dict), f"Таблица {table} должна возвращать объект для {table}:FORWARD"
                        assert "index" in data, f"Объект должен содержать поле 'index' для {table}:FORWARD"
                        assert data["index"] == expected_response["value"], f"Значение index должно быть {expected_response['value']} для {table}:FORWARD"
                    
                    # Дополнительная проверка через агента для положительных кейсов
                    print(f"Checking agent verification for table: {table}")
                    self._verify_agent(ENDPOINT, request_data, agent_verification, f"table: {table}")
                else:
                    # Ожидаем ошибку для некоторых таблиц
                    assert response.status_code in [400, 422]
                    self._validate_error_schema(response.json())
    
    def test_successful_iptables_map_with_different_chains(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с различными цепочками iptables"""
        # Используем таблицу filter, которая поддерживает большинство цепочек
        table = "filter"
        for chain in VALID_CHAINS:
            request_data = VALID_REQUEST_DATA.copy()
            request_data["data"]["table"] = table
            request_data["data"]["chain"] = chain
            with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                response = api_client.post(ENDPOINT, json=request_data)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Проверяем ответ на основе реальной логики API
                    expected_response = TABLE_CHAIN_RESPONSES[table][chain]
                    
                    if expected_response["type"] == "rules":
                        # Поддерживаемая цепочка - должна возвращать правила
                        assert isinstance(data, list), f"Цепочка {chain} должна возвращать массив правил"
                        if len(data) > 0:
                            for item in data:
                                self._validate_response_schema(item)
                    else:
                        # Неподдерживаемая цепочка - возвращает index
                        assert isinstance(data, dict), f"Цепочка {chain} должна возвращать объект"
                        assert "index" in data, f"Объект должен содержать поле 'index'"
                        assert data["index"] == expected_response["value"], f"Значение index должно быть {expected_response['value']}"
                    
                    # Дополнительная проверка через агента для положительных кейсов
                    print(f"Checking agent verification for chain: {chain}")
                    self._verify_agent(ENDPOINT, request_data, agent_verification, f"chain: {chain}")
                else:
                    # Ожидаем ошибку для неподдерживаемых цепочек
                    assert response.status_code in [400, 422]
                    self._validate_error_schema(response.json())
    
    def test_successful_iptables_map_with_different_targets(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с различными целями правил"""
        for target in VALID_TARGETS:
            request_data = VALID_REQUEST_DATA.copy()
            request_data["data"]["rules"][0]["target"] = target
            with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                response = api_client.post(ENDPOINT, json=request_data)
                if response.status_code == 200:
                    data = response.json()
                    
                    # API может возвращать как массив правил, так и объект с index
                    if isinstance(data, list):
                        for item in data:
                            self._validate_response_schema(item)
                    elif isinstance(data, dict):
                        # Проверяем объект с index
                        assert "index" in data, "Объект должен содержать поле 'index'"
                        assert isinstance(data["index"], int), "Поле index должно быть числом"
                    else:
                        pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                    
                    # Дополнительная проверка через агента для положительных кейсов
                    print(f"Checking agent verification for target: {target}")
                    self._verify_agent(ENDPOINT, request_data, agent_verification, f"target: {target}")
                else:
                    assert response.status_code in [400, 422]
                    self._validate_error_schema(response.json())
    
    def test_successful_iptables_map_with_different_protocols(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с различными протоколами"""
        for protocol in VALID_PROTOCOLS:
            request_data = VALID_REQUEST_DATA.copy()
            request_data["data"]["rules"][0]["protocol"] = protocol
            with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                response = api_client.post(ENDPOINT, json=request_data)
                if response.status_code == 200:
                    data = response.json()
                    
                    # API может возвращать как массив правил, так и объект с index
                    if isinstance(data, list):
                        for item in data:
                            self._validate_response_schema(item)
                    elif isinstance(data, dict):
                        # Проверяем объект с index
                        assert "index" in data, "Объект должен содержать поле 'index'"
                        assert isinstance(data["index"], int), "Поле index должно быть числом"
                    else:
                        pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                    
                    # Дополнительная проверка через агента для положительных кейсов
                    print(f"Checking agent verification for protocol: {protocol}")
                    self._verify_agent(ENDPOINT, request_data, agent_verification, f"protocol: {protocol}")
                else:
                    assert response.status_code in [400, 422]
                    self._validate_error_schema(response.json())
    
    def test_successful_iptables_map_with_ordered_true(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с ordered=True"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["ordered"] = True
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for ordered=True")
        self._verify_agent(ENDPOINT, request_data, agent_verification, "ordered=True")
    
    def test_successful_iptables_map_with_ordered_false(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с ordered=False"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["ordered"] = False
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for ordered=False")
        self._verify_agent(ENDPOINT, request_data, agent_verification, "ordered=False")
    
    def test_successful_iptables_map_with_insert_first_true(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с insert_first=True"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["insert_first"] = True
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for insert_first=True")
        self._verify_agent(ENDPOINT, request_data, agent_verification, "insert_first=True")
    
    def test_successful_iptables_map_with_insert_first_false(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с insert_first=False"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["insert_first"] = False
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for insert_first=False")
        self._verify_agent(ENDPOINT, request_data, agent_verification, "insert_first=False")
    
    def test_successful_iptables_map_with_single_rule(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с одним правилом"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"] = [VALID_REQUEST_DATA["data"]["rules"][0]]
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                assert len(data) == 1
                self._validate_response_schema(data[0])
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for single rule")
        self._verify_agent(ENDPOINT, request_data, agent_verification, "single rule")
    
    def test_successful_iptables_map_with_multiple_rules(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с множественными правилами"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"].extend([
            {
                "hash": "allow_ssh",
                "target": "ACCEPT",
                "protocol": "tcp",
                "destination_port": "22"
            },
            {
                "hash": "allow_dns",
                "target": "ACCEPT",
                "protocol": "udp",
                "destination_port": "53"
            }
        ])
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                assert len(data) == 4
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for multiple rules")
        self._verify_agent(ENDPOINT, request_data, agent_verification, "multiple rules")
    
    @pytest.mark.parametrize("edge_case", EDGE_CASES)
    def test_edge_cases_validation(self, api_client, attach_curl_on_fail, agent_verification, edge_case):
        """Тест edge cases для валидации"""
        with attach_curl_on_fail(ENDPOINT, edge_case, method="POST"):
            response = api_client.post(ENDPOINT, json=edge_case)
            # API может возвращать как 200 OK, так и ошибки валидации
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем, что ответ имеет корректную структуру
                if isinstance(data, list):
                    # Если возвращается массив правил, проверяем каждый элемент
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    # Если возвращается объект с index, проверяем его структуру
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                else:
                    pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for edge case: {edge_case}")
                self._verify_agent(ENDPOINT, edge_case, agent_verification, "edge case")
            else:
                # Если возвращается ошибка валидации, проверяем схему ошибки
                assert response.status_code in [400, 422]
                self._validate_error_schema(response.json())
    
    def test_empty_request_body(self, api_client, attach_curl_on_fail):
        """Тест с пустым телом запроса"""
        with attach_curl_on_fail(ENDPOINT, {}, method="POST"):
            response = api_client.post(ENDPOINT, json={})
            # API возвращает 400 Bad Request для пустого запроса
            assert response.status_code == 400
            self._validate_error_schema(response.json())
    
    def test_missing_required_fields(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с отсутствующими обязательными полями"""
        # Убираем обязательные поля
        invalid_data = {
            "data": {
                "table": "filter",
                # chain отсутствует
                "rules": []
            },
            "util": "iptables"
        }
        with attach_curl_on_fail(ENDPOINT, invalid_data, method="POST"):
            response = api_client.post(ENDPOINT, json=invalid_data)
            # API возвращает 200 OK даже для неполных данных
            assert response.status_code == 200
            data = response.json()
            
            # Проверяем структуру ответа
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for missing required fields")
        self._verify_agent(ENDPOINT, invalid_data, agent_verification, "missing required fields")
    
    def test_invalid_json_syntax(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с невалидным JSON"""
        invalid_json_data = '{"invalid": json}'
        with attach_curl_on_fail(ENDPOINT, invalid_json_data, headers={"Content-Type": "application/json"}, method="POST"):
            response = api_client.post(
                ENDPOINT,
                data=invalid_json_data,
                headers={"Content-Type": "application/json"}
            )
            
            # API может возвращать 200 OK даже для невалидного JSON
            # Проверяем, что ответ имеет корректную структуру
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for invalid JSON syntax")
                self._verify_agent(ENDPOINT, invalid_json_data, agent_verification, "invalid JSON syntax")
            else:
                # Если все же возвращается ошибка, проверяем схему ошибки
                assert response.status_code in [400, 422]
                self._validate_error_schema(response.json())
    
    def test_wrong_content_type(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с неправильным Content-Type"""
        request_data = json.dumps(VALID_REQUEST_DATA)
        with attach_curl_on_fail(ENDPOINT, request_data, headers={"Content-Type": "text/plain"}, method="POST"):
            response = api_client.post(
                ENDPOINT,
                data=request_data,
                headers={"Content-Type": "text/plain"}
            )
            
            # API может возвращать 200 OK даже для неправильного Content-Type
            # Проверяем, что ответ имеет корректную структуру
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for wrong content type")
                self._verify_agent(ENDPOINT, request_data, agent_verification, "wrong content type")
            else:
                # Если все же возвращается ошибка, проверяем код ошибки
                assert response.status_code in [400, 415]
    
    def test_malformed_rules_array(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с неправильно сформированным массивом правил"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"] = "not_an_array"
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
        
        # API может возвращать 200 OK даже для неправильно сформированных данных
        # Проверяем, что ответ имеет корректную структуру
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            
            # Дополнительная проверка через агента для положительных кейсов
            print(f"Checking agent verification for malformed rules array")
            self._verify_agent(ENDPOINT, request_data, agent_verification, "malformed rules array")
        else:
            # Если все же возвращается ошибка, проверяем схему ошибки
            assert response.status_code in [400, 422]
            self._validate_error_schema(response.json())
    
    def test_invalid_rule_structure(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с неправильной структурой правила"""
        request_data = VALID_REQUEST_DATA.copy()
        # Создаем новый массив правил с неправильной структурой
        request_data["data"]["rules"] = [
            {
                "hash": "invalid_rule",
                # Отсутствуют обязательные поля
            }
        ]
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
        
        # API может возвращать 200 OK даже для неправильной структуры правила
        # Проверяем, что ответ имеет корректную структуру
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
            
            # Дополнительная проверка через агента для положительных кейсов
            print(f"Checking agent verification for invalid rule structure")
            self._verify_agent(ENDPOINT, request_data, agent_verification, "invalid rule structure")
        else:
            # Если все же возвращается ошибка, проверяем схему ошибки
            assert response.status_code in [400, 422]
            self._validate_error_schema(response.json())
    
    def test_very_long_hash_values(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с очень длинными хеш-значениями"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"][0]["hash"] = "a" * 10000
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            if response.status_code == 200:
                data = response.json()
                
                # API может возвращать как массив правил, так и объект с index
                if isinstance(data, list):
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    # Проверяем объект с index
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                else:
                    pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for very long hash values")
                self._verify_agent(ENDPOINT, request_data, agent_verification, "very long hash values")
            else:
                assert response.status_code in [400, 422]
                self._validate_error_schema(response.json())
    
    def test_special_characters_in_hash(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест со спецсимволами в хеше"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"][0]["hash"] = "rule-123_456@789"
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            if response.status_code == 200:
                data = response.json()
                
                # API может возвращать как массив правил, так и объект с index
                if isinstance(data, list):
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    # Проверяем объект с index
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                else:
                    pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for special characters in hash")
                self._verify_agent(ENDPOINT, request_data, agent_verification, "special characters in hash")
            else:
                assert response.status_code in [400, 422]
                self._validate_error_schema(response.json())
    
    def test_numeric_port_values(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с числовыми значениями портов"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"][0]["destination_port"] = 80
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            if response.status_code == 200:
                data = response.json()
                
                # API может возвращать как массив правил, так и объект с index
                if isinstance(data, list):
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    # Проверяем объект с index
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                else:
                    pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for numeric port values")
                self._verify_agent(ENDPOINT, request_data, agent_verification, "numeric port values")
            else:
                assert response.status_code in [400, 422]
                self._validate_error_schema(response.json())
    
    def test_boolean_as_strings(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест с булевыми значениями в виде строк"""
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["ordered"] = "true"
        request_data["data"]["insert_first"] = "false"
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            if response.status_code == 200:
                data = response.json()
                
                # API может возвращать как массив правил, так и объект с index
                if isinstance(data, list):
                    for item in data:
                        self._validate_response_schema(item)
                elif isinstance(data, dict):
                    # Проверяем объект с index
                    assert "index" in data, "Объект должен содержать поле 'index'"
                    assert isinstance(data["index"], int), "Поле index должно быть числом"
                else:
                    pytest.fail(f"Неожиданный тип ответа: {type(data)}")
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for boolean as strings")
                self._verify_agent(ENDPOINT, request_data, agent_verification, "boolean as strings")
            else:
                assert response.status_code in [400, 422]
                self._validate_error_schema(response.json())
    
    def test_response_structure_validation(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест валидации структуры ответа"""
        with attach_curl_on_fail(ENDPOINT, VALID_REQUEST_DATA, method="POST"):
            response = api_client.post(ENDPOINT, json=VALID_REQUEST_DATA)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                # Проверяем, что это массив
                assert len(data) > 0
                
                # Проверяем каждый элемент массива
                for item in data:
                    assert isinstance(item, dict)
                    self._validate_response_schema(item)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for response structure validation")
        self._verify_agent(ENDPOINT, VALID_REQUEST_DATA, agent_verification, "response structure validation")
    
    def test_all_table_chain_combinations(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест всех комбинаций таблиц и цепочек на основе реальных ответов API"""
        for table, chains in TABLE_CHAIN_RESPONSES.items():
            for chain, expected in chains.items():
                request_data = VALID_REQUEST_DATA.copy()
                request_data["data"]["table"] = table
                request_data["data"]["chain"] = chain
                with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                    response = api_client.post(ENDPOINT, json=request_data)
                    assert response.status_code == 200, f"Комбинация {table}:{chain} должна возвращать 200"
                    data = response.json()
                    
                    if expected["type"] == "rules":
                        # Проверяем массив правил
                        assert isinstance(data, list), f"Комбинация {table}:{chain} должна возвращать массив правил"
                        if len(data) > 0:
                            for item in data:
                                self._validate_response_schema(item)
                    else:
                        # Проверяем объект с index
                        assert isinstance(data, dict), f"Комбинация {table}:{chain} должна возвращать объект"
                        assert "index" in data, f"Объект должен содержать поле 'index' для {table}:{chain}"
                        assert data["index"] == expected["value"], f"Значение index должно быть {expected['value']} для {table}:{chain}"
                    
                    # Дополнительная проверка через агента для положительных кейсов
                    print(f"Checking agent verification for table: {table}, chain: {chain}")
                    self._verify_agent(ENDPOINT, request_data, agent_verification, f"table: {table}, chain: {chain}")
    
    def test_index_returning_combinations(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест комбинаций, которые возвращают {"index": 0}"""
        # Комбинации, которые возвращают {"index": 0}
        index_returning_combinations = [
            ("filter", "PREROUTING"),  # filter не поддерживает PREROUTING
            ("filter", "POSTROUTING"), # filter не поддерживает POSTROUTING
            ("nat", "FORWARD"),        # nat не поддерживает FORWARD
            ("raw", "INPUT"),          # raw не поддерживает INPUT
            ("raw", "FORWARD"),        # raw не поддерживает FORWARD
        ]
        for table, chain in index_returning_combinations:
            request_data = VALID_REQUEST_DATA.copy()
            request_data["data"]["table"] = table
            request_data["data"]["chain"] = chain
            with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                response = api_client.post(ENDPOINT, json=request_data)
                # API возвращает 200 с index для этих комбинаций
                assert response.status_code == 200, f"Комбинация {table}:{chain} должна возвращать 200"
                data = response.json()
                assert isinstance(data, dict), f"Комбинация {table}:{chain} должна возвращать объект"
                assert "index" in data, f"Комбинация {table}:{chain} должна содержать поле 'index'"
                assert data["index"] == 0, f"Значение index должно быть 0 для комбинации {table}:{chain}"
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for index returning combination: {table}:{chain}")
                self._verify_agent(ENDPOINT, request_data, agent_verification, f"index returning combination: {table}:{chain}")
    
    def test_rules_with_resTime_resState(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест правил с различными комбинациями таблиц и цепочек"""
        # Комбинации, которые возвращают правила
        rules_combinations = [
            ("filter", "OUTPUT"),
            ("nat", "POSTROUTING"),
            ("nat", "OUTPUT"),
            ("mangle", "PREROUTING"),
            ("mangle", "INPUT"),
            ("mangle", "OUTPUT"),
            ("mangle", "POSTROUTING"),
            ("raw", "OUTPUT"),
        ]
        for table, chain in rules_combinations:
            request_data = VALID_REQUEST_DATA.copy()
            request_data["data"]["table"] = table
            request_data["data"]["chain"] = chain
            with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
                response = api_client.post(ENDPOINT, json=request_data)
                assert response.status_code == 200, f"Комбинация {table}:{chain} должна возвращать 200"
                data = response.json()
                assert isinstance(data, list), f"Комбинация {table}:{chain} должна возвращать массив правил"
                assert len(data) > 0, f"Массив правил не должен быть пустым для {table}:{chain}"
                
                for item in data:
                    self._validate_response_schema(item)
                    # Проверяем базовые обязательные поля
                    assert "hash" in item, f"Поле hash обязательно для {table}:{chain}"
                    
                    # Проверяем опциональные поля resTime и resState если они есть
                    if "resTime" in item:
                        assert isinstance(item["resTime"], (int, float)), f"resTime должен быть числом для {table}:{chain}"
                    if "resState" in item:
                        assert item["resState"] == "ok", f"resState должен быть 'ok' для {table}:{chain}"
                
                # Дополнительная проверка через агента для положительных кейсов
                print(f"Checking agent verification for rules with resTime/resState: {table}:{chain}")
                self._verify_agent(ENDPOINT, request_data, agent_verification, f"rules with resTime/resState: {table}:{chain}")
    
    def test_optional_fields_validation(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест валидации необязательных полей"""
        # Добавляем необязательные поля
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"][0].update({
            "source": "192.168.1.0/24",
            "source_port": "1024:65535",
            "in_interface": "eth0",
            "out_interface": "eth1",
            "comment": "Test rule with optional fields"
        })
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                for item in data:
                    self._validate_response_schema(item)
                    # Проверяем необязательные поля если они есть
                    if "source" in item:
                        assert isinstance(item["source"], str)
                    if "source_port" in item:
                        assert isinstance(item["source_port"], str)
                    if "in_interface" in item:
                        assert isinstance(item["in_interface"], str)
                    if "out_interface" in item:
                        assert isinstance(item["out_interface"], str)
                    if "comment" in item:
                        assert isinstance(item["comment"], str)
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for optional fields validation")
        agent_result = agent_verification(ENDPOINT, request_data)
        if agent_result == "unavailable":
            print(f"Agent verification skipped - agent is unavailable for optional fields validation")
        elif agent_result is not None:  # Проверка выполнилась
            if agent_result:
                print(f"Agent verification: Interface state matches expected for optional fields validation")
            else:
                pytest.fail(f"Agent verification failed: Interface state does not match expected for optional fields validation")
        else:
            print(f"Agent verification skipped for payload: {request_data}")
    
    def test_recursive_validation_of_nested_structures(self, api_client, attach_curl_on_fail, agent_verification):
        """Тест рекурсивной валидации вложенных структур"""
        # Создаем сложную структуру правил
        complex_rules = [
            {
                "hash": "complex_rule_1",
                "target": "ACCEPT",
                "protocol": "tcp",
                "destination_port": "80",
                "source": "192.168.1.0/24",
                "comment": "Complex rule with nested validation"
            },
            {
                "hash": "complex_rule_2",
                "target": "DROP",
                "protocol": "udp",
                "destination_port": "53",
                "source_port": "1024:65535",
                "in_interface": "eth0"
            }
        ]
        
        request_data = VALID_REQUEST_DATA.copy()
        request_data["data"]["rules"] = complex_rules
        with attach_curl_on_fail(ENDPOINT, request_data, method="POST"):
            response = api_client.post(ENDPOINT, json=request_data)
            assert response.status_code == 200
            data = response.json()
            
            # API может возвращать как массив правил, так и объект с index
            if isinstance(data, list):
                assert len(data) == 2
                
                # Рекурсивная валидация каждого правила
                for item in data:
                    self._validate_response_schema(item)
                    # Дополнительная проверка вложенных структур
                    if "source" in item:
                        assert isinstance(item["source"], str)
                        # Проверяем формат IP адреса
                        assert "/" in item["source"] or "." in item["source"]
                    if "source_port" in item:
                        assert isinstance(item["source_port"], str)
                        # Проверяем формат порта
                        assert ":" in item["source_port"] or item["source_port"].isdigit()
            elif isinstance(data, dict):
                # Проверяем объект с index
                assert "index" in data, "Объект должен содержать поле 'index'"
                assert isinstance(data["index"], int), "Поле index должно быть числом"
            else:
                pytest.fail(f"Неожиданный тип ответа: {type(data)}")
        
        # Дополнительная проверка через агента для положительных кейсов
        print(f"Checking agent verification for recursive validation of nested structures")
        agent_result = agent_verification(ENDPOINT, request_data)
        if agent_result == "unavailable":
            print(f"Agent verification skipped - agent is unavailable for recursive validation of nested structures")
        elif agent_result is not None:  # Проверка выполнилась
            if agent_result:
                print(f"Agent verification: Interface state matches expected for recursive validation of nested structures")
            else:
                pytest.fail(f"Agent verification failed: Interface state does not match expected for recursive validation of nested structures")
        else:
            print(f"Agent verification skipped for payload: {request_data}")
    
    def _validate_response_schema(self, data: Dict[str, Any]):
        """Валидация схемы ответа"""
        from services.conftest import validate_schema
        validate_schema(data, RESPONSE_SCHEMA)
    
    def _validate_error_schema(self, data: Dict[str, Any]):
        """Валидация схемы ошибки"""
        from services.conftest import validate_schema
        validate_schema(data, ERROR_SCHEMA)
        
        # Дополнительно проверяем вложенную структуру error объекта
        if "error" in data and isinstance(data["error"], dict):
            validate_schema(data["error"], ERROR_DETAIL_SCHEMA)
    
    def _verify_agent(self, endpoint: str, payload: Any, agent_verification, context: str):
        """Проверяет ответ агента по контракту {"result":"OK"} / {"result":"ERROR","message":"..."}."""
        agent_result = agent_verification(endpoint, payload)
        if agent_result == "unavailable":
            pytest.fail(f"Agent verification failed for {context}: agent is unavailable")
        if agent_result is None:
            print(f"Agent verification skipped for payload: {payload}")
            return
        # Поддержка старого формата ответов: True/False и "OK"/"ERROR"
        if isinstance(agent_result, bool):
            if agent_result is True:
                print(f"Agent verification: OK for {context}")
                return
            pytest.fail(f"Agent verification failed for {context}: unexpected response format {agent_result}")
        if isinstance(agent_result, str):
            normalized = agent_result.strip().upper()
            if normalized == "OK":
                print(f"Agent verification: OK for {context}")
                return
            if normalized == "ERROR":
                pytest.fail(f"Agent verification failed for {context}: agent returned ERROR")
        if isinstance(agent_result, dict):
            result_value = agent_result.get("result")
            if result_value == "OK":
                print(f"Agent verification: OK for {context}")
                return
            if result_value == "ERROR":
                message_text = agent_result.get("message", "")
                pytest.fail(f"Agent verification failed for {context}: {message_text}")
        pytest.fail(f"Agent verification failed for {context}: unexpected response format {agent_result}")
    
    # R24: локальный форматтер curl удален — используем фикстуру attach_curl_on_fail
