"""
Test for the /api/log-records/html endpoint.
"""
import pytest
import random
import string
import re

# --- Fixtures ---

@pytest.fixture(scope="module")
def api_response(api_client):
    """
    Performs a single, clean GET request to the endpoint and returns the response object.
    """
    response = api_client.get("/log-records/html")
    return response

@pytest.fixture(scope="module")
def html_content(api_response):
    """
    Extracts the HTML content from the response.
    """
    assert api_response.status_code == 200, \
        f"Expected status code 200, but got {api_response.status_code}"
    content = api_response.text
    assert content, "HTML response content should not be empty."
    return content

# --- Core HTML Structure Tests ---

def test_status_code(api_response):
    """
    Tests that the API returns a 200 OK status code.
    """
    assert api_response.status_code == 200

def test_doctype_present(html_content):
    """
    Checks for the presence of a DOCTYPE declaration.
    """
    assert html_content.lower().strip().startswith("<!doctype html>")

def test_html_body_head_tags_present(html_content):
    """
    Ensures the basic <html>, <head>, and <body> tags exist.
    """
    assert "<html" in html_content.lower()
    assert "</html" in html_content.lower()
    assert "<head" in html_content.lower()
    assert "</head" in html_content.lower()
    assert "<body" in html_content.lower()
    assert "</body>" in html_content.lower()

def test_title_is_present_and_not_empty(html_content):
    """
    Verifies that there is a non-empty <title> tag.
    """
    match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
    assert match, "The <title> tag is missing."
    assert match.group(1).strip(), "The <title> should not be empty."

# --- Parametrized Structure and Robustness Tests ---

# List of essential substrings to verify the basic structure of the <head>
head_structure_params = [
    '<meta charset="UTF-8">',
    '<meta name="viewport"',
    'content="width=device-width',
    '<meta http-equiv="X-UA-Compatible"',
    '<style type="text/css">',
]

@pytest.mark.parametrize("substring", head_structure_params)
def test_head_contains_essential_elements(html_content, substring):
    """
    Parametrized test to check for key elements within the <head> tag.
    """
    # Use regex to isolate the head content for a more robust check
    head_content = re.search(r"<head>(.*?)</head>", html_content, re.DOTALL | re.IGNORECASE)
    assert head_content, "Could not find <head> section."
    assert substring in head_content.group(1)

# --- Robustness Test with Random Parameters ---

def generate_random_string(length=8):
    """Generates a random string for parameter names and values."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Generate 30 sets of random query parameters to test endpoint stability
robustness_params = [
    {generate_random_string(): generate_random_string()} for _ in range(30)
]


@pytest.mark.parametrize("params", robustness_params)
def test_endpoint_handles_unexpected_params(api_client, params, attach_curl_on_fail):
    with attach_curl_on_fail("/log-records/html", params, method="GET"):
        response = api_client.get("/log-records/html", params=params)
        assert response.status_code == 200
        content = response.text
        assert content, "HTML response should not be empty when random params are provided."
        assert "<html" in content.lower()
        assert "</body>" in content.lower() 