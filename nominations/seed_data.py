"""Seed script: wipe all Nomination/Award/Campaign data and create fresh test records.
Run with: bench --site pollen execute nominations.seed_data
"""
import frappe
from frappe.utils import now_datetime, add_days
from datetime import datetime, timedelta


def execute():
	# ── 1. Delete in dependency order ──────────────────────────────────────────
	for doctype in ("Vote", "Nomination", "Nomination OTP", "Award", "Campaign"):
		records = frappe.get_all(doctype, pluck="name")
		for r in records:
			frappe.delete_doc(doctype, r, ignore_permissions=True, force=True, delete_permanently=True)
		print(f"  Deleted {len(records)} {doctype} records")

	frappe.db.commit()

	# ── 2. Create Campaign ──────────────────────────────────────────────────────
	now = now_datetime()
	nom_start  = (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
	nom_end    = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
	vote_start = (now - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S")
	future     = (now + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

	campaign = frappe.get_doc({
		"doctype": "Campaign",
		"title": "Best of 2026",
		"slug": "best-of-2026",
		"status": "Draft",
		"description": "<p>Recognising outstanding contributors of 2026.</p>",
		"nomination_start": nom_start,
		"nomination_end": nom_end,
		"voting_start": vote_start,
		"voting_end": future,
	}).insert(ignore_permissions=True)
	print(f"\n  Campaign created: {campaign.name}")

	# ── 3. Create Awards ────────────────────────────────────────────────────────
	awards_data = [
		{
			"award_name": "Best Innovator",
			"slug": "best-innovator",
			"description": "For the person who brought the most creative ideas to life.",
			"sequence": 1,
			"max_finalists": 3,
		},
		{
			"award_name": "Community Champion",
			"slug": "community-champion",
			"description": "For outstanding contribution to the community.",
			"sequence": 2,
			"max_finalists": 3,
		},
		{
			"award_name": "Rising Star",
			"slug": "rising-star",
			"description": "For the most impressive newcomer of the year.",
			"sequence": 3,
			"max_finalists": 3,
		},
	]

	award_names = {}
	for a in awards_data:
		doc = frappe.get_doc({
			"doctype": "Award",
			"campaign": campaign.name,
			**a,
		}).insert(ignore_permissions=True)
		award_names[a["slug"]] = doc.name
		print(f"  Award created: {doc.name} ({a['award_name']})")

	# ── 4. Create Nominations (finalists) ───────────────────────────────────────
	nominations_data = [
		# Best Innovator
		{"award_slug": "best-innovator", "nominee_name": "Priya Sharma",     "justification": "Led the AI-powered scheduling system that saved 200+ hours/month.", "phone": "+919876543210"},
		{"award_slug": "best-innovator", "nominee_name": "Rahul Mehta",      "justification": "Single-handedly redesigned the entire onboarding pipeline.",           "phone": "+919876543211"},
		{"award_slug": "best-innovator", "nominee_name": "Anjali Desai",     "justification": "Introduced automated testing which cut bug reports by 40%.",            "phone": "+919876543212"},
		# Community Champion
		{"award_slug": "community-champion", "nominee_name": "Vikram Nair",  "justification": "Organised 12 community meetups and mentored 20 junior members.",        "phone": "+919876543213"},
		{"award_slug": "community-champion", "nominee_name": "Meera Patel",  "justification": "Runs the weekly knowledge-sharing series attended by 100+ people.",     "phone": "+919876543214"},
		{"award_slug": "community-champion", "nominee_name": "Arjun Singh",  "justification": "Founded the internal open-source guild with 50 active contributors.",   "phone": "+919876543215"},
		# Rising Star
		{"award_slug": "rising-star",    "nominee_name": "Kavya Reddy",      "justification": "Joined 6 months ago and already owns two critical microservices.",      "phone": "+919876543216"},
		{"award_slug": "rising-star",    "nominee_name": "Rohan Joshi",      "justification": "Shipped 3 major features in her first quarter.",                         "phone": "+919876543217"},
		{"award_slug": "rising-star",    "nominee_name": "Sneha Kulkarni",   "justification": "Proactively documented the entire legacy codebase in 2 months.",        "phone": "+919876543218"},
	]

	from nominations.otp import hash_phone

	for n in nominations_data:
		phone = n["phone"]
		nom = frappe.get_doc({
			"doctype": "Nomination",
			"campaign": campaign.name,
			"award": award_names[n["award_slug"]],
			"nominee_name": n["nominee_name"],
			"justification": n["justification"],
			"is_finalist": 1,
			"status": "Submitted",
			"nominator_phone": phone,
			"nominator_phone_hash": hash_phone(phone),
			"submitted_at": now_datetime(),
			"submitted_from_ip": "127.0.0.1",
		}).insert(ignore_permissions=True)
		print(f"  Nomination created: {nom.name} — {n['nominee_name']}")

	# Bypass the state-machine validator to set the campaign to Voting Open.
	frappe.db.set_value("Campaign", campaign.name, "status", "Voting Open")
	print(f"  Campaign status set to: Voting Open")

	frappe.db.commit()
	print("\n✓ Seed complete. Campaign slug: best-of-2026")
