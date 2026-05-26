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
import re
import secrets

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_url, now_datetime


# Rich-text fields whose inline images must be reachable from the public URL.
_PUBLIC_HTML_FIELDS = ("intro_message",)
_PRIVATE_FILE_RE = re.compile(r"/private/files/([^\"'\s>?#]+)")


class NominationFinalist(Document):
	def before_insert(self):
		if not self.submission_token:
			self.submission_token = secrets.token_urlsafe(24)

	def validate(self):
		if not self.submission_token:
			self.submission_token = secrets.token_urlsafe(24)
		self.public_url = f"{get_url()}/finalist/{self.submission_token}"
		self._publicise_inline_images()
		self._normalise_criteria_files()
		self._recompute_totals()

	def _publicise_inline_images(self):
		"""Frappe's rich text editor uploads inline images as private by default.
		The finalist page is opened without a login, so any /private/files/...
		URLs return 403. Flip those File docs to public and rewrite the URLs.
		"""
		for fieldname in _PUBLIC_HTML_FIELDS:
			html = self.get(fieldname)
			if not html or "/private/files/" not in html:
				continue
			seen: set[str] = set()
			for match in _PRIVATE_FILE_RE.finditer(html):
				private_url = "/private/files/" + match.group(1)
				if private_url in seen:
					continue
				seen.add(private_url)
				file_name = frappe.db.get_value("File", {"file_url": private_url}, "name")
				if not file_name:
					continue
				try:
					f = frappe.get_doc("File", file_name)
					if f.is_private:
						f.is_private = 0
						f.save(ignore_permissions=True)
				except Exception:
					frappe.log_error(
						title="Nomination Finalist: failed to make inline image public",
						message=frappe.get_traceback(),
					)
					continue
			# Replace any remaining /private/files/... references with /files/...
			# (Frappe rewrites the File.file_url on save, but the embedded HTML
			# still points at the old path until we update it ourselves.)
			new_html = _PRIVATE_FILE_RE.sub(r"/files/\1", html)
			if new_html != html:
				self.set(fieldname, new_html)


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

	def push_to_voting(self, selection: dict | None = None, justification_override: str | None = None) -> str:
		"""Create a ``Nomination`` record from this finalist and link it back.

		``selection`` is an optional dict like::

		    {
		        "criteria": ["row-name-1", "row-name-3"],  # rows to include
		        "include_photo": True,
		        "include_designation": True,
		        "include_organization": True,
		    }

		If ``selection`` is ``None`` (or ``criteria`` is missing), all answered
		criteria and all nominee details are included.

		If ``justification_override`` (HTML) is provided, it is stored verbatim
		on the resulting Nomination instead of the auto-built justification.

		Idempotent: if ``self.nomination`` already exists, returns it.
		"""
		if self.nomination and frappe.db.exists("Nomination", self.nomination):
			return self.nomination

		selection = selection or {}
		override = (justification_override or "").strip()
		justification = override or self._build_justification(selection)
		phone = (self.nominee_phone or "").strip() or "+0000000000"
		include_photo = selection.get("include_photo", True) if selection else True

		nom = frappe.get_doc({
			"doctype": "Nomination",
			"campaign": self.campaign,
			"award": self.award,
			"nominee_name": self.nominee_name,
			"nominee_photo": self.nominee_photo if include_photo else None,
			"justification": justification or self.nominee_name,
			"nominator_phone": phone,
			"is_finalist": 1,
			"status": "Submitted",
			"submitted_at": now_datetime(),
		}).insert(ignore_permissions=True)

		self.db_set("nomination", nom.name)
		return nom.name

	def _build_justification(self, selection: dict | None = None) -> str:
		"""Build an HTML justification block for the public Nomination doc.

		Nomination.justification is a Text Editor (HTML) field, so we emit HTML
		with inline styles so the rendered output looks good both inside the
		Frappe rich-text editor and on the public voting page (where the
		surrounding ``prose`` styles also kick in).
		"""
		from html import escape

		selection = selection or {}
		selected_rows = selection.get("criteria")
		# When selection is missing/empty, include everything that has text.
		include_all = not selected_rows
		selected_set = set(selected_rows or [])
		include_intro = bool(selection.get("include_intro"))

		parts: list[str] = []

		# 1) Designation / Organization on the very first line so voters see
		# the nominee's role immediately. Designation comes first, then a thin
		# separator, then organization.
		header_bits: list[str] = []
		if selection.get("include_designation", True) and (self.designation or "").strip():
			header_bits.append(
				'<span style="color:#0f766e;font-weight:600">'
				+ escape(self.designation.strip())
				+ "</span>"
			)
		if selection.get("include_organization", True) and (self.organization or "").strip():
			header_bits.append(
				'<span style="color:#64748b">'
				+ escape(self.organization.strip())
				+ "</span>"
			)
		if header_bits:
			parts.append(
				'<p style="margin:0 0 12px 0;font-size:14px;line-height:1.4">'
				+ '<span style="color:#94a3b8;margin:0 8px">•</span>'.join(header_bits)
				+ "</p>"
			)

		# 2) Optional intro message (rich HTML) directly under the header.
		if include_intro and (self.intro_message or "").strip():
			parts.append(
				'<div style="margin:0 0 16px 0">'
				+ self.intro_message.strip()
				+ "</div>"
			)

		# 3) Each criteria row rendered as a soft elevated card with a colored
		# left accent rail and a matching numbered chip. The card background
		# stays white so the response copy is the focus; only the accent rail,
		# the numbered chip and the title pick up the rotating palette color.
		palette = [
			("#7c3aed", "#ede9fe"),  # violet
			("#0ea5e9", "#e0f2fe"),  # sky
			("#059669", "#d1fae5"),  # emerald
			("#d97706", "#fef3c7"),  # amber
			("#db2777", "#fce7f3"),  # pink
			("#4f46e5", "#e0e7ff"),  # indigo
		]
		shown = 0
		for row in self.criteria or []:
			if not include_all and row.name not in selected_set:
				continue
			text = (row.response_text or "").strip()
			if not text:
				continue
			accent, soft = palette[shown % len(palette)]
			shown += 1
			body = escape(text).replace("\n", "<br>")
			parts.append(
				'<div style="margin:0 0 14px 0;background:#ffffff;'
				'border:1px solid #e5e7eb;border-left:4px solid ' + accent + ';'
				'border-radius:10px;padding:14px 16px;'
				'box-shadow:0 1px 2px rgba(15,23,42,0.04)">'
				f'<h4 style="margin:0 0 8px 0;color:{accent};font-size:15px;font-weight:700;'
				'line-height:1.35;letter-spacing:0.01em">'
				f"{escape(row.criteria_name or '')}</h4>"
				f'<p style="margin:0;color:#334155;font-size:14px;line-height:1.6">'
				+ body + "</p>"
				"</div>"
			)

		return "".join(parts)

	def preview_push(self, selection: dict | None = None) -> dict:
		"""Render the would-be Nomination payload for preview in the desk dialog."""
		include_photo = True if selection is None else bool(selection.get("include_photo", True))
		return {
			"nominee_name": self.nominee_name,
			"nominee_photo": self.nominee_photo if include_photo else None,
			"justification": self._build_justification(selection),
		}

	def mark_winner(self):
		"""Mark this finalist as the winner of its award.

		Sets the ``Award.winner_nomination`` to the linked voting Nomination
		(if any) so the public voting / campaign page can render the winner.
		"""
		if not self.nomination:
			frappe.throw(_("Push this finalist to voting before marking as winner."))
		# Clear any previous winner for the award (one winner per award).
		previous = frappe.db.get_value("Award", self.award, "winner_nomination")
		if previous and previous != self.nomination:
			# Unset the is_winner flag on the prior finalist if we can find it.
			prior = frappe.db.get_value(
				"Nomination Finalist", {"award": self.award, "nomination": previous}, "name"
			)
			if prior and prior != self.name:
				frappe.db.set_value("Nomination Finalist", prior, {
					"is_winner": 0,
					"status": "Not Selected",
				}, update_modified=False)
		frappe.db.set_value("Award", self.award, "winner_nomination", self.nomination)
		self.db_set("is_winner", 1)
		self.db_set("status", "Winner")

	def unmark_winner(self):
		current = frappe.db.get_value("Award", self.award, "winner_nomination")
		if current and current == self.nomination:
			frappe.db.set_value("Award", self.award, "winner_nomination", None)
		self.db_set("is_winner", 0)
		if self.status == "Winner":
			self.db_set("status", "Evaluated" if self.evaluated_at else "Submitted")


def regenerate_token(name: str) -> str:
	"""Mint a new token (invalidates the previous public URL)."""
	doc = frappe.get_doc("Nomination Finalist", name)
	doc.submission_token = secrets.token_urlsafe(24)
	doc.save(ignore_permissions=False)
	return doc.public_url

