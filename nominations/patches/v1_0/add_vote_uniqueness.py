"""Add UNIQUE INDEX on Vote(award, voter_phone_hash)."""
import frappe


def execute():
	try:
		frappe.db.sql("ALTER TABLE `tabVote` DROP INDEX `idx_one_vote_per_award`")
	except Exception:
		pass
	frappe.db.sql(
		"""
		ALTER TABLE `tabVote`
		ADD UNIQUE INDEX `idx_one_vote_per_award` (`award`, `voter_phone_hash`)
		"""
	)
