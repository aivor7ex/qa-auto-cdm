import pytest
import json

ENDPOINT = "/utils/ping"

# Схема успешного ответа
RESPONSE_SCHEMA = {
    "required": {"pid": int},
    "optional": {},
}

# Локальный валидатор схемы (рекурсивная проверка)
def validate_schema(data, schema):
    if isinstance(data, list):
        for item in data:
            validate_schema(item, schema)
        return
    assert isinstance(data, dict), f"Ожидался dict, получено: {type(data).__name__}"
    for key, expected_type in schema.get("required", {}).items():
        assert key in data, f"Отсутствует обязательное поле '{key}': {json.dumps(data, ensure_ascii=False, indent=2)}"
        actual_type = type(data[key])
        if isinstance(expected_type, tuple):
            assert actual_type in expected_type, (
                f"Поле '{key}' имеет тип {actual_type.__name__}, ожидалось одно из {[t.__name__ for t in expected_type]}"
            )
        else:
            assert actual_type is expected_type, (
                f"Поле '{key}' имеет тип {actual_type.__name__}, ожидался {expected_type.__name__}"
            )
    for key, expected_type in schema.get("optional", {}).items():
        if key in data and data[key] is not None:
            actual_type = type(data[key])
            if isinstance(expected_type, tuple):
                assert actual_type in expected_type, (
                    f"Необязательное поле '{key}' имеет тип {actual_type.__name__}, ожидалось одно из {[t.__name__ for t in expected_type]}"
                )
            else:
                assert actual_type is expected_type, (
                    f"Необязательное поле '{key}' имеет тип {actual_type.__name__}, ожидался {expected_type.__name__}"
                )

# Универсальная проверка ошибки
def validate_error(resp_json):
    assert isinstance(resp_json, dict), f"Ожидался dict, получено: {type(resp_json).__name__}"
    if "detail" in resp_json:
        assert isinstance(resp_json["detail"], (str, list)), "detail должен быть str или list"
        return
    assert "error" in resp_json, f"Ожидались поля 'detail' или 'error', получено: {json.dumps(resp_json, ensure_ascii=False)}"
    err = resp_json["error"]
    assert isinstance(err, dict), "'error' должен быть объектом"
    assert "statusCode" in err and isinstance(err["statusCode"], int), "error.statusCode обязателен и целое число"
    assert "message" in err and isinstance(err["message"], str), "error.message обязателен и строка"
    if "name" in err:
        assert isinstance(err["name"], str)
    if "stack" in err and err["stack"] is not None:
        assert isinstance(err["stack"], str)

@pytest.mark.parametrize(
    "payload, expected_status, expect_success",
    [
        # 1. Минимальный
        ({"addr": "8.8.8.8"}, 200, True),
        # 2. Только source
        ({"addr": "8.8.4.4", "source": "eth0"}, 200, True),
        # 3. Только period (дробное)
        ({"addr": "1.1.1.1", "period": 0.5}, 200, True),
        # 4. Только payloadSize
        ({"addr": "1.0.0.1", "payloadSize": 1200}, 200, True),
        # 5. pmtuDefinition: "do"
        ({"addr": "9.9.9.9", "pmtuDefinition": "do"}, 200, True),
        # 6. pmtuDefinition: "want"
        ({"addr": "9.9.9.10", "pmtuDefinition": "want"}, 200, True),
        # 7. pmtuDefinition: "dont"
        ({"addr": "9.9.9.11", "pmtuDefinition": "dont"}, 200, True),
        # 8. Только timeout
        ({"addr": "example.com", "timeout": 2}, 200, True),
        # 9. Только packetsAmount (минимум)
        ({"addr": "8.8.8.8", "packetsAmount": 1}, 200, True),
        # 10. packetsAmount на верхней границе (65535)
        ({"addr": "8.8.4.4", "packetsAmount": 65535}, 200, True),
        # 11. Полный набор параметров
        ({"addr": "8.8.8.8", "source": "eth1", "period": 1, "payloadSize": 1200, "pmtuDefinition": "do", "timeout": 3, "packetsAmount": 5}, 200, True),
        # 12. Отсутствует обязательный addr → реальный API возвращает 400
        ({}, 400, False),
        # 13. Неверный тип timeout (строка)
        ({"addr": "8.8.8.8", "timeout": "2"}, 400, False),
        # 14. Неверное значение pmtuDefinition
        ({"addr": "8.8.8.8", "pmtuDefinition": "invalid"}, 200, False),
        # 15. Некорректный packetsAmount (0)
        ({"addr": "8.8.8.8", "packetsAmount": 0}, 200, False),
        # 16. Некорректный packetsAmount (>65535)
        ({"addr": "8.8.8.8", "packetsAmount": 65536}, 200, False),
        # 17. Неверный тип period (строка)
        ({"addr": "1.1.1.1", "period": "0.5"}, 400, False),
        # 18. Неверный тип payloadSize (строка)
        ({"addr": "1.0.0.1", "payloadSize": "1200"}, 400, False),
        # 19. payloadSize = 0 (edge)
        ({"addr": "1.0.0.1", "payloadSize": 0}, 200, False),
        # 20. payloadSize = 65536 (edge)
        ({"addr": "1.0.0.1", "payloadSize": 65536}, 200, False),
        # 21. period = 0 (edge)
        ({"addr": "1.1.1.1", "period": 0}, 200, False),
        # 22. period = -1 (edge)
        ({"addr": "1.1.1.1", "period": -1}, 200, False),
        # 23. timeout = 0 (edge)
        ({"addr": "8.8.8.8", "timeout": 0}, 200, False),
        # 24. timeout = -1 (edge)
        ({"addr": "8.8.8.8", "timeout": -1}, 200, False),
        # 25. source: пустая строка
        ({"addr": "8.8.8.8", "source": ""}, 200, False),
        # 26. source: спецсимволы
        ({"addr": "8.8.8.8", "source": "eth0$!@#"}, 200, False),
        # 27. addr: домен с тире
        ({"addr": "test-domain.com"}, 200, True),
        # 28. addr: длинная строка
        ({"addr": "a"*255}, 200, False),
        # 29. addr: спецсимволы
        ({"addr": "!@#$.com"}, 200, False),
        # 30. addr: пустая строка
        ({"addr": ""}, 400, False),
        # 31. Неизвестный параметр
        ({"addr": "8.8.8.8", "unknown": 123}, 200, False),
        # 32. Все параметры null
        ({"addr": None, "source": None, "period": None, "payloadSize": None, "pmtuDefinition": None, "timeout": None, "packetsAmount": None}, 400, False),
        # 33. Невалидный JSON (строка вместо объекта)
        ("not a json", 400, False),
        # 34. Невалидный JSON (массив вместо объекта)
        ([{"addr": "8.8.8.8"}], 400, False),
        # 35. Пустое тело
        (None, 400, False),
        # 36. Неверный Content-Type (ожидаем 400 как общий случай)
        ({"addr": "8.8.8.8"}, 400, False),
        # 37. packetsAmount: строка
        ({"addr": "8.8.8.8", "packetsAmount": "five"}, 400, False),
        # 38. payloadSize: null
        ({"addr": "8.8.8.8", "payloadSize": None}, 400, False),
        # 39. period: null
        ({"addr": "8.8.8.8", "period": None}, 400, False),
        # 40. timeout: null
        ({"addr": "8.8.8.8", "timeout": None}, 400, False),
    ]
)
def test_post_utils_ping(api_client, attach_curl_on_fail, agent_verification, payload, expected_status, expect_success):
    """
    Тестирует POST /utils/ping на валидность схемы, коды ответа и обработку ошибок.
    """
    def do_request(payload, content_type="application/json"):
        if payload is None:
            return api_client.post(ENDPOINT, data=None, headers={"Content-Type": content_type})
        if isinstance(payload, str):
            return api_client.post(ENDPOINT, data=payload, headers={"Content-Type": content_type})
        if isinstance(payload, list):
            return api_client.post(ENDPOINT, data=json.dumps(payload), headers={"Content-Type": content_type})
        return api_client.post(ENDPOINT, json=payload, headers={"Content-Type": content_type})

    with attach_curl_on_fail(ENDPOINT, payload):
        # Спецкейс: неверный Content-Type
        if isinstance(payload, dict) and expected_status == 400 and "addr" in payload and len(payload) == 1:
            resp = api_client.post(ENDPOINT, json=payload, headers={"Content-Type": "text/plain"})
        else:
            resp = do_request(payload)
        assert resp.status_code == expected_status, f"Статус {resp.status_code}, ожидался {expected_status}. Ответ: {resp.text}"
        
        if expect_success:
            validate_schema(resp.json(), RESPONSE_SCHEMA)
            
            # Agent verification is disabled per instruction
            # # Дополнительная проверка агента для позитивных тестовых случаев
            # if isinstance(payload, dict) and "addr" in payload:
            #     print(f"Цель проверки агента: Проверка выполнения ping операции")
            #     print(f"Минимальные входные данные для проверки: {json.dumps(payload, ensure_ascii=False)}")
            #     # Выполняем проверку через агента
            #     agent_result = agent_verification("/utils/ping", payload)
            #     # Обрабатываем результат проверки агента
            #     if agent_result == "unavailable":
            #         pytest.fail("Агент недоступен. Тест не может быть выполнен корректно.")
            #     elif agent_result.get("result") == "OK":
            #         print("Agent verification: Проверка успешна - агент подтвердил выполнение операции")
            #     elif agent_result.get("result") == "ERROR":
            #         message = agent_result.get("message", "Неизвестная ошибка")
            #         pytest.fail(f"Agent verification: Ошибка - агент сообщил о проблеме в выполнении операции: {message}")
            #     else:
            #         pytest.fail(f"Agent verification: Неожиданный результат - {agent_result}")
        elif resp.status_code in (400, 422):
            validate_error(resp.json())
