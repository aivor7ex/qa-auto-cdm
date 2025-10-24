import pytest
import requests
import json

ENDPOINT = "/vlanInfos/change-stream"


class TestVlanChangeStream:
    def test_stream_connection_and_heartbeat(self, api_client, api_base_url, attach_curl_on_fail):
        """Проверяет только соединение. При падении формирует cURL через attach_curl_on_fail."""
        with attach_curl_on_fail(ENDPOINT, method="GET"):
            with api_client.get(ENDPOINT, stream=True, timeout=5) as response:
                assert response.status_code == 200

    @pytest.mark.parametrize("query_params, description", [
        ("?foo=bar", "Simple unused parameter"),
        ("?limit=100", "Pagination parameter"),
        ("?offset=20", "Offset parameter"),
        ("?sort=name", "Sort parameter"),
        ("?filter={'a':'b'}", "JSON filter parameter"),
        ("?id=12345", "ID parameter"),
        ("?search=my-vlan", "Search parameter"),
        ("?unused_param=", "Parameter with empty value"),
        ("?flag", "Parameter with no value"),
        ("?a=1&b=2&c=3", "Multiple unused parameters"),
        ("?p=<script>alert('xss')</script>", "XSS attempt"),
        ("?p=../../etc/passwd", "Path traversal attempt"),
        ("?p=' OR 1=1;--", "SQL injection attempt"),
        ("?a[0]=1&a[1]=2", "Array-like parameter"),
        ("?u[name]=admin", "Object-like parameter"),
        ("?long_param=" + "a" * 200, "Long parameter value"),
        ("?" + "b" * 100 + "=val", "Long parameter name"),
        ("?%20=%20", "URL-encoded space parameters"),
        ("?emoji=✅", "Unicode emoji in parameter"),
        ("?cyrillic=привет", "Cyrillic characters"),
        ("?null_val=null", "String 'null'"),
        ("?true_val=true", "String 'true'"),
        ("?a=1&a=2", "Duplicate parameter names"),
        ("?q=!@#$%^&*()", "Special characters"),
        ("?q=;,:/?@&=+$", "Reserved characters"),
        ("?p=%00", "Null byte injection attempt"),
        ("?p=1.0", "Float value"),
        ("?p=-1", "Negative value"),
        ("?p=1e6", "Scientific notation"),
        ("?case=sensitive", "Case-sensitive key"),
        ("?CASE=sensitive", "Upper-case key"),
        ("?key=a\\nb\\rc", "Value with newlines"),
        ("?p=None", "String 'None'"),
        ("?p=undefined", "String 'undefined'"),
        ("?p={}", "JSON object string"),
        ("?p=[]", "JSON array string"),
        ("?_p=1", "Leading underscore key"),
        ("?-p=1", "Leading hyphen key"),
    ])
    def test_stream_ignores_query_params(self, api_client, query_params, description, attach_curl_on_fail):
        """Поток должен игнорировать любые параметры и давать heartbeat."""
        url = f"{ENDPOINT}{query_params}"
        response = None
        with attach_curl_on_fail(url, method="GET"):
            with api_client.get(url, stream=True, timeout=5) as response:
                assert response.status_code == 200
                first_line = next(response.iter_lines(decode_unicode=True), None)
                assert first_line, f"[{description}] Нет первой строки"
                try:
                    arr = json.loads(first_line)
                except Exception as e:
                    pytest.fail(f"[{description}] Первая строка не JSON: {first_line}", pytrace=False)
                assert isinstance(arr, list) and len(arr) >= 3, f"[{description}] Ответ не массив или слишком короткий: {arr}"
                assert isinstance(arr[0], str), f"[{description}] Первый элемент не строка: {arr}"
                assert arr[1] == "new", f"[{description}] Второй элемент не 'new': {arr}"
                assert isinstance(arr[2], dict) and "opts" in arr[2], f"[{description}] opts отсутствует: {arr}"
