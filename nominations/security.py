"""Signed verification tokens (JSON over itsdangerous-style HMAC)."""
from __future__ import annotations

import base64
import hmac
import json
import time
from hashlib import sha256

import frappe

from nominations.msg91 import _site_salt

TOKEN_PREFIX = "v1."


def _sign(payload_b64: str) -> str:
	key = _site_salt().encode()
	sig = hmac.new(key, payload_b64.encode(), sha256).digest()
	return base64.urlsafe_b64encode(sig).rstrip(b"=").decode()


def issue_token(payload: dict, ttl_seconds: int = 300) -> str:
	body = dict(payload)
	body["exp"] = int(time.time()) + ttl_seconds
	payload_b64 = (
		base64.urlsafe_b64encode(json.dumps(body, separators=(",", ":")).encode())
		.rstrip(b"=")
		.decode()
	)
	sig = _sign(payload_b64)
	return f"{TOKEN_PREFIX}{payload_b64}.{sig}"


def verify_token(token: str) -> dict:
	if not token or not token.startswith(TOKEN_PREFIX):
		frappe.throw("Invalid verification token.")
	try:
		payload_b64, sig = token[len(TOKEN_PREFIX):].rsplit(".", 1)
	except ValueError:
		frappe.throw("Invalid verification token.")
	expected = _sign(payload_b64)
	if not hmac.compare_digest(expected, sig):
		frappe.throw("Invalid verification token.")
	padding = "=" * (-len(payload_b64) % 4)
	try:
		body = json.loads(base64.urlsafe_b64decode(payload_b64 + padding).decode())
	except Exception:
		frappe.throw("Invalid verification token.")
	if int(body.get("exp", 0)) < int(time.time()):
		frappe.throw("Verification token has expired. Please request a new code.")
	return body
