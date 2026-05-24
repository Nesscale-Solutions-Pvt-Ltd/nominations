"""Make inline images in existing Nomination Finalist `intro_message` public.

Frappe's rich-text editor uploads pasted images as private by default. The
public finalist URL has no session, so those `/private/files/...` URLs return
403. New saves are fixed by the controller's `_publicise_inline_images` hook;
this patch backfills records created before that hook existed.
"""
from __future__ import annotations

import re

import frappe

_PRIVATE_FILE_RE = re.compile(r"/private/files/([^\"'\s>?#]+)")


def execute():
	if not frappe.db.has_table("Nomination Finalist"):
		return

	rows = frappe.get_all(
		"Nomination Finalist",
		filters={"intro_message": ("like", "%/private/files/%")},
		fields=["name", "intro_message"],
	)
	if not rows:
		return

	for row in rows:
		html = row.intro_message or ""
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
					title="publicise_finalist_intro_images: file flip failed",
					message=frappe.get_traceback(),
				)
				continue

		new_html = _PRIVATE_FILE_RE.sub(r"/files/\1", html)
		if new_html != html:
			frappe.db.set_value(
				"Nomination Finalist",
				row.name,
				"intro_message",
				new_html,
				update_modified=False,
			)

	frappe.clear_cache(doctype="Nomination Finalist")
