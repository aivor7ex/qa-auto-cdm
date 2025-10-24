import pytest
import random
import string

# --- Constants ---

ENDPOINT_TEMPLATE = "/cycleLogs/{}/exists"

# --- Schemas ---

EXISTS_SCHEMA = {
    "exists": bool
}

# --- Parameters for Tests ---

# Parameters for checking existing IDs. The value is not used, it's for parameterization.
EXISTING_ID_PARAMS = [
    (f"random_run_{i}", i)
    for i in range(20)
]

# Parameters for checking non-existing IDs. Using static predefined IDs.
NON_EXISTING_ID_PARAMS = [
    ("non_existing_1", "static_id_1"),
    ("non_existing_2", "static_id_2"),
    ("non_existing_3", "static_id_3"),
    ("non_existing_4", "static_id_4"),
    ("non_existing_5", "static_id_5"),
    ("non_existing_6", "static_id_6"),
    ("non_existing_7", "static_id_7"),
    ("non_existing_8", "static_id_8"),
    ("non_existing_9", "static_id_9"),
    ("non_existing_10", "static_id_10"),
    ("non_existing_11", "static_id_11"),
    ("non_existing_12", "static_id_12"),
    ("non_existing_13", "static_id_13"),
    ("non_existing_14", "static_id_14"),
    ("non_existing_15", "static_id_15"),
    ("non_existing_16", "static_id_16"),
    ("non_existing_17", "static_id_17"),
    ("non_existing_18", "static_id_18"),
    ("non_existing_19", "static_id_19"),
    ("non_existing_20", "static_id_20")
]

# --- Tests ---

@pytest.mark.parametrize("name, run_index", EXISTING_ID_PARAMS)
def test_existing_log_id_exists(api_client, name, run_index, attach_curl_on_fail):
    logs_response = api_client.get("/cycleLogs")
    assert logs_response.status_code == 200, f"Expected 200 OK, got {logs_response.status_code}"
    logs_data = logs_response.json()
    assert isinstance(logs_data, list)
    assert logs_data, "Could not retrieve any logs to test for existence."
    log_item = random.choice(logs_data)
    assert "id" in log_item, "Log item is missing 'id' field."
    log_id = log_item["id"]
    endpoint = ENDPOINT_TEMPLATE.format(log_id)
    with attach_curl_on_fail(endpoint, method="GET"):
        exists_response = api_client.get(endpoint)
        assert exists_response.status_code == 200, f"Expected 200 OK, got {exists_response.status_code}"
        response_data = exists_response.json()
        assert isinstance(response_data, dict)
        for field, f_type in EXISTS_SCHEMA.items():
            assert field in response_data, f"Mandatory key '{field}' is missing"
            assert isinstance(response_data[field], f_type), f"Key '{field}' has wrong type"
        assert response_data["exists"] is True, "Endpoint reported a valid ID does not exist."

@pytest.mark.parametrize("name, non_existing_id", NON_EXISTING_ID_PARAMS)
def test_non_existing_log_id_exists(api_client, name, non_existing_id, attach_curl_on_fail):
    endpoint = ENDPOINT_TEMPLATE.format(non_existing_id)
    with attach_curl_on_fail(endpoint, method="GET"):
        exists_response = api_client.get(endpoint)
        assert exists_response.status_code == 200, f"Expected 200 OK, got {exists_response.status_code}"
        response_data = exists_response.json()
        assert isinstance(response_data, dict)
        for field, f_type in EXISTS_SCHEMA.items():
            assert field in response_data, f"Mandatory key '{field}' is missing"
            assert isinstance(response_data[field], f_type), f"Key '{field}' has wrong type"
        assert response_data["exists"] is False, "Endpoint reported a non-valid ID exists."