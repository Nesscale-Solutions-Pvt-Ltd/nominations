"""Rebuild Nomination.justification HTML for every Nomination Finalist that
has been pushed to voting, and ensure any inline images referenced from the
justification or intro_message are publicly accessible.

This patch is idempotent and safe to re-run: it just re-renders the HTML from
the finalist's current selection of criteria responses + intro message + nominee
details using the controller's canonical `_build_justification` helper, and
flips any `/private/files/...` `File` records used inline to public.
"""
from __future__ import annotations

import re

import frappe

_PRIVATE_FILE_RE = re.compile(r"/private/files/([^\"'\s>?#]+)")


def _publicise_inline_files(html: str) -> str:
	"""Make every /private/files/<name> referenced in `html` public.

	Returns the html with `/private/files/` rewritten to `/files/`.
	"""
	if not html or "/private/files/" not in html:
		return html or ""
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
				title="Nominations patch: failed to publicise inline image",
				message=frappe.get_traceback(),
			)
	return _PRIVATE_FILE_RE.sub(r"/files/\1", html)


def execute():
	finalists = frappe.get_all(
		"Nomination Finalist",
		filters={"nomination": ["is", "set"]},
		pluck="name",
	)
	updated = 0
	for name in finalists:
		try:
			fin = frappe.get_doc("Nomination Finalist", name)
		except Exception:
			frappe.log_error(
				title=f"Nominations patch: failed to load finalist {name}",
				message=frappe.get_traceback(),
			)
			continue

		# 1) Ensure the finalist's own intro_message images are public.
		if fin.intro_message and "/private/files/" in fin.intro_message:
			new_intro = _publicise_inline_files(fin.intro_message)
			if new_intro != fin.intro_message:
				fin.db_set("intro_message", new_intro, update_modified=False)
				fin.intro_message = new_intro

		# 2) Rebuild the justification HTML using the canonical helper. We pass
		# selection=None so every criteria row with a response is included, the
		# intro message is included when present, and designation/organization
		# are included when present (matches the helper's defaults).
		selection = {
			"include_intro": bool((fin.intro_message or "").strip()),
			"include_designation": True,
			"include_organization": True,
			"include_photo": True,
		}
		justification = fin._build_justification(selection)
		justification = _publicise_inline_files(justification)

		nomination_name = fin.nomination
		if not nomination_name:
			continue
		if not frappe.db.exists("Nomination", nomination_name):
			continue

		# Also re-sync the nominee photo if it was originally suppressed by an
		# earlier push but the finalist now has one.
		updates = {"justification": justification}
		if fin.nominee_photo:
			current_photo = frappe.db.get_value("Nomination", nomination_name, "nominee_photo")
			if not current_photo:
				updates["nominee_photo"] = fin.nominee_photo

		frappe.db.set_value("Nomination", nomination_name, updates, update_modified=False)
		updated += 1

	frappe.db.commit()
	print(f"[nominations] rebuilt justification for {updated} finalist nominations")
