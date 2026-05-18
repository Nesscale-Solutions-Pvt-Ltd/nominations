import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime


class OTPRequest(Document):
	def before_insert(self):
		if not self.created_at:
			self.created_at = now_datetime()
		if not self.expires_at:
			settings = frappe.get_single("Nominations Settings")
			ttl = int(settings.otp_ttl_seconds or 600)
			self.expires_at = add_to_date(self.created_at, seconds=ttl)
