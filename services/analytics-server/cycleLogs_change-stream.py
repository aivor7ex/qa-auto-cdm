import pytest
import random
import string

ENDPOINT = "/cycleLogs/change-stream"

# Уменьши до 5 тестов - нет смысла гонять 35 раз один и тот же кейс
PARAMS = [
    ("case_alpha", {"alpha": "abcde12345"}),
    ("case_numeric", {"num": "9876543210"}),
    ("case_special", {"spec": "!@#%&*()_"}),
    ("case_empty", {"empty": ""}),
    ("case_unicode", {"uni": "тестЮникод"}),
]

@pytest.mark.parametrize("name, params", PARAMS)
def test_cycle_logs_change_stream(api_client, name, params, attach_curl_on_fail):
    """
    Tests the /cycleLogs/change-stream endpoint.
    Verifies that the change stream connection can be established (200 OK).
    Does NOT validate response content as the stream waits for real events.
    """
    with attach_curl_on_fail(ENDPOINT, params, method="GET"):
        # Короткий timeout только на установку соединения
        response = api_client.get(
            ENDPOINT, 
            params=params, 
            stream=True, 
            timeout=(5, 0.5)  # (connect timeout, read timeout)
        )
        
        try:
            # Единственное что проверяем - соединение установлено
            assert response.status_code == 200, \
                f"Expected 200, got {response.status_code}"
            
            # НЕ читаем данные - их может не быть без реальных событий
            print(f"Change stream connection established successfully")
            
        finally:
            response.close()