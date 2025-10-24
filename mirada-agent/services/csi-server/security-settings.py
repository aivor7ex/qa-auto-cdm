#!/usr/bin/env python3
"""
Service handler for POST /security-settings

Deterministic verification by querying current auth settings from csi-server
container via a Node.js one-liner using @codemaster/bus, then comparing fields
provided in the request body.

Input JSON examples:
  {"max_bad_auth_attempts": 6, "bad_auth_decay_s": 333, "block_time_s": 666}
  {"max_bad_auth_attempts": 3}
  {"bad_auth_decay_s": 120}
  {"block_time_s": 900}
  {}

Behavior:
  1) Executes a safe docker exec command to read current values
  2) Parses JSON output: {bad_auth_decay_s, block_time_s, max_bad_auth_attempts}
  3) Compares only fields present in request payload
  4) Returns {result: "OK"} if all provided fields match, otherwise {result: "ERROR", message}

No side effects. Uses subprocess.run with check=False only.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import subprocess
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


def _build_node_script() -> str:
    """Return the Node.js script for querying auth settings via @codemaster/bus.

    Can be overridden by SECURITY_SETTINGS_NODE_SCRIPT env var.
    """
    override = os.environ.get("SECURITY_SETTINGS_NODE_SCRIPT")
    if override:
        return override
    # Default script is based on the specification in the task description
    return (
        "const Bus=require(\"@codemaster/bus\");"
        "const call=new Bus(process.env.BUS_SOCKET).rpc(\"configuration\",Bus.EMITTER,Bus.json_convert).call;"
        "(async()=>{try{const cur=await call({\"current-revision\":{domain:\"auth-settings\"}});"
        "const v=(await call({get:{revision:cur.id,path:\"\"}}))||{};"
        "const out={bad_auth_decay_s:Number(v.bad_auth_decay_s),block_time_s:Number(v.block_time_s),max_bad_auth_attempts:Number(v.max_bad_auth_attempts)};"
        "console.log(JSON.stringify(out,null,2));process.exit(0);}catch(e){console.error(String(e));process.exit(1);}})()"
    )


def _execute_query() -> subprocess.CompletedProcess:
    """Execute the docker+node command safely and return CompletedProcess.

    The container name and node binary are configurable via environment:
      - CSI_SERVER_CONTAINER (default: csi.csi-server)
      - NODE_BIN (default: node)
      - SECURITY_SETTINGS_QUERY_CMD (full command override)
    """
    # Full command override if provided
    override_cmd = os.environ.get("SECURITY_SETTINGS_QUERY_CMD")
    if override_cmd:
        cmd = override_cmd
        logger.info("Using override SECURITY_SETTINGS_QUERY_CMD")
        return subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, check=False)

    container = os.environ.get("CSI_SERVER_CONTAINER", "csi.csi-server")
    node_bin = os.environ.get("NODE_BIN", "node")
    script = _build_node_script()

    # Build a safe shell command; script goes inside single quotes for -e '...'
    # We quote container name to avoid injection; node -e body is a literal
    cmd = (
        f"docker exec -i {shlex.quote(container)} {shlex.quote(node_bin)} -e '" + script + "'"
    )
    logger.info("Executing security settings query: docker exec to %s", container)
    return subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, check=False)


def _parse_current_settings(stdout_text: str) -> Dict[str, int] | None:
    """Parse JSON from command stdout into a normalized dict with int values.

    - Tolerates noisy output by extracting the first JSON object substring
    - Does NOT require all expected keys to be present
    - Skips keys that are missing or non-integer-convertible
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

    out: Dict[str, int] = {}
    for key in ("bad_auth_decay_s", "block_time_s", "max_bad_auth_attempts"):
        if key in data:
            try:
                out[key] = int(data.get(key))
            except Exception:
                # Skip non-integer-convertible values rather than failing
                continue
    return out


def _validate_request(req: Dict[str, Any]) -> Dict[str, int] | str:
    """Validate and normalize the incoming request body.

    Returns dict of only provided keys with int values, or error message string.
    """
    if not isinstance(req, dict):
        return "Invalid request body"

    allowed = {"max_bad_auth_attempts", "bad_auth_decay_s", "block_time_s"}
    provided_keys = [k for k in req.keys() if k in allowed]
    normalized: Dict[str, int] = {}

    for key in provided_keys:
        val = req.get(key)
        if val is None:
            return f"Invalid value for {key}: null"
        try:
            ival = int(val)
        except Exception:
            return f"Invalid value for {key}: not an integer"
        normalized[key] = ival

    # No keys is allowed (trivially OK upon comparison)
    return normalized


def handle(request_body: Dict[str, Any]) -> Dict[str, Any]:
    """Core handler for security settings verification.

    Arguments:
        request_body: JSON dict with optional keys: max_bad_auth_attempts, bad_auth_decay_s, block_time_s

    Returns:
        {"result": "OK"} or {"result": "ERROR", "message": str}
    """
    # Validate request body
    vr = _validate_request(request_body)
    if isinstance(vr, str):
        return {"result": "ERROR", "message": vr}
    expected = vr  # dict of keys to verify

    try:
        proc = _execute_query()
    except Exception as e:
        logger.error("Failed to execute security settings query: %s", e)
        return {"result": "ERROR", "message": f"Execution failure: {e}"}

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        return {"result": "ERROR", "message": stderr or "Query command failed"}

    current = _parse_current_settings(proc.stdout or "")
    if current is None:
        # Provide stderr snippet for easier diagnostics but keep deterministic message
        return {"result": "ERROR", "message": "Invalid JSON from query"}

    # Compare only provided keys; empty expected means OK
    mismatches: List[str] = []
    for key, exp_val in expected.items():
        if key not in current:
            mismatches.append(f"{key}: expected {exp_val}, actual <missing>")
            continue
        cur_val = current.get(key)
        if cur_val != exp_val:
            mismatches.append(f"{key}: expected {exp_val}, actual {cur_val}")

    if mismatches:
        return {"result": "ERROR", "message": "; ".join(mismatches)}

    return {"result": "OK"}


if __name__ == "__main__":
    # Simple manual test
    print(handle({}))


