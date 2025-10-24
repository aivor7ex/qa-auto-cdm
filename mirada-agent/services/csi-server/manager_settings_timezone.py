#!/usr/bin/env python3
"""
Service handler for POST /manager/settings/timezone

Deterministic verification by querying current timezone settings from csi-server
container via a Node.js one-liner using @codemaster/bus, then comparing with
the provided timezone value in the request body.

Input JSON example:
  {"data": "timezone_value"}

Behavior:
  1) Executes a safe docker exec command to read current timezone value
  2) Parses JSON output: {"timezone": "timezone_value"}
  3) Compares request data with the timezone value from the query
  4) Returns {result: "OK"} if they match, otherwise {result: "ERROR", message}

No side effects. Uses subprocess.run with check=False only.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


def _build_node_script() -> str:
    """Return the Node.js script for querying timezone settings via @codemaster/bus.

    Can be overridden by TIMEZONE_SETTINGS_NODE_SCRIPT env var.
    """
    override = os.environ.get("TIMEZONE_SETTINGS_NODE_SCRIPT")
    if override:
        return override
    # Default script based on the specification in the task description
    return (
        "const Bus=require('@codemaster/bus');"
        "const call=new Bus(process.env.BUS_SOCKET).rpc('configuration',Bus.EMITTER,Bus.json_convert).call;"
        "(async()=>{try{const cur=await call({'current-revision':{domain:'host-settings'}});"
        "const v=(await call({get:{revision:cur.id,path:''}}))||{};"
        "console.log(JSON.stringify(v,null,2));process.exit(0);}catch(e){console.error('Error:',String(e));process.exit(1);}})()"
    )


def _execute_query() -> subprocess.CompletedProcess:
    """Execute the docker+node command safely and return CompletedProcess.

    The container name and node binary are configurable via environment:
      - CSI_SERVER_CONTAINER (default: csi.csi-server)
      - NODE_BIN (default: node)
      - TIMEZONE_SETTINGS_QUERY_CMD (full command override)
    """
    # Full command override if provided
    override_cmd = os.environ.get("TIMEZONE_SETTINGS_QUERY_CMD")
    if override_cmd:
        cmd = override_cmd
        logger.info("Using override TIMEZONE_SETTINGS_QUERY_CMD")
        return subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, check=False)

    container = os.environ.get("CSI_SERVER_CONTAINER", "csi.csi-server")
    node_bin = os.environ.get("NODE_BIN", "node")
    script = _build_node_script()

    # Build a safe shell command; use double quotes to avoid escaping issues
    # We quote container name to avoid injection; node -e body is a literal
    cmd = [
        "docker", "exec", "-i", container, node_bin, "-e", script
    ]
    logger.info("Executing timezone settings query: docker exec to %s", container)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _parse_current_timezone(stdout_text: str) -> Optional[str]:
    """Parse JSON from command stdout to extract timezone value.

    - Tolerates noisy output by extracting the first JSON object substring
    - Returns the timezone value if found, None otherwise
    """
    text = stdout_text or ""
    # Try direct parse first
    data: Any | None = None
    try:
        data = json.loads(text)
    except Exception:
        # Fallback: extract JSON object from noisy text
        import re as _re
        m = _re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                data = None
    
    if not isinstance(data, dict):
        return None
    
    timezone = data.get("timezone")
    if isinstance(timezone, str):
        return timezone
    
    return None


def _validate_request(req: Dict[str, Any]) -> str | None:
    """Validate the incoming request body.

    Returns the timezone value if valid, or error message string.
    """
    if not isinstance(req, dict):
        return "Invalid request body"

    data = req.get("data")
    if not isinstance(data, str) or not data.strip():
        return "Invalid or missing 'data' field - must be a non-empty string"

    return data.strip()


def handle(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Core handler for timezone settings verification.

    Arguments:
        request_body: JSON dict with "data" field containing timezone string

    Returns:
        {"result": "OK"} or {"result": "ERROR", "message": str}
    """
    # Validate request body
    expected_timezone = _validate_request(request_body)
    if isinstance(expected_timezone, str) and expected_timezone.startswith("Invalid"):
        return {"result": "ERROR", "message": expected_timezone}

    try:
        proc = _execute_query()
    except Exception as e:
        logger.error("Failed to execute timezone settings query: %s", e)
        return {"result": "ERROR", "message": f"Execution failure: {e}"}

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        return {"result": "ERROR", "message": stderr or "Query command failed"}

    current_timezone = _parse_current_timezone(proc.stdout or "")
    if current_timezone is None:
        return {"result": "ERROR", "message": "Invalid JSON from query or timezone not found"}

    # Compare timezone values
    if current_timezone != expected_timezone:
        return {
            "result": "ERROR", 
            "message": f"Timezone mismatch: expected '{expected_timezone}', actual '{current_timezone}'"
        }

    return {"result": "OK"}


if __name__ == "__main__":
    # Simple manual test
    print(handle({"data": "timezone_value"}))
