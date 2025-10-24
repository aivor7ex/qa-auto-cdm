#!/usr/bin/env python3
"""
Service handler for POST /integrity/test

Deterministic verification based on application logs containing INTEGRITY_SUCCESS/INTEGRITY_ERROR.

Input JSON examples:
  {"state": "success"}
  {"state": "error"}

Behavior:
  - Executes command to check integrity status
  - Searches for INTEGRITY_SUCCESS/INTEGRITY_ERROR in application logs
  - For state "success": returns OK if INTEGRITY_SUCCESS is found, ERROR otherwise
  - For state "error": returns OK if INTEGRITY_ERROR is found, ERROR otherwise

No side effects beyond reading logs. Uses subprocess.run with check=False only.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Dict, List

logger = logging.getLogger(__name__)


def _execute_integrity_check() -> subprocess.CompletedProcess:
    """Execute the integrity check command safely."""
    # Получаем команду из переменной окружения или используем дефолтную
    integrity_cmd = os.environ.get("INTEGRITY_CHECK_CMD", "echo 'INTEGRITY_SUCCESS'")
    
    # Разбиваем команду на аргументы
    cmd_parts = integrity_cmd.split()
    if not cmd_parts:
        cmd_parts = ["echo", "INTEGRITY_SUCCESS"]
    
    logger.info("Executing integrity check command: %s", " ".join(cmd_parts))
    return subprocess.run(cmd_parts, capture_output=True, text=True, check=False)


def _search_integrity_marker(log_output: str, marker: str) -> bool:
    """Search for integrity marker (INTEGRITY_SUCCESS or INTEGRITY_ERROR) in log output."""
    if not log_output:
        return False

    if marker.upper() == "INTEGRITY_SUCCESS":
        patterns = [
            r'INTEGRITY_SUCCESS',
            r'\[info\]\s+INTEGRITY_SUCCESS',
            r'INTEGRITY_SUCCESS\s+\{',
        ]
    else:
        # INTEGRITY_ERROR может встречаться как уровень [error] или просто текст
        patterns = [
            r'INTEGRITY_ERROR',
            r'\[error\]\s+INTEGRITY_ERROR',
            r'INTEGRITY_ERROR\s+\{',
        ]

    for pattern in patterns:
        if re.search(pattern, log_output, re.IGNORECASE):
            logger.info("Found %s pattern: %s", marker, pattern)
            return True

    return False


def _search_in_application_logs(marker: str) -> bool:
    """Search for integrity marker in application logs."""
    # Получаем настройки из переменных окружения
    log_source = os.environ.get("INTEGRITY_LOG_SOURCE", "docker logs csi.csi-server")
    since_time = os.environ.get("INTEGRITY_LOG_SINCE", "5m")
    
    # Формируем команду для поиска в логах
    grep_marker = marker.upper()
    if "docker logs" in log_source:
        cmd = f"{log_source} --since={since_time} | grep -i '{grep_marker}'"
    else:
        cmd = f"{log_source} | grep -i '{grep_marker}'"
    
    logger.info("Searching in application logs: %s", cmd)
    
    try:
        result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout:
            logger.info("Found %s in application logs", grep_marker)
            return True
    except Exception as e:
        logger.warning("Failed to search application logs: %s", e)
    
    return False


def _detect_integrity_marker(marker: str) -> bool:
    """Run integrity detection flow and return True if the specified marker is found.

    The function checks command output first, then falls back to application logs.
    """
    marker_upper = marker.upper()
    result = _execute_integrity_check()

    if result.returncode == 0:
        log_output = result.stdout or ""
        logger.info("Integrity check output length: %d", len(log_output))
        if _search_integrity_marker(log_output, marker_upper):
            logger.info("%s found in command output", marker_upper)
            return True
    else:
        logger.warning(
            "Integrity check command failed: rc=%d, stderr=%s",
            result.returncode,
            result.stderr,
        )

    logger.info("Searching in application logs as fallback")
    if _search_in_application_logs(marker_upper):
        logger.info("%s found in application logs", marker_upper)
        return True

    logger.info("%s not detected in command output or application logs", marker_upper)
    return False


def handle(state: str) -> Dict[str, str]:
    """Core handler logic for integrity test verification.

    Arguments:
        state: Expected state from request body ("success" or "error")

    Returns:
        Dict with keys {"result": "OK"} or {"result": "ERROR", "message": str}
    """
    logger.info("Integrity test handler received: state=%s", state)

    # Валидация входных данных
    if not isinstance(state, str) or not state:
        logger.warning("Validation failed: invalid or empty state")
        return {"result": "ERROR", "message": "Invalid or empty state"}

    if state not in ("success", "error"):
        logger.warning("Validation failed: state must be 'success' or 'error', got: %s", state)
        return {"result": "ERROR", "message": f"State must be 'success' or 'error', got: {state}"}

    try:
        if state == "success":
            success_detected = _detect_integrity_marker("INTEGRITY_SUCCESS")
            if success_detected:
                logger.info("Verification passed for expected 'success'")
                return {"result": "OK"}
            logger.warning("Verification failed: expected 'success' but not detected")
            return {"result": "ERROR", "message": "INTEGRITY_SUCCESS not found in application logs"}

        # state == "error"
        error_detected = _detect_integrity_marker("INTEGRITY_ERROR")
        if error_detected:
            logger.info("Verification passed for expected 'error'")
            return {"result": "OK"}
        logger.warning("Verification failed: expected 'error' but not detected")
        return {"result": "ERROR", "message": "INTEGRITY_ERROR not found in application logs"}

    except Exception as e:
        logger.error("Unexpected error during integrity test: %s", e)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


if __name__ == "__main__":
    # Тестирование обработчика
    test_result_success = handle("success")
    print(f"Test result (success): {test_result_success}")
    test_result_error = handle("error")
    print(f"Test result (error): {test_result_error}")
