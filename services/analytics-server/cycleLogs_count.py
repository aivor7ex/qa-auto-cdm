import pytest
import random
import string

# --- Constants ---

ENDPOINT = "/cycleLogs/count"

# --- Schema ---

COUNT_SCHEMA = {
    "count": int
}

# --- Parameters for Test ---
PARAMS = [
    ("case_alpha", {"alpha": "abcde12345"}),
    ("case_numeric", {"num": "9876543210"}),
    ("case_special", {"spec": "!@#%&*()_"}),
    ("case_empty", {"empty": ""}),
    ("case_unicode", {"uni": "тестЮникод"}),
]


# --- Tests ---

@pytest.mark.parametrize("name, params", PARAMS)
def test_cycle_logs_count(api_client, name, params, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        response_data = response.json()
        assert isinstance(response_data, dict)
        for field, f_type in COUNT_SCHEMA.items():
            assert field in response_data, f"Mandatory key '{field}' is missing"
            assert isinstance(response_data[field], f_type), f"Key '{field}' has wrong type"
        assert response_data["count"] >= 0, f"Count must be non-negative, but got {response_data['count']}" 