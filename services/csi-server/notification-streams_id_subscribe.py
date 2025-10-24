import pytest


# Endpoint constants (do not hardcode host/port; use fixtures for base path and client)
ENDPOINT = "/notification-streams/{id}/subscribe"

# Success response schema derived from example: {"count": 1}
SUCCESS_RESPONSE_SCHEMA = {"count": int}


def _assert_schema(value, schema):
    """Recursively validate that "value" matches the provided "schema" types."""
    if schema is None:
        assert value is None
        return
    if isinstance(schema, type):
        assert isinstance(value, schema)
        return
    if isinstance(schema, dict):
        assert isinstance(value, dict)
        for key, sub_schema in schema.items():
            assert key in value
            _assert_schema(value[key], sub_schema)
        return
    if isinstance(schema, list):
        assert isinstance(value, list)
        if len(schema) == 0:
            return
        sub_schema = schema[0]
        for item in value:
            _assert_schema(item, sub_schema)
        return
    raise AssertionError("Unsupported schema type: {}".format(type(schema)))


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in header (baseline)
def test_subscribe_with_token_header(api_client, api_base_url, auth_token, attach_curl_on_fail, request, stream_id):
    url = f"{api_base_url}{ENDPOINT.format(id=stream_id)}"
    token = auth_token
    headers = {"x-access-token": token}

    with attach_curl_on_fail(ENDPOINT.format(id=stream_id), None, headers, "POST"):
        response = api_client.post(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in query
def test_subscribe_with_token_query_param(api_client, api_base_url, auth_token, attach_curl_on_fail, request, stream_id):
    url = f"{api_base_url}{ENDPOINT.format(id=stream_id)}"
    token = auth_token
    params = {"access_token": token}

    with attach_curl_on_fail(ENDPOINT.format(id=stream_id), None, None, "POST"):
        response = api_client.post(url, params=params)
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in body (x-www-form-urlencoded)
def test_subscribe_with_token_form_urlencoded(api_client, api_base_url, auth_token, attach_curl_on_fail, request, stream_id):
    url = f"{api_base_url}{ENDPOINT.format(id=stream_id)}"
    token = auth_token
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"access_token": token}

    with attach_curl_on_fail(ENDPOINT.format(id=stream_id), data, headers, "POST"):
        response = api_client.post(url, headers=headers, data=data)
    assert response.status_code == 200
    data_json = response.json()
    _assert_schema(data_json, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in body (multipart/form-data)
def test_subscribe_with_token_multipart_form(api_client, api_base_url, auth_token, attach_curl_on_fail, request, stream_id):
    url = f"{api_base_url}{ENDPOINT.format(id=stream_id)}"
    token = auth_token
    files = {"access_token": (None, token)}

    with attach_curl_on_fail(ENDPOINT.format(id=stream_id), None, None, "POST"):
        response = api_client.post(url, files=files)
    # API responds with 400 for multipart; assert real behavior per R16/R17
    assert response.status_code == 400


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # empty JSON body, token in header
def test_subscribe_with_empty_json_and_header_token(api_client, api_base_url, auth_token, attach_curl_on_fail, request, stream_id):
    url = f"{api_base_url}{ENDPOINT.format(id=stream_id)}"
    token = auth_token
    headers = {"x-access-token": token, "Content-Type": "application/json"}

    with attach_curl_on_fail(ENDPOINT.format(id=stream_id), {}, headers, "POST"):
        response = api_client.post(url, headers=headers, json={})
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # trailing slash in path
def test_subscribe_with_trailing_slash(api_client, api_base_url, auth_token, attach_curl_on_fail, request, stream_id):
    url = f"{api_base_url}{ENDPOINT.format(id=stream_id)}/"
    token = auth_token
    headers = {"x-access-token": token}

    with attach_curl_on_fail(ENDPOINT.format(id=stream_id) + "/", None, headers, "POST"):
        response = api_client.post(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)



# ----- ДОПОЛНИТЕЛЬНЫЕ НЕГАТИВНЫЕ КЕЙСЫ -----
@pytest.mark.parametrize(
    "post_kwargs, expected_status, desc",
    [
        ({}, 401, "без токена вообще → 401"),
        ({"headers": {"x-access-token": ""}}, 401, "пустой токен в заголовке → 401"),
        ({"headers": {"x-access-token": "INVALID.TOKEN"}}, 401, "неверный токен в заголовке → 401"),
        ({"params": {"access_token": ""}}, 401, "пустой токен в query → 401"),
        ({"params": {"access_token": "INVALID"}}, 401, "неверный токен в query → 401"),
        ({"json": {"access_token": ""}, "headers": {"Content-Type": "application/json"}}, 401, "пустой токен в JSON-теле → 401"),
        ({"json": {"access_token": "INVALID"}, "headers": {"Content-Type": "application/json"}}, 401, "неверный токен в JSON-теле → 401"),
        ({"headers": {"Authorization": "Bearer INVALID"}}, 401, "заголовок Authorization вместо x-access-token → 401"),
        ({"headers": {"Authorization": "Bearer "}}, 401, "Authorization с пустым значением → 401"),
        ({"headers": {"X-Access-Token": "INVALID"}}, 401, "неверное имя заголовка (X-Access-Token) → 401"),
        ({"headers": {"x-access-token": "invalid token"}}, 401, "токен с пробелом внутри → 401"),
        ({"headers": {"x-access-token": "Bearer INVALID"}}, 401, "токен с префиксом Bearer в x-access-token → 401"),
    ],
    ids=[
        "no_token_anywhere",
        "empty_hdr",
        "invalid_hdr",
        "empty_query",
        "invalid_query",
        "empty_body_json",
        "invalid_body_json",
        "auth_header_instead",
        "auth_header_empty",
        "wrong_header_name_capitalized",
        "invalid_hdr_with_space",
        "bearer_in_hdr_value",
    ],
)
def test_subscribe_auth_negatives_matrix(api_client, api_base_url, post_kwargs, expected_status, desc, attach_curl_on_fail):
    url = f"{api_base_url}{ENDPOINT.format(id='alerts')}"

    headers_for_curl = post_kwargs.get("headers") if post_kwargs else None
    payload_for_curl = post_kwargs.get("json") if post_kwargs else None

    with attach_curl_on_fail(ENDPOINT.format(id='alerts'), payload_for_curl, headers_for_curl, "POST"):
        response = api_client.post(url, **post_kwargs)
    assert response.status_code == expected_status, f"{desc}; получено {response.status_code}"

