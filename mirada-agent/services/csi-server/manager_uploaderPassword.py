#!/usr/bin/env python3
"""
Service handler for POST /manager/uploaderPassword

Verification endpoint for uploader password system state.

Input: POST request without body

Behavior:
  1) Executes: sudo grep uploader /etc/shadow  
  2) Reads current password hash
  3) Validates hash format and structure
  4) Returns verification result
  
Returns:
  {"result": "OK"} if hash is valid and readable
  {"result": "ERROR", "message": "description"} if error or invalid hash

No side effects beyond reading system files. Uses subprocess.run with check=False only.
This endpoint is typically called after password changes to verify system consistency.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _extract_password_hash(shadow_line: str) -> Optional[str]:
    """Extract password hash from /etc/shadow line.
    
    Shadow line format: username:password_hash:last_change:min:max:warn:inactive:expire:reserved
    
    Args:
        shadow_line: Line from /etc/shadow containing uploader user info
        
    Returns:
        Password hash string or None if parsing failed
    """
    if not shadow_line or not shadow_line.strip():
        return None
    
    # Split by ':' and get the second field (password hash)
    parts = shadow_line.strip().split(':')
    if len(parts) < 2:
        logger.warning("Invalid shadow line format: %s", shadow_line)
        return None
    
    password_hash = parts[1]
    if not password_hash or password_hash in ('*', '!', '!!'):
        logger.warning("Invalid or locked password hash: %s", password_hash)
        return None
    
    return password_hash


def _get_uploader_hash() -> Optional[str]:
    """Get current uploader password hash from /etc/shadow.
    
    Returns:
        Password hash string or None if command failed or user not found
    """
    try:
        cmd = ["sudo", "grep", "uploader", "/etc/shadow"]
        logger.info("Executing command: %s", " ".join(cmd))
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.warning("Command failed: rc=%d, stderr=%s", result.returncode, result.stderr)
            return None
        
        stdout = result.stdout.strip()
        if not stdout:
            logger.warning("No uploader entry found in /etc/shadow")
            return None
        
        # Handle multiple lines (should not happen, but be safe)
        lines = stdout.split('\n')
        uploader_line = lines[0]  # Take first line
        
        logger.info("Found uploader entry: %s", uploader_line[:50] + "..." if len(uploader_line) > 50 else uploader_line)
        
        return _extract_password_hash(uploader_line)
        
    except Exception as e:
        logger.error("Exception while getting uploader hash: %s", e)
        return None


def handle() -> Dict[str, str]:
    """Core handler logic for uploader password verification.
    
    Algorithm:
      This endpoint is called AFTER password change to verify it was successful:
      1) Execute: sudo grep uploader /etc/shadow
      2) Get current password hash
      3) Compare with expected changes (just verify we can read it)
      4) Return success - hash is readable and valid
    
    Note: This endpoint assumes password change already happened externally.
    We just verify the system state is consistent.
    
    Returns:
        Dict with keys {"result": "OK"} or {"result": "ERROR", "message": str}
    """
    logger.info("=== Starting uploader password verification ===")
    
    try:
        # Get current password hash to verify system state
        logger.info("Getting current uploader password hash")
        current_hash = _get_uploader_hash()
        
        if current_hash is None:
            return {"result": "ERROR", "message": "Failed to get uploader password hash from system"}
        
        logger.info("Hash obtained successfully (length: %d)", len(current_hash))
        
        # Verify the hash has valid format (starts with $ and contains expected patterns)
        if not current_hash.startswith('$'):
            logger.warning("Invalid hash format: does not start with $")
            return {"result": "ERROR", "message": "Invalid password hash format"}
        
        # Check for known hash types (md5, sha256, sha512, gost, etc.)
        hash_patterns = [
            r'^\$1\$',           # MD5
            r'^\$5\$',           # SHA-256
            r'^\$6\$',           # SHA-512
            r'^\$gost\d+\$',     # GOST variants like $gost12512$
            r'^\$gost\d+hash\$', # GOST variants like $gost12512hash$
        ]
        
        is_valid_format = any(re.match(pattern, current_hash) for pattern in hash_patterns)
        if not is_valid_format:
            logger.warning("Unknown hash format: %s", current_hash[:20])
            return {"result": "ERROR", "message": "Unknown password hash format"}
        
        logger.info("Password hash verification successful - valid hash format detected")
        return {"result": "OK"}
    
    except Exception as e:
        logger.error("Unexpected error during password verification: %s", e)
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


if __name__ == "__main__":
    # Test handler
    test_result = handle()
    print(f"Test result: {test_result}")