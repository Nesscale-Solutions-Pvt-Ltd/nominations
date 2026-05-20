import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class Nomination(Document):
	def before_insert(self):
		if not self.submitted_at:
			self.submitted_at = now_datetime()
		# Auto-fetch campaign from award if not set
		if self.award and not self.campaign:
			self.campaign = frappe.db.get_value("Award", self.award, "campaign")

	def validate(self):
		# Verify award belongs to campaign
		award_campaign = frappe.db.get_value("Award", self.award, "campaign")
		if award_campaign != self.campaign:
			frappe.throw(_("Award does not belong to this Campaign."))

		# Lock is_finalist once voting opens
		campaign_status = frappe.db.get_value("Campaign", self.campaign, "status")
		if campaign_status in ("Voting Open", "Closed") and not self.is_new():
			old = self.get_doc_before_save()
			if old and old.is_finalist != self.is_finalist:
				frappe.throw(_("Cannot change finalist status after voting has opened."))

		if len((self.justification or "").strip()) < 20:
			frappe.throw(_("Justification must be at least 20 characters."))

	def after_insert(self):
		frappe.db.sql(
			"UPDATE `tabCampaign` SET total_nominations = total_nominations + 1 WHERE name=%s",
			(self.campaign,),
		)
		frappe.publish_realtime(
			event="nominations:nomination",
			message={
				"campaign": self.campaign,
				"award": self.award,
				"nomination": self.name,
				"nominee_name": self.nominee_name,
				"submitted_at": str(self.submitted_at),
			},
			after_commit=True,
		)

	def on_update(self):
		# Keep award.total_finalists in sync
		if self.award:
			count = frappe.db.count(
				"Nomination", {"award": self.award, "is_finalist": 1, "status": "Submitted"}
			)
			frappe.db.set_value("Award", self.award, "total_finalists", count, update_modified=False)

	def on_trash(self):
		if frappe.db.count("Vote", {"nomination": self.name}):
			frappe.throw(_("Cannot delete a Nomination that has votes."))
		frappe.db.sql(
			"UPDATE `tabCampaign` SET total_nominations = GREATEST(total_nominations - 1, 0) WHERE name=%s",
			(self.campaign,),
		)
