#!/usr/bin/env python3
"""
Service handler for POST /manager/config

Deterministic verification of configuration import completion by checking:
1. Presence of /tmp/miradaexport/config.bkp file in csi.csi-server container
2. Configuration restore log in /app/ctld-logs/configuration-restore

Input: POST request without body (import signal)

Behavior:
1. Check if config.bkp file exists in container
2. Check configuration-restore log for import completion
3. Return {"result": "OK"} if both checks pass, otherwise {"result": "ERROR", "message": "..."}

No side effects. Uses subprocess.run with check=False only.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _check_config_file_exists() -> bool:
    """Check if config.bkp file exists in csi.csi-server container by copying it to host.
    
    Returns:
        True if file exists and can be copied, False otherwise
    """
    container = os.environ.get("CSI_SERVER_CONTAINER", "csi.csi-server")
    config_path = os.environ.get("CONFIG_BACKUP_PATH", "/tmp/miradaexport/config.bkp")
    
    # Создаем временный файл на хосте
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"config_check_{os.getpid()}.bkp")
    
    cmd = ["docker", "cp", f"{container}:{config_path}", temp_path]
    logger.info("Copying config file to check existence: %s", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info("Config file %s successfully copied from container %s", config_path, container)
            # Проверяем, что файл действительно скопировался
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                logger.info("Temporary config file exists on host: %s, size: %d bytes", temp_path, file_size)
                file_exists = file_size > 0
                if not file_exists:
                    logger.warning("Config file copied but has zero size")
            else:
                logger.warning("Config file copied but temporary file doesn't exist on host: %s", temp_path)
                file_exists = False
            return file_exists
        else:
            logger.warning("Config file %s not found in container %s: %s", config_path, container, result.stderr)
            return False
    except Exception as e:
        logger.error("Failed to copy config file: %s", e)
        return False
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug("Temporary file %s removed", temp_path)
        except Exception as e:
            logger.warning("Failed to remove temporary file %s: %s", temp_path, e)


def _check_config_file_size() -> int:
    """Get size of config.bkp file in bytes by copying it to host.
    
    Returns:
        File size in bytes, or -1 if error
    """
    container = os.environ.get("CSI_SERVER_CONTAINER", "csi.csi-server")
    config_path = os.environ.get("CONFIG_BACKUP_PATH", "/tmp/miradaexport/config.bkp")
    
    # Создаем временный файл на хосте
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"config_size_{os.getpid()}.bkp")
    
    cmd = ["docker", "cp", f"{container}:{config_path}", temp_path]
    logger.info("Copying config file to check size: %s", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            # Получаем размер скопированного файла
            file_size = -1
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                logger.info("Config file size: %d bytes", file_size)
            else:
                logger.warning("Config file was copied but doesn't exist on host")
            
            return file_size
        else:
            logger.warning("Failed to copy config file for size check: %s", result.stderr)
            return -1
    except Exception as e:
        logger.error("Error copying config file for size check: %s", e)
        return -1
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug("Temporary file %s removed", temp_path)
        except Exception as e:
            logger.warning("Failed to remove temporary file %s: %s", temp_path, e)


def _check_restore_log_exists() -> bool:
    """Check if configuration-restore log exists in csi.csi-server container by copying it.
    
    Returns:
        True if log exists and can be copied, False otherwise
    """
    container = os.environ.get("CSI_SERVER_CONTAINER", "csi.csi-server")
    log_path = os.environ.get("CONFIG_RESTORE_LOG_PATH", "/app/ctld-logs/configuration-restore")
    
    # Создаем временный файл на хосте
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"restore_log_check_{os.getpid()}.log")
    
    cmd = ["docker", "cp", f"{container}:{log_path}", temp_path]
    logger.info("Copying restore log to check existence: %s", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info("Restore log %s successfully copied from container %s", log_path, container)
            # Проверяем, что файл действительно скопировался
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                logger.info("Temporary restore log exists on host: %s, size: %d bytes", temp_path, file_size)
                log_exists = True
            else:
                logger.warning("Restore log copied but temporary file doesn't exist on host: %s", temp_path)
                log_exists = False
            return log_exists
        else:
            logger.warning("Restore log %s not found in container %s: %s", log_path, container, result.stderr)
            return False
    except Exception as e:
        logger.error("Failed to copy restore log: %s", e)
        return False
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug("Temporary file %s removed", temp_path)
        except Exception as e:
            logger.warning("Failed to remove temporary file %s: %s", temp_path, e)


def _analyze_restore_log() -> Dict[str, Any]:
    """Analyze configuration-restore log for import completion markers by copying it to host.
    
    Returns:
        Dict with analysis results: {"success": bool, "messages": list, "error": str}
    """
    container = os.environ.get("CSI_SERVER_CONTAINER", "csi.csi-server")
    log_path = os.environ.get("CONFIG_RESTORE_LOG_PATH", "/app/ctld-logs/configuration-restore")
    
    # Создаем временный файл на хосте
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"restore_log_analysis_{os.getpid()}.log")
    
    cmd = ["docker", "cp", f"{container}:{log_path}", temp_path]
    logger.info("Copying restore log for analysis: %s", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("Failed to copy restore log: %s", result.stderr)
            return {"success": False, "messages": [], "error": "Failed to copy restore log"}
        
        # Читаем скопированный файл
        if not os.path.exists(temp_path):
            logger.error("Copied restore log file doesn't exist on host")
            return {"success": False, "messages": [], "error": "Copied restore log file not found"}
        
        analysis_result = {"success": False, "messages": [], "error": None}
        
        try:
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
            
            lines = log_content.split('\n')
            
            # Ищем признаки успешного импорта
            success_patterns = [
                "done dumping",
                "writing",
                "archive on stdout"
            ]
            
            error_patterns = [
                "error",
                "failed",
                "exception"
            ]
            
            success_count = 0
            error_count = 0
            messages = []
            
            for line in lines:
                line_lower = line.lower()
                
                # Проверяем на ошибки
                for error_pattern in error_patterns:
                    if error_pattern in line_lower:
                        error_count += 1
                        messages.append(f"Error found: {line.strip()}")
                        break
                
                # Проверяем на успешные операции
                for success_pattern in success_patterns:
                    if success_pattern in line_lower:
                        success_count += 1
                        break
            
            logger.info("Restore log analysis: success_count=%d, error_count=%d", success_count, error_count)
            
            # Считаем импорт успешным если есть успешные операции и нет критических ошибок
            is_success = success_count > 0 and error_count == 0
            
            analysis_result = {
                "success": is_success,
                "messages": messages,
                "error": None,
                "success_count": success_count,
                "error_count": error_count
            }
            
        except Exception as e:
            logger.error("Error reading restore log file: %s", e)
            analysis_result = {"success": False, "messages": [], "error": f"File reading error: {str(e)}"}
        
        return analysis_result
        
    except Exception as e:
        logger.error("Error analyzing restore log: %s", e)
        return {"success": False, "messages": [], "error": f"Analysis error: {str(e)}"}
    finally:
        # Удаляем временный файл
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug("Temporary file %s removed", temp_path)
        except Exception as e:
            logger.warning("Failed to remove temporary file %s: %s", temp_path, e)


def handle() -> Dict[str, Any]:
    """Core handler for manager/config endpoint.
    
    Verifies that configuration import has completed successfully by checking:
    1. Config backup file exists
    2. Restore log exists and indicates successful import
    
    Returns:
        {"result": "OK"} or {"result": "ERROR", "message": str}
    """
    logger.info("=== MANAGER CONFIG VERIFICATION STARTED ===")
    
    errors = []
    
    # 1. Проверяем наличие файла конфигурации
    config_exists = _check_config_file_exists()
    if not config_exists:
        errors.append("Config backup file not found")
    else:
        # Проверяем размер файла
        file_size = _check_config_file_size()
        if file_size <= 0:
            errors.append("Config backup file is empty or inaccessible")
        else:
            logger.info("Config backup file verified: %d bytes", file_size)
    
    # 2. Проверяем наличие лога восстановления
    log_exists = _check_restore_log_exists()
    if not log_exists:
        errors.append("Configuration restore log not found")
    else:
        # Анализируем содержимое лога
        log_analysis = _analyze_restore_log()
        if not log_analysis["success"]:
            if log_analysis["error"]:
                errors.append(f"Restore log analysis failed: {log_analysis['error']}")
            else:
                errors.append("Configuration restore log indicates import failure")
                if log_analysis["messages"]:
                    errors.extend(log_analysis["messages"])
        else:
            logger.info("Configuration restore log verified: %d successful operations", 
                       log_analysis.get("success_count", 0))
    
    # Формируем результат
    if errors:
        error_message = "; ".join(errors)
        logger.error("Manager config verification failed: %s", error_message)
        result = {"result": "ERROR", "message": error_message}
    else:
        logger.info("Manager config verification completed successfully")
        result = {"result": "OK"}
    
    return result


if __name__ == "__main__":
    # Простой тест обработчика
    result = handle()
    print(f"Test result: {result}")