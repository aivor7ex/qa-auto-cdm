import pytest
import random
import string

ENDPOINT = "CustomRules/apply"

# --- Test Data for Parameterization ---
def generate_random_string(length=10):
    """Generates a random alphanumeric string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Generate ~30 varied sets of parameters and headers to test endpoint stability.
ROBUSTNESS_CASES = []
for i in range(15):
    ROBUSTNESS_CASES.append(pytest.param(
        {generate_random_string(): generate_random_string()}, {}, id=f"random_param_{i}"
    ))
for i in range(15):
    ROBUSTNESS_CASES.append(pytest.param(
        {}, {f"X-{generate_random_string()}": generate_random_string()}, id=f"random_header_{i}"
    ))

# --- Tests ---
@pytest.mark.ids
def test_custom_rules_apply_status_code(api_client, attach_curl_on_fail):
    """
    Tests the basic success case for GET /CustomRules/apply.
    Expects a 204 No Content response.
    """
    with attach_curl_on_fail(ENDPOINT, method="GET"):
        response = api_client.get(ENDPOINT)
        assert response.status_code == 204
        # Body should be empty for 204 response
        assert not response.content

@pytest.mark.ids
@pytest.mark.parametrize("params, headers", ROBUSTNESS_CASES)
def test_custom_rules_apply_robustness(api_client, params, headers, attach_curl_on_fail):
    """
    Verifies that the endpoint ignores any unexpected query parameters or headers
    and consistently returns a 204 No Content response.
    """
    with attach_curl_on_fail(ENDPOINT, payload=params, headers=headers, method="GET"):
        response = api_client.get(ENDPOINT, params=params, headers=headers)
        assert response.status_code == 204
        assert not response.content