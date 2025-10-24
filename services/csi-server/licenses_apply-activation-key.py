import pytest
import json

# Отдельный тест для проверки агента по эндпоинту /licenses/apply-activation-key
# ВАЖНО: внешняя вендорная служба может отклонять слишком частые запросы,
# связанные с одним и тем же serialNumber (антифрод/дедупликация/рейтлимит).
# Если тесты гоняются многократно и быстро подряд на одном стенде,
# возможны временные ошибки на шагах создания лицензии у вендора
# или обмена activationCode -> activationKey. Рекомендуется выдерживать
# небольшие паузы между прогонами и сценариями.
# Инструкции:
# - Агенту в теле запроса отправляется токен доступа: {"x-access-token": token}
# - Обработка ответа агента:
#   {"result":"OK"} -> успех
#   {"result":"ERROR","message":"..."} -> провал теста с сообщением
#   Любой недоступный/некорректный ответ -> тест должен падать (агента не пропускать)

ENDPOINT = "/licenses/apply-activation-key"


def _print_validation(step: str, ok: bool, details: str = "") -> None:
    msg = f"[validation] step={step} status={'OK' if ok else 'FAIL'}"
    if details:
        msg += f" — {details}"
    print(msg)


def _prepare_agent_payload(auth_token: str) -> dict:
    payload = {"x-access-token": auth_token}
    _print_validation("prepare-payload", True, details=json.dumps(payload))
    return payload


def _handle_agent_response(agent_result):
    # Успех
    if isinstance(agent_result, dict) and agent_result.get("result") == "OK":
        _print_validation("agent-response", True, details="result=OK")
        return

    # Явная ошибка
    if isinstance(agent_result, dict) and agent_result.get("result") == "ERROR":
        message = agent_result.get("message", "unknown error")
        _print_validation("agent-response", False, details=f"result=ERROR message={message}")
        pytest.fail(f"Agent verification failed: {message}")

    # Агент недоступен или неожиданный ответ — падаем (не пропускать)
    _print_validation("agent-response", False, details=f"unexpected={agent_result}")
    pytest.fail("Agent verification unavailable or unexpected response")


def test_licenses_apply_activation_key_agent_verification(agent_verification, auth_token):
    # Шаг 1: подготовка тела запроса к агенту
    payload = _prepare_agent_payload(auth_token)

    # Шаг 2: вызов агента
    _print_validation("agent-request", True, details=f"endpoint={ENDPOINT}")
    agent_result = agent_verification(ENDPOINT, payload)

    # Шаг 3: обработка ответа агента согласно контракту
    _handle_agent_response(agent_result)


## Доработать алгоритм добавление лицензии, когда начнёшь пилить агента. 
# Сделать один-в-один: https://wiki.codemaster.pro/pages/viewpage.action?pageId=115474609

# # Константы
# ENDPOINT = "/licenses/apply-activation-key"
# SUCCESS_RESPONSE_SCHEMA = {
# 	"type": "object",
# 	"properties": {
# 		"serialNumber": {"type": "string"},
# 		"licenseNumber": {"type": "string"},
# 		"bandwidth": {"type": "integer"},
# 		"expiresAt": {"type": "string"}
# 	},
# 	"required": ["serialNumber", "licenseNumber"]
# }


# def _check_types_recursive(obj, schema):
# 	if schema.get("type") == "object":
# 		assert isinstance(obj, dict), f"Expected object, got {type(obj)}"
# 		for key, prop in schema.get("properties", {}).items():
# 			if key in obj:
# 				_check_types_recursive(obj[key], prop)
# 		for req in schema.get("required", []):
# 			assert req in obj, f"Missing required field: {req}"
# 	elif schema.get("type") == "array":
# 		assert isinstance(obj, list) and not isinstance(obj, str), f"Expected array, got {type(obj)}"
# 		if "items" in schema and isinstance(schema["items"], list):
# 			for item, item_schema in zip(obj, schema["items"]):
# 				_check_types_recursive(item, item_schema)
# 		elif "items" in schema and isinstance(schema["items"], dict):
# 			for item in obj:
# 				_check_types_recursive(item, schema["items"])
# 	elif schema.get("type") == "string":
# 		assert isinstance(obj, str), f"Expected string, got {type(obj)}"
# 	elif schema.get("type") == "integer":
# 		assert isinstance(obj, int), f"Expected integer, got {type(obj)}"
# 	elif schema.get("type") == "number":
# 		assert isinstance(obj, (int, float)), f"Expected number, got {type(obj)}"
# 	elif schema.get("type") == "boolean":
# 		assert isinstance(obj, bool), f"Expected boolean, got {type(obj)}"
# 	elif schema.get("type") == "null":
# 		assert obj is None, f"Expected null, got {type(obj)}"


# # --- Helpers for chain generation ---

# def _get_license_number(api_client, api_base_url, auth_token, attach_curl_on_fail):
# 	endpoint = "/licenses"
# 	url = f"{api_base_url}{endpoint}"
# 	headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
# 	with attach_curl_on_fail(endpoint, None, headers, "GET"):
# 		response = api_client.get(url, headers=headers)
# 		assert response.status_code == 200, f"Ожидается 200 OK; получено {response.status_code}"
# 		data = response.json()
# 		assert isinstance(data, dict) and "licenseNumber" in data, "В ответе должен быть licenseNumber"
# 		return data["licenseNumber"]


# def _generate_activation_code(api_client, api_base_url, auth_token, attach_curl_on_fail, license_number, bundled=True):
# 	endpoint = "/licenses/generate-activation-code"
# 	url = f"{api_base_url}{endpoint}"
# 	headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
# 	payload = {"licenseNumber": license_number, "bundled": bundled}
# 	with attach_curl_on_fail(endpoint, payload, headers, "POST"):
# 		resp = api_client.post(url, headers=headers, json=payload)
# 		assert resp.status_code == 200, f"Ожидается 200 OK; получено {resp.status_code}"
# 		data = resp.json()
# 		assert isinstance(data, dict) and "value" in data, "Ожидается поле 'value' (activationCode)"
# 		return data["value"]




# def _exchange_activation_code_for_key(api_client, api_base_url, attach_curl_on_fail, activation_code, bundled=True, auth_token=None, license_number=None, tolerate_not_found=False):
# 	endpoint_for_curl = "/activation-keys/"
# 	url = "http://10.100.103.20/api/activation-keys/"
# 	headers = {"Content-Type": "application/json"}
# 	if auth_token:
# 		headers["x-access-token"] = auth_token
# 	payload = {"activationCode": activation_code, "bundled": bundled}
# 	# Если bundled == False, внешняя служба ожидает явный licenseNumber
# 	if bundled is False and license_number:
# 		payload["licenseNumber"] = license_number.strip() if isinstance(license_number, str) else license_number
# 	with attach_curl_on_fail(endpoint_for_curl, payload, headers, "POST"):
# 		resp = api_client.post(url, headers=headers, json=payload)
# 		if resp.status_code == 200:
# 			data = resp.json()
# 			assert isinstance(data, dict) and "value" in data, "Ожидается поле 'value' (activationKey)"
# 			return data["value"]
# 		elif tolerate_not_found and resp.status_code == 400:
# 			body = resp.json() if resp.content else {}
# 			if body.get("error", {}).get("message") == "license-not-found":
# 				return None
# 			assert False, f"Неожидаемое тело ошибки при 400: {body}"
# 		else:
# 			assert False, f"Ожидается 200 OK; получено {resp.status_code}"


# # --- Chain test based on provided algorithm ---

# def test_generate_and_apply_activation_key_chain(api_client, api_base_url, auth_token, attach_curl_on_fail):
# 	license_number = _get_license_number(api_client, api_base_url, auth_token, attach_curl_on_fail)
# 	activation_code = _generate_activation_code(api_client, api_base_url, auth_token, attach_curl_on_fail, license_number, bundled=True)
# 	activation_key = _exchange_activation_code_for_key(api_client, api_base_url, attach_curl_on_fail, activation_code, bundled=True, auth_token=auth_token)

# 	# Apply activation key
# 	url = f"{api_base_url}{ENDPOINT}"
# 	headers = {"x-access-token": auth_token, "Content-Type": "application/json"}
# 	payload = {"activationKey": activation_key}
# 	with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
# 		resp = api_client.post(url, headers=headers, json=payload)
# 		if resp.status_code == 200:
# 			data = resp.json()
# 			_check_types_recursive(data, SUCCESS_RESPONSE_SCHEMA)
# 		elif resp.status_code == 422:
# 			err = resp.json()
# 			assert isinstance(err, dict) and "error" in err, "Ожидается объект ошибки с полем 'error'"
# 			error_obj = err["error"]
# 			assert error_obj.get("statusCode") == 422, "Ожидается statusCode 422"
# 			assert error_obj.get("name") == "UnprocessableEntityError", "Ожидается имя ошибки UnprocessableEntityError"
# 			assert error_obj.get("message") == "activation-key-already-applied", "Ожидается сообщение activation-key-already-applied"
# 		else:
# 			assert False, f"Неожиданный статус код: {resp.status_code}"

# 	# Re-apply same key -> 422 activation-key-already-applied
# 	with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
# 		resp2 = api_client.post(url, headers=headers, json=payload)
# 		assert resp2.status_code == 422, f"Ожидается 422; получено {resp2.status_code}"
# 		err = resp2.json()
# 		assert isinstance(err, dict) and "error" in err, "Ожидается объект ошибки с полем 'error'"
# 		error_obj = err["error"]
# 		assert error_obj.get("statusCode") == 422, "Ожидается statusCode 422"
# 		assert error_obj.get("name") == "UnprocessableEntityError", "Ожидается имя ошибки UnprocessableEntityError"
# 		assert error_obj.get("message") == "activation-key-already-applied", "Ожидается сообщение activation-key-already-applied"


# # ---------------------------- Позитивные кейсы (параметризованные) ----------------------------

# @pytest.mark.parametrize(
# 	"case",
# 	[
# 		{"name": "bundled_true", "bundled": True},
# 		{"name": "bundled_false", "bundled": False},
# 		{"name": "header_case_insensitive", "bundled": True, "headers_case": True},
# 		{"name": "with_extra_headers", "bundled": True, "extra_headers": {"X-Trace-Id": "t-1"}},
# 		{"name": "repeat_chain_different_code", "bundled": True, "repeat": 2},
# 		{"name": "apply_trimmed_key", "bundled": True, "trim_key": True},
# 		{"name": "double_space_license_number", "bundled": True, "wrap_spaces": True},
# 		{"name": "use_token_header_alias", "bundled": True, "token_header": "X-Access-Token"},
# 		{"name": "json_ct_lowercase", "bundled": True, "ct_header": "content-type"},
# 		{"name": "ct_urlencoded_to_exchange", "bundled": True, "exchange_ct": "application/x-www-form-urlencoded"},
# 		{"name": "ct_mixed_case", "bundled": True, "ct_header": "Content-type"},
# 		{"name": "allow_unicode_license", "bundled": True, "unicode_license": True},
# 		{"name": "long_license", "bundled": True, "long_license": True},
# 		{"name": "no_bundled_field_exchange", "bundled": None},
# 	],
# 	ids=lambda c: c["name"],
# )
# def test_apply_activation_key_positive_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, case):
# 	# Получаем номер лицензии
# 	license_number = _get_license_number(api_client, api_base_url, auth_token, attach_curl_on_fail)
# 	if case.get("wrap_spaces"):
# 		license_number = f"  {license_number}  "
# 	if case.get("unicode_license"):
# 		license_number = f"ЛИЦ-{license_number}"
# 	if case.get("long_license"):
# 		license_number = f"LIC-{license_number}-" + ("0" * 64)

# 	# Генерируем activationCode
# 	bundled_flag = True if case.get("bundled") is None else case.get("bundled")
# 	activation_code = _generate_activation_code(api_client, api_base_url, auth_token, attach_curl_on_fail, license_number, bundled=bundled_flag)

# 	# Обмен на activationKey
# 	activation_key = _exchange_activation_code_for_key(
# 		api_client,
# 		api_base_url,
# 		attach_curl_on_fail,
# 		activation_code,
# 		bundled=case.get("bundled", True),
# 		auth_token=auth_token,
# 		license_number=license_number,
# 		tolerate_not_found=bool(case.get("wrap_spaces") or case.get("unicode_license") or case.get("long_license")),
# 	)

# 	# Подготовка заголовков
# 	headers = {"Content-Type": "application/json"}
# 	if case.get("ct_header"):
# 		# альтернативный заголовок регистра
# 		del headers["Content-Type"]
# 		headers[case["ct_header"]] = "application/json"
# 	if case.get("extra_headers"):
# 		headers.update(case["extra_headers"])
# 	if case.get("token_header"):
# 		headers[case["token_header"]] = auth_token
# 	else:
# 		headers["x-access-token"] = auth_token

# 	# При необходимости "подрезаем" ключ
# 	key_to_apply = activation_key.strip() if case.get("trim_key") else activation_key

# 	# Применяем ключ
# 	url = f"{api_base_url}{ENDPOINT}"
# 	payload = {"activationKey": key_to_apply}
# 	with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
# 		if activation_key is None:
# 			pytest.skip("Внешняя служба вернула license-not-found для пробельного licenseNumber; пропуск кейса wrap_spaces")
			
# 		resp = api_client.post(url, headers=headers, json=payload)
# 		assert resp.status_code in (200, 422), f"Ожидается 200 или 422; получено {resp.status_code}"
# 		if resp.status_code == 200 and resp.content:
# 			_check_types_recursive(resp.json(), SUCCESS_RESPONSE_SCHEMA)
# 		elif resp.status_code == 422:
# 			err = resp.json(); assert err.get("error", {}).get("message") == "activation-key-already-applied"

# 	# Повторное применение всегда должно давать 422
# 	with attach_curl_on_fail(ENDPOINT, payload, headers, "POST"):
# 		retry = api_client.post(url, headers=headers, json=payload)
# 		assert retry.status_code == 422, f"Ожидается 422; получено {retry.status_code}"
# 		err = retry.json(); assert err.get("error", {}).get("message") == "activation-key-already-applied"


# # ---------------------------- Негативные кейсы (параметризованные) ----------------------------

# @pytest.mark.parametrize(
# 	"case",
# 	[
# 		{"name": "no_token", "headers": {"Content-Type": "application/json"}},
# 		{"name": "invalid_token", "headers": {"x-access-token": "invalid", "Content-Type": "application/json"}},
# 		{"name": "no_content_type", "headers": {"x-access-token": "__USE_VALID__"}, "send_raw": True},
# 		{"name": "empty_body", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "raw": "", "send_raw": True, "expect": 400},
# 		{"name": "null_body", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "raw": "null", "send_raw": True, "expect": 400},
# 		{"name": "object_instead_of_string", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {"activationKey": {"v": "x"}}, "expect": 400},
# 		{"name": "array_instead_of_object", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "raw": "[]", "send_raw": True, "expect": 400},
# 		{"name": "wrong_content_type_urlencoded", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/x-www-form-urlencoded"}, "raw": "activationKey=abc", "send_raw": True},
# 		{"name": "too_long_key", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {"activationKey": "A" * 10000}},
# 		{"name": "invalid_base64", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {"activationKey": "not-base64=="}},
# 		{"name": "missing_activationKey", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {} , "expect": 400},
# 		{"name": "number_instead_of_string", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {"activationKey": 12345}, "expect": 400},
# 		{"name": "bool_instead_of_string", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {"activationKey": True}, "expect": 400},
# 		{"name": "null_instead_of_string", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "json": {"activationKey": None}, "expect": 400},
# 		{"name": "invalid_json", "headers": {"x-access-token": "__USE_VALID__", "Content-Type": "application/json"}, "raw": '{"activationKey":"x"', "send_raw": True, "expect": 400},
# 	],
# 	ids=lambda c: c["name"],
# )
# def test_apply_activation_key_negative_cases(api_client, api_base_url, auth_token, attach_curl_on_fail, case):
# 	url = f"{api_base_url}{ENDPOINT}"
# 	# Подбор заголовков
# 	headers = dict(case.get("headers") or {})
# 	if headers.get("x-access-token") == "__USE_VALID__":
# 		headers["x-access-token"] = auth_token
# 	if not any(k.lower() == "content-type" for k in headers.keys()) and not case.get("send_raw"):
# 		headers["Content-Type"] = "application/json"

# 	# Тело запроса
# 	payload = case.get("json")
# 	raw = case.get("raw") if case.get("send_raw") else None

# 	with attach_curl_on_fail(ENDPOINT, payload if not raw else raw, headers, "POST"):
# 		if raw is not None:
# 			resp = api_client.post(url, headers=headers, data=raw)
# 		else:
# 			resp = api_client.post(url, headers=headers, json=payload)

# 		expect = case.get("expect")
# 		if expect is not None:
# 			assert resp.status_code == expect, f"Ожидается {expect}; получено {resp.status_code}"
# 		else:
# 			# Как минимум не 5xx
# 			assert resp.status_code < 500, f"Неожиданный статус сервера: {resp.status_code}"
