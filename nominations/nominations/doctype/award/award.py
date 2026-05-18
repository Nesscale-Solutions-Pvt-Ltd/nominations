import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(text: str) -> str:
	text = (text or "").strip().lower()
	text = re.sub(r"[^a-z0-9]+", "-", text)
	return text.strip("-")


class Award(Document):
	def validate(self):
		if not self.slug:
			self.slug = slugify(self.award_name)
		if not SLUG_RE.match(self.slug or ""):
			frappe.throw(_("Slug must contain only lowercase letters, digits, and hyphens."))

		# Unique (campaign, slug)
		existing = frappe.db.get_value(
			"Award",
			{"campaign": self.campaign, "slug": self.slug, "name": ("!=", self.name)},
		)
		if existing:
			frappe.throw(_("Another Award in this Campaign already uses slug '{0}'.").format(self.slug))

		campaign = frappe.get_cached_doc("Campaign", self.campaign)
		self.public_voting_url = f"{get_url()}/vote/{campaign.slug}/{self.slug}"

		# is_finalist becomes read-only after voting opens — enforced at Nomination side
		# Compute total_finalists
		if not self.is_new():
			self.total_finalists = frappe.db.count(
				"Nomination", {"award": self.name, "is_finalist": 1, "status": "Submitted"}
			) or 0

	def on_trash(self):
		# Prevent deletion if nominations exist
		if frappe.db.count("Nomination", {"award": self.name}):
			frappe.throw(_("Cannot delete an Award that has nominations."))
