import pytest
import random
import string
import csv
import re
from io import StringIO
from datetime import datetime

# --- Constants ---

ENDPOINT = "/cycleLogs/csv"
EXPECTED_CSV_HEADER = ["Дата и время", "Критичность", "Подсистема", "Сообщение", "Результат", "Пользователь"]

# --- Parameters for Test ---
PARAMS = [
    ("case_alpha", {"alpha": "abcde12345"}),
    ("case_numeric", {"num": "9876543210"}),
    ("case_special", {"spec": "!@#%&*()_"}),
    ("case_empty", {"empty": ""}),
    ("case_unicode", {"uni": "тестЮникод"}),
]

# --- Helper Functions ---

def is_iso_datetime(s):
    """Checks if a string is a valid ISO 8601 datetime."""
    if not isinstance(s, str): return False
    try:
        datetime.fromisoformat(s.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError): return False

# --- Tests ---

@pytest.mark.parametrize("name, params", PARAMS)
def test_cycle_logs_csv(api_client, name, params, attach_curl_on_fail):
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        response = api_client.get(ENDPOINT, params=params)
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        response_text = response.text
        assert response_text, "CSV response is empty."
        csv_file = StringIO(response_text)
        reader = csv.reader(csv_file)
        header = next(reader)
        assert header == EXPECTED_CSV_HEADER, f"CSV header is incorrect. Expected {EXPECTED_CSV_HEADER}, got {header}"
        header_col_count = len(header)
        for i, row in enumerate(reader):
            assert len(row) == header_col_count, f"Row {i+1} has incorrect column count. Expected {header_col_count}, got {len(row)}"
            assert is_iso_datetime(row[0]), f"First column in row {i+1} is not a valid ISO date: {row[0]}" 