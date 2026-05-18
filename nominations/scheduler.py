"""Scheduled jobs."""
from __future__ import annotations

import frappe
from frappe.utils import add_to_date, now_datetime


def auto_transition_campaigns():
	"""Move campaigns forward based on timestamps."""
	now = now_datetime()
	campaigns = frappe.get_all(
		"Campaign",
		fields=["name", "status", "nomination_start", "nomination_end", "voting_start", "voting_end"],
		filters={"status": ("!=", "Closed")},
	)
	for c in campaigns:
		try:
			doc = frappe.get_doc("Campaign", c.name)
			target = None
			if doc.status == "Draft" and doc.nomination_start and doc.nomination_start <= now:
				target = "Nominations Open"
			elif doc.status == "Nominations Open" and doc.nomination_end and doc.nomination_end <= now:
				target = "Shortlisting"
			elif doc.status == "Shortlisting" and doc.voting_start and doc.voting_start <= now:
				target = "Voting Open"
			elif doc.status == "Voting Open" and doc.voting_end and doc.voting_end <= now:
				target = "Closed"
			if target and target != doc.status:
				doc.status = target
				doc.save(ignore_permissions=True)
		except Exception:
			# Validation may legitimately block (e.g. no finalists yet).
			frappe.db.rollback()
			frappe.log_error(frappe.get_traceback(), f"auto_transition_campaigns: {c.name}")


def cleanup_expired_otps():
	cutoff = add_to_date(now_datetime(), hours=-1)
	frappe.db.sql("DELETE FROM `tabOTP Request` WHERE creation < %s", (cutoff,))
	frappe.db.commit()
