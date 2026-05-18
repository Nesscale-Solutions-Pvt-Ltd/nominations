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
