import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class Vote(Document):
	def before_insert(self):
		if not self.voted_at:
			self.voted_at = now_datetime()
		# Denormalize award from nomination
		if self.nomination and not self.award:
			self.award = frappe.db.get_value("Nomination", self.nomination, "award")

	def after_insert(self):
		campaign = frappe.db.get_value("Nomination", self.nomination, "campaign")
		frappe.publish_realtime(
			event="nominations:vote",
			message={
				"campaign": campaign,
				"award": self.award,
				"nomination": self.nomination,
				"category": self.category,
				"business_name": self.business_name,
				"contact_person_name": self.contact_person_name,
				"voted_at": str(self.voted_at),
			},
			after_commit=True,
		)
