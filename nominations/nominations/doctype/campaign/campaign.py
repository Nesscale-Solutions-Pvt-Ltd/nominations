import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, now_datetime


VALID_TRANSITIONS = {
	"Draft": {"Nominations Open"},
	"Nominations Open": {"Shortlisting"},
	"Shortlisting": {"Voting Open"},
	"Voting Open": {"Closed"},
	"Closed": set(),
}

# Reverse transitions allowed via the Reopen action (Nominations Manager only).
# Used when a campaign moved forward by mistake and needs to be rolled back.
REOPEN_TRANSITIONS = {
	"Nominations Open": {"Draft"},
	"Shortlisting": {"Nominations Open"},
	"Voting Open": {"Shortlisting", "Nominations Open"},
	"Closed": {"Voting Open", "Shortlisting", "Nominations Open"},
}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(text: str) -> str:
	text = (text or "").strip().lower()
	text = re.sub(r"[^a-z0-9]+", "-", text)
	return text.strip("-")


class Campaign(Document):
	def autoname(self):
		if not self.slug and self.title:
			self.slug = slugify(self.title)
		self.name = self.slug

	def validate(self):
		if not self.slug:
			self.slug = slugify(self.title)
		if not SLUG_RE.match(self.slug or ""):
			frappe.throw(_("Slug must contain only lowercase letters, digits, and hyphens."))

		if self.nomination_end and self.nomination_start and self.nomination_end <= self.nomination_start:
			frappe.throw(_("Nomination End must be after Nomination Start."))
		if self.voting_start and self.nomination_end and self.voting_start < self.nomination_end:
			frappe.throw(_("Voting Start must be on or after Nomination End."))
		if self.voting_end and self.voting_start and self.voting_end <= self.voting_start:
			frappe.throw(_("Voting End must be after Voting Start."))

		self._validate_transition()
		self._set_public_urls()

	def _validate_transition(self):
		if self.is_new():
			if self.status and self.status != "Draft":
				frappe.throw(_("New campaigns must start in Draft."))
			return
		old = self.get_doc_before_save()
		if not old:
			return
		if old.status == self.status:
			return

		# Allow a reverse (reopen) transition when explicitly requested via the
		# reopen() action. The flag is set on the in-memory doc only.
		if self.flags.allow_reopen:
			allowed_reverse = REOPEN_TRANSITIONS.get(old.status, set())
			if self.status in allowed_reverse:
				return
			frappe.throw(_("Cannot reopen campaign from {0} to {1}.").format(old.status, self.status))

		allowed = VALID_TRANSITIONS.get(old.status, set())
		if self.status not in allowed:
			frappe.throw(_("Cannot transition status from {0} to {1}.").format(old.status, self.status))

		if self.status == "Nominations Open":
			count = frappe.db.count("Award", {"campaign": self.name})
			if not count:
				frappe.throw(_("Add at least one Award before opening nominations."))
		elif self.status == "Voting Open":
			# Each award must have at least one finalist
			awards = frappe.get_all("Award", {"campaign": self.name}, ["name", "award_name"])
			missing = []
			for a in awards:
				finalists = frappe.db.count(
					"Nomination", {"award": a.name, "is_finalist": 1, "status": "Submitted"}
				)
				if not finalists:
					missing.append(a.award_name)
			if missing:
				frappe.throw(
					_("These awards have no finalists yet: {0}").format(", ".join(missing))
				)

	def _set_public_urls(self):
		base = get_url()
		self.nomination_public_url = f"{base}/nominate/{self.slug}"
		self.voting_public_url = f"{base}/vote/{self.slug}"

	def on_update(self):
		# NOTE: winners are no longer auto-decided when the campaign closes.
		# Managers mark the winner manually from the Nomination Finalist or
		# Award form once they've reviewed the votes.
		return

	def compute_winners(self):
		"""DEPRECATED — kept for manual/legacy callers; no longer auto-invoked.

		Picks the finalist with the most votes per award. Use the manual
		``mark_finalist_winner`` flow instead.
		"""
		awards = frappe.get_all("Award", {"campaign": self.name}, ["name"])
		for a in awards:
			top = frappe.db.sql(
				"""
				SELECT name FROM `tabNomination`
				WHERE award=%s AND is_finalist=1 AND status='Submitted'
				ORDER BY vote_count DESC, submitted_at ASC
				LIMIT 1
				""",
				(a.name,),
			)
			winner = top[0][0] if top else None
			frappe.db.set_value("Award", a.name, "winner_nomination", winner)

	# --- Whitelisted admin actions ---
	@frappe.whitelist()
	def transition_to(self, new_status: str):
		self.status = new_status
		self.save()
		return {"status": self.status}

	@frappe.whitelist()
	def reopen(self, target_status: str = "Nominations Open"):
		"""Roll a campaign back to an earlier status (e.g. when wrong dates
		caused it to advance to Shortlisting by mistake).

		Restricted to users with the "Nominations Manager" role.
		"""
		roles = frappe.get_roles(frappe.session.user)
		if "Nominations Manager" not in roles and "System Manager" not in roles:
			frappe.throw(_("Only Nominations Manager can reopen a campaign."))

		allowed = REOPEN_TRANSITIONS.get(self.status, set())
		if target_status not in allowed:
			frappe.throw(
				_("Cannot reopen campaign from {0} to {1}.").format(self.status, target_status)
			)

		# If we are leaving Closed, clear computed winners so they are not stale.
		if self.status == "Closed":
			for a in frappe.get_all("Award", {"campaign": self.name}, ["name"]):
				frappe.db.set_value("Award", a.name, "winner_nomination", None)

		self.flags.allow_reopen = True
		self.status = target_status
		self.save()
		return {"status": self.status}

	@frappe.whitelist()
	def clone_campaign(self):
		new = frappe.copy_doc(self)
		new.title = f"{self.title} (Copy)"
		new.slug = f"{self.slug}-copy-{frappe.generate_hash(length=4)}"
		new.status = "Draft"
		new.total_nominations = 0
		new.total_votes = 0
		new.insert()
		# Clone awards
		for a in frappe.get_all("Award", {"campaign": self.name}, ["name"]):
			award = frappe.get_doc("Award", a.name)
			new_award = frappe.copy_doc(award)
			new_award.campaign = new.name
			new_award.winner_nomination = None
			new_award.total_finalists = 0
			new_award.insert()
		return new.name
