import pytest
import json
import os

@pytest.fixture(autouse=True, scope="session")
def skip_if_software():
    creds_path = os.path.join(os.path.dirname(__file__), "..", "..", "creds.json")
    try:
        with open(creds_path, encoding="utf-8") as f:
            creds = json.load(f)
        if creds.get("type") == "software":
            pytest.skip("Тест не актуален для SW")
    except Exception:
        # Если не удалось прочитать файл - скипаем, чтобы не ломать запуск
        pytest.skip("Тесты во вкладке BOOST пропущены, так как не удалось прочитать файл creds.json")
