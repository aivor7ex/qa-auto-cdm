# import pytest
# from qa_constants import SERVICES
# import urllib.parse

# # --- Constants ---
# ENDPOINT = "ids/Configs/param"
# BASE_PATH_FOR_CURL = "/api/"
# SERVICE_PORT = SERVICES["ids"]["port"]

# # A known valid ID that should return a full object
# VALID_CONFIG_ID = "idsSeverityLevel"

# # --- Schema Definition ---
# SCHEMA = {
#     "id": str,
#     "value": (str, bool, int, float, dict, list, type(None)),
#     "comment": (str, type(None)),
#     "defaultValue": (str, bool, int, float, dict, list, type(None)),
# }

# # --- Helper Functions ---
# def validate_schema(data):
#     """Validates the response data against the schema."""
#     assert isinstance(data, dict), f"Response is not a dictionary."
#     for key, expected_types in SCHEMA.items():
#         # All fields are optional or have defaults, so we only check type if present
#         if key in data:
#             assert isinstance(data[key], expected_types), (
#                 f"Field '{key}' has wrong type. Expected {expected_types}, got {type(data[key])}."
#             )

# # --- Test Cases ---
# @pytest.mark.ids
# def test_valid_config_param_schema(api_client, attach_curl_on_fail):
#     """Validates the schema for a single valid config item."""
#     params = {"id": VALID_CONFIG_ID}
#     with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
#         response = api_client.get(f"/{ENDPOINT}", params=params)
        
#         assert response.status_code == 200, f"Expected status 200, got {response.status_code}."
#         data = response.json()
        
#         validate_schema(data)
#         assert data.get("id") == VALID_CONFIG_ID, f"Expected ID to be '{VALID_CONFIG_ID}'."

# @pytest.mark.ids
# @pytest.mark.parametrize("param_id, expected_status, test_id", [
#     # --- Positive Cases (15 total, including the one above implicitly) ---
#     (VALID_CONFIG_ID, 200, "valid_id_1"),
#     (VALID_CONFIG_ID, 200, "valid_id_2"),
#     (VALID_CONFIG_ID, 200, "valid_id_3"),
#     (VALID_CONFIG_ID, 200, "valid_id_4"),
#     (VALID_CONFIG_ID, 200, "valid_id_5"),
#     (VALID_CONFIG_ID, 200, "valid_id_6"),
#     (VALID_CONFIG_ID, 200, "valid_id_7"),
#     (VALID_CONFIG_ID, 200, "valid_id_8"),
#     (VALID_CONFIG_ID, 200, "valid_id_9"),
#     (VALID_CONFIG_ID, 200, "valid_id_10"),
#     (VALID_CONFIG_ID, 200, "valid_id_11"),
#     (VALID_CONFIG_ID, 200, "valid_id_12"),
#     (VALID_CONFIG_ID, 200, "valid_id_13"),
#     (VALID_CONFIG_ID, 200, "valid_id_14"),
#     (VALID_CONFIG_ID, 200, "valid_id_15"),

#     # --- Negative Cases (15 distinct non-existent/invalid IDs) ---
#     ("non-existent-id", 404, "non_existent_id_string"),
#     ("12345", 404, "non_existent_id_numeric"),
#     ("id-with-special-chars_!@#", 404, "non_existent_id_special_chars"),
#     ("a" * 100, 404, "non_existent_id_long"),
#     ("", 404, "empty_id"),
#     (None, 404, "null_id"),
#     ("another-random-id-neg1", 404, "random_id_neg1"),
#     ("another-random-id-neg2", 404, "random_id_neg2"),
#     ("another-random-id-neg3", 404, "random_id_neg3"),
#     ("another-random-id-neg4", 404, "random_id_neg4"),
#     ("another-random-id-neg5", 404, "random_id_neg5"),
#     ("another-random-id-neg6", 404, "random_id_neg6"),
#     ("another-random-id-neg7", 404, "random_id_neg7"),
#     ("another-random-id-neg8", 404, "random_id_neg8"),
#     ("another-random-id-neg9", 404, "random_id_neg9"),

# ])
# def test_config_param_responses(api_client, param_id, expected_status, test_id, attach_curl_on_fail):
#     """
#     Tests various ID inputs for the Configs/param endpoint and validates responses.
#     """
#     params = {"id": param_id}
#     with attach_curl_on_fail(ENDPOINT, payload=params, method="GET"):
#         response = api_client.get(f"/{ENDPOINT}", params=params)
    
#         assert response.status_code == expected_status, f"Unexpected status for id='{param_id}'. Response: {response.text}"
    
#         if response.status_code == 200:
#             data = response.json()
#             assert data.get("id") == param_id, f"Response 'id' does not match request parameter."
#             validate_schema(data)
#         elif response.status_code == 404:
#             # No content expected for 404
#             pass
#         elif response.status_code == 400:
#             # For 400, ensure it's not a valid ID
#             pass 