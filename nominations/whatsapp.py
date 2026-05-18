"""Send OTPs through the frappe_whatsapp app's templated messaging.

This module is a thin adapter so the existing `request_otp` flow can dispatch
to WhatsApp instead of MSG91 when configured. We create a `WhatsApp Message`
doc with `message_type="Template"` and `body_param` set to the OTP value(s);
frappe_whatsapp's `before_insert` hook handles the Meta API call.
"""
from __future__ import annotations

import json

import frappe
from frappe import _


def _settings():
	return frappe.get_cached_doc("Nominations Settings")


def send_otp_whatsapp(phone_e164: str, otp: str) -> dict:
	"""Send the OTP using a configured WhatsApp template.

	The template must have at least one body variable for the OTP. Additional
	variables (if any) are passed as empty strings so Meta accepts the payload.
	The template name comes from Nominations Settings -> whatsapp_template.
	"""
	settings = _settings()
	template_name = settings.get("whatsapp_template")
	if not template_name:
		frappe.log_error(
			"WhatsApp template missing in Nominations Settings",
			"Nominations WhatsApp",
		)
		frappe.throw(
			_(
				"WhatsApp template is not configured. "
				"Set a WhatsApp Template in Nominations Settings, "
				"switch OTP Channel to SMS, or disable 'Require OTP Verification'."
			)
		)

	# Build the body params dict expected by frappe_whatsapp.
	# Count `{{N}}` placeholders in the template body and pass OTP for {{1}};
	# remaining variables default to empty strings.
	try:
		template_doc = frappe.get_cached_doc("WhatsApp Templates", template_name)
	except frappe.DoesNotExistError:
		frappe.throw(_("Configured WhatsApp template does not exist."))

	body_text = template_doc.get("template") or ""
	# Naive variable count: highest {{n}} found.
	import re
	indices = [int(m) for m in re.findall(r"\{\{(\d+)\}\}", body_text)]
	var_count = max(indices) if indices else 1

	params = {str(i + 1): "" for i in range(var_count)}
	params["1"] = otp  # First variable receives the OTP.

	# Point reference_doctype/name at the Nominations Settings single doc so any
	# other code path in frappe_whatsapp that dereferences self.reference_doctype
	# does not crash on None.
	try:
		frappe.get_doc(
			{
				"doctype": "WhatsApp Message",
				"to": phone_e164,
				"type": "Outgoing",
				"message_type": "Template",
				"content_type": "text",
				"template": template_name,
				"body_param": json.dumps(params),
				"reference_doctype": "Nominations Settings",
				"reference_name": "Nominations Settings",
			}
		).insert(ignore_permissions=True)
	except frappe.ValidationError as e:
		# frappe_whatsapp re-throws the bare Meta error message (e.g.
		# "(#100) Invalid parameter") but the actionable detail
		# (error_data.details) sits in frappe.flags.integration_request.
		# Pull it out so the API caller gets something useful, and log the
		# full Meta response for ops.
		details = _meta_error_details()
		frappe.log_error(
			frappe.get_traceback() + "\n\nMeta error payload:\n" + json.dumps(details, indent=2),
			f"Nominations WhatsApp OTP failed (template={template_name})",
		)
		hint = details.get("error_data", {}).get("details") or details.get("message") or str(e)
		frappe.throw(_("WhatsApp could not deliver the verification code: {0}").format(hint))
	except Exception as e:
		frappe.log_error(
			frappe.get_traceback(),
			f"Nominations WhatsApp OTP failed (template={template_name})",
		)
		frappe.throw(
			_("Could not send WhatsApp verification message: {0}").format(
				str(e) or "unknown error"
			)
		)

	return {"channel": "whatsapp", "template": template_name}


def _meta_error_details() -> dict:
	"""Return the ``error`` block from the last Meta Graph API response, or {}."""
	req = getattr(frappe.flags, "integration_request", None)
	if req is None:
		return {}
	try:
		return req.json().get("error", {}) or {}
	except Exception:
		return {}
