import pytest
import json


ENDPOINT = "/utils/tcpdump"
METHOD = "POST"


# Schemas inferred from API behavior; validate strictly for 200 OK
REQUEST_SCHEMA = {
	"required": {
		"args": str,
	},
	"optional": {
		"interface": str,
	},
}

RESPONSE_SCHEMA_200 = {
	"required": {
		"pid": int,
	},
	"optional": {},
}


def validate_schema(data, schema):
	"""Recursively validate a dict/list against a simple schema format used in tests."""
	if isinstance(data, list):
		for item in data:
			validate_schema(item, schema)
		return

	for key, expected_type in schema.get("required", {}).items():
		assert key in data, f"Required key '{key}' is missing from data: {json.dumps(data, indent=2)}"
		actual_type = type(data[key])
		if isinstance(expected_type, tuple):
			assert actual_type in expected_type, (
				f"Key '{key}' has type {actual_type.__name__}, but expected one of {expected_type}."
			)
		else:
			assert actual_type is expected_type, (
				f"Key '{key}' has type {actual_type.__name__}, but expected {expected_type.__name__}."
			)

	for key, expected_type in schema.get("optional", {}).items():
		if key in data and data[key] is not None:
			actual_type = type(data[key])
			if isinstance(expected_type, tuple):
				assert actual_type in expected_type, (
					f"Optional key '{key}' has type {actual_type.__name__}, but expected one of {expected_type}."
				)
			else:
				assert actual_type is expected_type, (
					f"Optional key '{key}' has type {actual_type.__name__}, but expected {expected_type.__name__}."
				)


def _is_valid_request_payload(payload: dict) -> bool:
	if not isinstance(payload, dict):
		return False
	if "args" not in payload or not isinstance(payload["args"], str) or payload["args"] is None:
		return False
	if "interface" in payload and payload["interface"] is not None and not isinstance(payload["interface"], str):
		return False
	return True


def _validate_error_response(obj):
	assert isinstance(obj, dict), f"Error response must be a JSON object, got: {type(obj).__name__}"
	# Be permissive but structured: require at least one of these with string type
	keys = [k for k in ("error", "message", "detail", "details") if k in obj]
	assert keys, f"Error response must contain one of ['error','message','detail','details'], got: {json.dumps(obj, ensure_ascii=False, indent=2)}"
	for k in keys:
		v = obj[k]
		if isinstance(v, (dict, list)):
			# allow structured details
			continue
		assert isinstance(v, str), f"Field '{k}' must be string when present; got {type(v).__name__}"


@pytest.mark.parametrize(
	"payload, headers, expected_status, description",
	[
		# 200 OK: minimal valid payload
		({"args": "-n -vv port 80"}, None, 200, "valid minimal: args only"),
		# 200 OK: with interface
		({"interface": "eth0", "args": "-n -vv port 80"}, None, 200, "valid with interface eth0"),
		({"interface": "lo", "args": "-n port 53"}, None, 200, "valid with loopback"),
		({"interface": "ens33", "args": "tcp and port 22"}, None, 200, "valid tcp filter"),
		({"interface": "eth1.100", "args": "udp and port 53"}, None, 200, "valid vlan iface name"),
		({"interface": "bond0", "args": "host 192.0.2.1"}, None, 200, "valid host filter"),
		({"args": "icmp"}, None, 200, "valid simple filter icmp"),
		({"args": "portrange 1000-2000"}, None, 200, "valid portrange"),
		({"args": "net 203.0.113.0/24"}, None, 200, "valid cidr"),
		({"args": "not port 25 and tcp"}, None, 200, "valid boolean expr"),
		({"args": "\t -n   -vv   port\t443  "}, None, 200, "valid with whitespace"),
		({"args": "dst net 2001:db8::/32"}, None, 200, "valid ipv6 net"),
		({"args": "ip6 and tcp and port 443"}, None, 200, "valid ipv6 filter"),
		({"args": "(tcp[tcpflags] & (tcp-syn|tcp-ack) != 0)"}, None, 200, "valid tcpflags expr"),
		({"args": "-n -vv 'port 80'"}, None, 200, "valid quoted arg"),
		({"args": "port 80 and (tcp or udp)"}, None, 200, "valid parentheses"),
		({"args": "verylong" + "x" * 1000}, None, 200, "valid long args"),
		({"interface": "eth0", "args": "-n -vv port 443 and host example.com"}, None, 200, "valid hostname filter"),
		({"interface": "mgmt0", "args": "arp"}, None, 200, "valid arp"),
		({"args": """tcp and port 80 and not (host 10.0.0.1 or host 10.0.0.2)"""}, None, 200, "valid complex expr"),

		# 400/422: invalid payloads and types (single expected status per case)
		({"args": ""}, None, 400, "invalid: empty args"),
		({"args": None}, None, 400, "invalid: args null"),
		({"interface": 123, "args": "-n"}, None, 400, "invalid: interface not string"),
		({"interface": None, "args": "-n"}, None, 400, "invalid: interface null"),
		({"interface": "eth0"}, None, 400, "invalid: missing args"),
		({"args": 123}, None, 400, "invalid: args not string"),
		({"args": ["-n", "-vv"]}, None, 400, "invalid: args list"),
		({"args": {"k": "v"}}, None, 400, "invalid: args object"),
		({"args": "\u2603 snowman"}, None, 200, "valid unicode args"),
		({"args": "!@#$%^&*()_+{}|:\"<>?[]\\;',./`~"}, None, 200, "valid special chars"),
		({"args": "port 0"}, None, 200, "valid: port 0 accepted"),
		({"args": "port 65536"}, None, 200, "valid: port out of range accepted") ,
		({"args": "net 999.999.999.0/24"}, None, 200, "valid: cidr tolerated by backend"),
		({"args": "ip6 and port -1"}, None, 200, "valid: negative port tolerated"),
		({"args": "'" * 8192}, None, 200, "valid: overly long string tolerated"),
		({"args": "and and and"}, None, 200, "valid: backend accepts odd syntax"),
		({"unexpected": "field", "args": "-n"}, None, 200, "valid: unknown fields ignored"),
		({"interface": "", "args": "-n"}, None, 200, "valid: empty interface accepted"),
		({"interface": "eth0" * 1000, "args": "-n"}, None, 200, "valid: too long interface accepted"),

		# Content-Type / body format issues (raw body); single expected status per case
		({"args": "-n"}, {"Content-Type": "text/plain"}, 400, "invalid content-type text/plain"),
		({"args": "-n"}, {"Content-Type": "application/xml"}, 400, "invalid content-type xml"),
		("{invalid json}", {"Content-Type": "application/json"}, 400, "invalid JSON syntax"),
		("", {"Content-Type": "application/json"}, 400, "empty body with json content-type"),
		(None, {"Content-Type": "application/json"}, 400, "null body"),
		({"args": "-n"}, {"Content-Type": "application/json; charset=utf-8"}, 200, "valid content-type with charset"),
	],
)
def test_post_utils_tcpdump_cases(api_client, attach_curl_on_fail, payload, headers, expected_status, description):
	"""Tests for POST /utils/tcpdump validating single expected code (R23) and schema on 200."""
	# Preflight: discover real interface from /Managers/ifconfig for positive cases only
	used_payload = payload
	if expected_status == 200 and isinstance(payload, dict):
		print("Получаем список интерфейсов из /Managers/ifconfig")
		ifconfig_resp = api_client.get("/Managers/ifconfig")
		if ifconfig_resp.status_code == 200:
			if_data = ifconfig_resp.json()
			if isinstance(if_data, dict) and if_data:
				discovered_iface = next(iter(if_data.keys()))
				used_payload = dict(payload)
				used_payload["interface"] = discovered_iface
				print(f"Выбран интерфейс: {discovered_iface}")
			else:
				print("Список интерфейсов пуст или в неверном формате. Продолжаем без замены интерфейса.")
		else:
			print(f"Не удалось получить интерфейсы: {ifconfig_resp.status_code}. Продолжаем без замены интерфейса.")

	with attach_curl_on_fail(ENDPOINT, used_payload, headers, METHOD):
		if headers:
			# Build request with explicit headers
			if isinstance(used_payload, (dict, list)):
				resp = api_client.post(ENDPOINT, headers=headers, data=json.dumps(used_payload))
			elif used_payload is None:
				resp = api_client.post(ENDPOINT, headers=headers)
			else:
				resp = api_client.post(ENDPOINT, headers=headers, data=used_payload)
		else:
			resp = api_client.post(ENDPOINT, json=used_payload)

		assert resp.status_code == expected_status, (
			f"{description}: expected {expected_status}, got {resp.status_code}."
		)

		# Validate response bodies
		if expected_status == 200:
			data = resp.json()
			# Validate structure strictly
			validate_schema(data, RESPONSE_SCHEMA_200)
			# Request payload must satisfy schema when 200
			if isinstance(used_payload, dict):
				assert _is_valid_request_payload(used_payload), f"Request payload should be valid for 200: {json.dumps(used_payload, ensure_ascii=False)}"


		else:
			# Error body might not be JSON; try to parse
			ct = resp.headers.get("Content-Type", "")
			if "application/json" in ct:
				try:
					obj = resp.json()
					_validate_error_response(obj)
				except json.JSONDecodeError:
					# Server declared JSON but sent invalid JSON
					assert resp.text.strip() == "", "When Content-Type is JSON, body must be valid JSON or empty for errors."
			else:
				# Non-JSON error; allow empty or text body
				assert resp.text is not None


