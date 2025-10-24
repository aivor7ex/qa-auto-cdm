import pytest
from UI.conftest import CURRENT_CLUSTER_STATE
from pathlib import Path

def pytest_collection_modifyitems(config, items):
    if CURRENT_CLUSTER_STATE == "slave":
        # Пропускаем все тесты в директории firewall, если кластер находится в режиме slave
        for item in items:
            path = Path(str(item.fspath))
            if "firewall" in path.parts:
                item.add_marker(pytest.mark.skip(reason="Тесты вкладки Межсетевое экранирование пропускаются в режиме Slave.")) 