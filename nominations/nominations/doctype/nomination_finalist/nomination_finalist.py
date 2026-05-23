"""Nomination Finalist controller.

A Nomination Finalist is created manually by the admin for a Campaign + Award.
A unique token + public URL is generated so the nominee can fill in their
response against each criteria and upload supporting documents/videos without
logging in. Management later awards marks per criteria.

When a finalist is promoted to public voting, ``push_to_voting`` creates a
``Nomination`` record (is_finalist=1) and links it back via ``nomination``.
"""
from __future__ import annotations

import json
import secrets

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_url, now_datetime


class NominationFinalist(Document):
	def before_insert(self):
		if not self.submission_token:
			self.submission_token = secrets.token_urlsafe(24)

	def validate(self):
		if not self.submission_token:
			self.submission_token = secrets.token_urlsafe(24)
		self.public_url = f"{get_url()}/finalist/{self.submission_token}"
		self._normalise_criteria_files()
		self._recompute_totals()

	def _normalise_criteria_files(self):
		for row in self.criteria or []:
			raw = (row.response_files or "").strip()
			if not raw:
				row.response_files = ""
				continue
			try:
				data = json.loads(raw)
				if not isinstance(data, list):
					raise ValueError
				clean = []
				for item in data:
					if not isinstance(item, dict):
						continue
					url = (item.get("file_url") or "").strip()
					if not url:
						continue
					clean.append({
						"file_url": url,
						"file_type": item.get("file_type") or "Other",
						"caption": (item.get("caption") or "").strip(),
					})
				row.response_files = json.dumps(clean)
			except Exception:
				# Preserve whatever the manager typed but warn — don't blow up save.
				frappe.msgprint(
					_("Criteria '{0}': response files is not valid JSON; left as-is.").format(
						row.criteria_name or row.idx
					),
					alert=True,
				)

	def _recompute_totals(self):
		max_total = 0
		awarded_total = 0
		for row in self.criteria or []:
			max_total += cint(row.max_marks)
			awarded_total += cint(row.marks_awarded)
		self.total_max_marks = max_total
		self.total_marks_awarded = awarded_total
		self.score_percentage = round((awarded_total / max_total * 100), 2) if max_total else 0

	def mark_sent(self):
		self.db_set("status", "Sent")
		self.db_set("sent_at", now_datetime())

	def mark_submitted(self):
		self.db_set("status", "Submitted")
		self.db_set("submitted_at", now_datetime())

	def mark_evaluated(self):
		self.db_set("status", "Evaluated")
		self.db_set("evaluated_at", now_datetime())

	def push_to_voting(self) -> str:
		"""Create a ``Nomination`` record from this finalist and link it back.

		Idempotent: if ``self.nomination`` already exists, returns it.
		"""
		if self.nomination and frappe.db.exists("Nomination", self.nomination):
			return self.nomination

		justification = self._build_justification()
		phone = (self.nominee_phone or "").strip() or "+0000000000"

		nom = frappe.get_doc({
			"doctype": "Nomination",
			"campaign": self.campaign,
			"award": self.award,
			"nominee_name": self.nominee_name,
			"nominee_photo": self.nominee_photo,
			"justification": justification or self.nominee_name,
			"nominator_phone": phone,
			"is_finalist": 1,
			"status": "Submitted",
			"submitted_at": now_datetime(),
		}).insert(ignore_permissions=True)

		self.db_set("nomination", nom.name)
		return nom.name

	def _build_justification(self) -> str:
		parts = []
		for row in self.criteria or []:
			text = (row.response_text or "").strip()
			if not text:
				continue
			parts.append(f"### {row.criteria_name}\n{text}")
		return "\n\n".join(parts)


def regenerate_token(name: str) -> str:
	"""Mint a new token (invalidates the previous public URL)."""
	doc = frappe.get_doc("Nomination Finalist", name)
	doc.submission_token = secrets.token_urlsafe(24)
	doc.save(ignore_permissions=False)
	return doc.public_url

