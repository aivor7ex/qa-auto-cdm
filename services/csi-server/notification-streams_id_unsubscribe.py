import pytest


# Endpoint constants (do not hardcode host/port; use fixtures for base path and client)
ENDPOINT = "/notification-streams/{id}/unsubscribe"
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
def test_unsubscribe_with_token_header(api_client, auth_token, api_base_url, attach_curl_on_fail, stream_id):
    url_path = ENDPOINT.format(id=stream_id)
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(url_path, None, headers, "POST"):
        response = api_client.post(url_path, headers=headers)
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in query
def test_unsubscribe_with_token_query_param(api_client, auth_token, api_base_url, attach_curl_on_fail, stream_id):
    url_path = ENDPOINT.format(id=stream_id)
    params = {"access_token": auth_token}

    with attach_curl_on_fail(url_path, None, None, "POST"):
        response = api_client.post(url_path, params=params)
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in body (x-www-form-urlencoded)
def test_unsubscribe_with_token_form_urlencoded(api_client, auth_token, api_base_url, attach_curl_on_fail, stream_id):
    url_path = ENDPOINT.format(id=stream_id)
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {"access_token": auth_token}

    with attach_curl_on_fail(url_path, data, headers, "POST"):
        response = api_client.post(url_path, headers=headers, data=data)
    assert response.status_code == 200
    data_json = response.json()
    _assert_schema(data_json, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # token in body (multipart/form-data)
def test_unsubscribe_with_token_multipart_form(api_client, auth_token, api_base_url, attach_curl_on_fail, stream_id):
    url_path = ENDPOINT.format(id=stream_id)
    files = {"access_token": (None, auth_token)}

    with attach_curl_on_fail(url_path, {"access_token": auth_token}, None, "POST"):
        response = api_client.post(url_path, files=files)
    assert response.status_code == 400
    # Optionally validate basic error structure without enforcing success schema
    data = response.json()
    assert isinstance(data, dict)
    assert "error" in data and isinstance(data["error"], dict)
    assert data["error"].get("statusCode") == 400


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # empty JSON body, token in header
def test_unsubscribe_with_empty_json_and_header_token(api_client, auth_token, api_base_url, attach_curl_on_fail, stream_id):
    url_path = ENDPOINT.format(id=stream_id)
    headers = {"x-access-token": auth_token, "content-type": "application/json"}

    with attach_curl_on_fail(url_path, {}, headers, "POST"):
        response = api_client.post(url_path, headers=headers, json={})
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize("stream_id", ["alerts", "information", "warnings"])  # trailing slash in path
def test_unsubscribe_with_trailing_slash(api_client, auth_token, api_base_url, attach_curl_on_fail, stream_id):
    url_path = ENDPOINT.format(id=stream_id) + "/"
    headers = {"x-access-token": auth_token}

    with attach_curl_on_fail(url_path, None, headers, "POST"):
        response = api_client.post(url_path, headers=headers)
    assert response.status_code == 200
    data = response.json()
    _assert_schema(data, SUCCESS_RESPONSE_SCHEMA)


@pytest.mark.parametrize(
    "post_kwargs, expected_status, desc",
    [
        ({}, 401, "без токена вообще → 401"),
        ({"headers": {"x-access-token": ""}}, 401, "пустой токен в заголовке → 401"),
        ({"headers": {"x-access-token": "INVALID.TOKEN"}}, 401, "неверный/поддельный токен в заголовке → 401"),
        ({"params": {"access_token": ""}}, 401, "пустой токен в query → 401"),
        ({"params": {"access_token": "INVALID"}}, 401, "неверный токен в query → 401"),
        ({"json": {"access_token": ""}, "headers": {"Content-Type": "application/json"}}, 401, "пустой токен в JSON-теле → 401"),
        ({"json": {"access_token": "INVALID"}, "headers": {"Content-Type": "application/json"}}, 401, "неверный токен в JSON-теле → 401"),
        ({"headers": {"Authorization": "Bearer INVALID"}}, 401, "заголовок Authorization вместо x-access-token → 401"),
        ({"headers": {"Authorization": "Bearer "}}, 401, "Authorization с пустым значением → 401"),
        ({"headers": {"X-Access-Token": "INVALID"}}, 401, "неверное имя заголовка (X-Access-Token) → 401"),
        ({"headers": {"x-access-token": "invalid token"}}, 401, "токен с пробелом внутри → 401"),
        ({"headers": {"x-access-token": "Bearer INVALID"}}, 401, "токен с префиксом Bearer в x-access-token → 401"),
        ({"data": {"access_token": "SOME"}}, 400, "токен в form-urlencoded теле → 400"),
        ({"files": [], "data": {"access_token": "SOME"}}, 400, "токен в multipart/form-data → 400"),
        ({"headers": {"Content-Type": "application/json"}, "json": {}}, 401, "только Content-Type и тело без токена → 401"),
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
        "form_urlencoded_token_bad_request",
        "multipart_form_token_bad_request",
        "json_body_no_token",
    ],
)
def test_unsubscribe_auth_negatives_matrix(api_client, api_base_url, attach_curl_on_fail, post_kwargs, expected_status, desc):
    # Use a representative stream id for negative cases
    url_path = ENDPOINT.format(id="alerts")

    headers_for_curl = post_kwargs.get("headers") if post_kwargs else None
    payload_for_curl = post_kwargs.get("json") if post_kwargs else None

    with attach_curl_on_fail(url_path, payload_for_curl, headers_for_curl, "POST"):
        response = api_client.post(url_path, **post_kwargs)
    assert response.status_code == expected_status, f"{desc}; получено {response.status_code}"


