"""
Утилиты для работы с vswitch сервисами
"""

from .remove_interface_addr import (
    remove_interface_addr_handler,
    remove_all_interface_addresses,
    get_interface_addresses,
    check_interface_address_exists
)
from .delete_interface import delete_interface
from .revert_interface import revert_interface_changes
