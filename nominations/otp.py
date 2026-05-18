"""Channel-agnostic OTP helpers used by ``nominations.api``.

This module is the single seam between the public API and the underlying
OTP delivery providers (MSG91 SMS, frappe_whatsapp). The API layer must
not import any provider-specific module directly.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

import frappe


def _settings():
	return frappe.get_cached_doc("Nominations Settings")


# ---------------------------------------------------------------------------
# Generation + hashing
# ---------------------------------------------------------------------------

def generate_otp(length: int | None = None) -> str:
	length = int(length or _settings().otp_length or 6)
	n = secrets.randbelow(10 ** length)
	return str(n).zfill(length)


def _site_salt() -> str:
	settings = _settings()
	salt = settings.get_password("site_salt", raise_exception=False)
	if not salt:
		# Generate and persist once. Use a fresh, non-cached doc so we don't
		# stomp on a concurrently-mutated cached copy.
		doc = frappe.get_doc("Nominations Settings")
		salt = secrets.token_hex(32)
		doc.site_salt = salt
		doc.save(ignore_permissions=True)
	return salt


def hash_phone(phone: str) -> str:
	return hashlib.sha256((phone + _site_salt()).encode()).hexdigest()


def constant_time_eq(a: str, b: str) -> bool:
	return hmac.compare_digest(a or "", b or "")


def mask_phone(phone: str) -> str:
	if not phone or len(phone) < 6:
		return phone or ""
	return phone[:5] + "****" + phone[-3:]


# ---------------------------------------------------------------------------
# Delivery dispatcher
# ---------------------------------------------------------------------------

def send_otp(phone_e164: str, otp: str) -> dict:
	"""Send ``otp`` to ``phone_e164`` using the channel configured in
	Nominations Settings (SMS via MSG91, or WhatsApp via frappe_whatsapp)."""
	channel = (_settings().get("otp_channel") or "SMS").strip().lower()
	if channel == "whatsapp":
		from nominations import whatsapp as _wa

		return _wa.send_otp_whatsapp(phone_e164, otp)

	from nominations import msg91 as _sms

	return _sms.send_otp_sms(phone_e164, otp)
