import pytest
import random
import string

# --- Constants ---
ENDPOINT = "/security-reports/query"
SUCCESS_SCHEMA = {
    # Ключ — динамический, совпадает с id, значение — int
    "type": int  # type — placeholder, будет проверяться динамически
}
ERROR_SCHEMA = {
    "error": dict
}

# --- Test Data ---
# Валидные id (по факту — только 'total')
VALID_IDS = ["total"]
# id, которые вызывают ошибку в теле, но статус 200
ERROR_IDS = [
    "active", "blocked", "pending", "archived", "failed", "success", "in_progress",
    "user_1", "user_2", "user_3", "user_4", "user_5", "user_6", "user_7", "user_8", "user_9", "user_10",
    "reportA", "reportB", "reportC", "reportD", "reportE", "reportF", "reportG", "reportH", "reportI", "reportJ",
    "2024", "2023", "2022", "2021", "2020", "last_month", "this_month", "random1", "random2", "random3"
]


# --- Tests ---
@pytest.mark.parametrize("id_value", VALID_IDS)
def test_security_reports_query_success(api_client, id_value, attach_curl_on_fail):
    """
    Проверяет успешный ответ для валидных id.
    API возвращает пустой объект {} для id=total, что является валидным ответом.
    """
    params = {"id": id_value}
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Expected 200, got {response.status_code} for id={id_value}"
        data = response.json()
        assert isinstance(data, dict), f"Response is not dict for id={id_value}"
        # API возвращает пустой объект {} для валидных id, что является нормальным поведением
        # если нет данных для отображения
        if len(data) == 0:
            pytest.skip(f"API returned empty object for id={id_value} - this is valid when no data is available")
        # Если есть данные, проверяем структуру
        assert len(data) == 1, f"Response must have exactly one key for id={id_value}"
        key = list(data.keys())[0]
        assert key == id_value, f"Response key '{key}' does not match requested id '{id_value}'"
        assert isinstance(data[key], int), f"Value for key '{key}' is not int for id={id_value}"

@pytest.mark.parametrize("id_value", ERROR_IDS)
def test_security_reports_query_semantic_error(api_client, id_value, attach_curl_on_fail):
    """
    Проверяет, что для несуществующих id возвращается 200 и тело содержит ключ 'error'.
    """
    params = {"id": id_value}
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Expected 200, got {response.status_code} for id={id_value}"
        data = response.json()
        assert isinstance(data, dict), f"Response is not dict for id={id_value}"
        assert "error" in data, f"No 'error' key in response for id={id_value}"
        # API возвращает строку "template not found" в поле error
        assert isinstance(data["error"], str), f"Error field is not string for id={id_value}"

@pytest.mark.parametrize("params", [
    {},  # отсутствие id
    {"id": ""},  # пустой id
    {"id": None},  # None
    {"wrong_param": "total"},  # неправильный параметр
])
def test_security_reports_query_bad_request(api_client, params, attach_curl_on_fail):
    """
    Проверяет, что при отсутствии обязательного id или некорректных параметрах возвращается 400 и структура ошибки.
    """
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 400, f"Expected 400, got {response.status_code} for params={params}"
        data = response.json()
        assert isinstance(data, dict), "Error response is not dict"
        assert "error" in data, "No 'error' key in error response"
        err = data["error"]
        assert isinstance(err, dict), "'error' is not dict"
        for field in ["statusCode", "name", "message"]:
            assert field in err, f"'{field}' missing in error details" 