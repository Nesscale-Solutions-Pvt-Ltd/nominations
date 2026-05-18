"""MSG91 OTP integration + hashing helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

import frappe
import requests


def _settings():
	return frappe.get_cached_doc("Nominations Settings")


def generate_otp(length: int | None = None) -> str:
	length = int(length or _settings().otp_length or 6)
	n = secrets.randbelow(10 ** length)
	return str(n).zfill(length)


def _site_salt() -> str:
	salt = _settings().get_password("site_salt", raise_exception=False)
	if not salt:
		# Generate and persist a salt the first time it's needed.
		salt = secrets.token_hex(32)
		doc = frappe.get_doc("Nominations Settings")
		doc.site_salt = salt
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	return salt


def hash_otp(otp: str, phone: str) -> str:
	return hashlib.sha256((otp + phone + _site_salt()).encode()).hexdigest()


def hash_phone(phone: str) -> str:
	return hashlib.sha256((phone + _site_salt()).encode()).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
	return hmac.compare_digest(a or "", b or "")


def mask_phone(phone: str) -> str:
	if not phone or len(phone) < 6:
		return phone or ""
	return phone[:5] + "****" + phone[-3:]


def send_otp_sms(phone_e164: str, otp: str) -> dict:
	"""Send the OTP via MSG91. Retries once on 5xx."""
	settings = _settings()
	auth_key = settings.get_password("msg91_auth_key", raise_exception=False)
	if not auth_key or not settings.msg91_template_id:
		frappe.log_error(
			"MSG91 credentials missing in Nominations Settings",
			"MSG91 send_otp_sms",
		)
		frappe.throw(
			"SMS provider is not configured. "
			"Set MSG91 Auth Key and Template ID in Nominations Settings, "
			"or disable 'Require OTP Verification'."
		)
	url = "https://control.msg91.com/api/v5/otp"
	params = {
		"template_id": settings.msg91_template_id,
		"mobile": phone_e164.lstrip("+"),
		"authkey": auth_key,
		"otp": otp,
		"otp_expiry": max(1, int((settings.otp_ttl_seconds or 600) / 60)),
	}

	for attempt in range(2):
		try:
			r = requests.post(url, params=params, timeout=10)
			if r.status_code >= 500:
				if attempt == 0:
					time.sleep(2)
					continue
				r.raise_for_status()
			r.raise_for_status()
			data = r.json()
			if data.get("type") != "success":
				frappe.log_error(
					f"MSG91 error for {mask_phone(phone_e164)}: {data}",
					"MSG91 send_otp_sms",
				)
				frappe.throw("Could not send verification SMS. Please try again.")
			return data
		except requests.RequestException as e:
			if attempt == 0:
				time.sleep(2)
				continue
			frappe.log_error(
				f"MSG91 request failed for {mask_phone(phone_e164)}: {e}",
				"MSG91 send_otp_sms",
			)
			frappe.throw("SMS provider is unreachable. Please try again shortly.")
	return {}
