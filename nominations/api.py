"""Public, guest-accessible API for the Nominations app.

All endpoints are rate-limited and shaped per Campaign lifecycle state.
"""
from __future__ import annotations

import re

from datetime import timedelta

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime, now_datetime

from nominations import otp as _otp, security


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

E164_RE = re.compile(r"^\+?[1-9]\d{7,14}$")


def _normalize_phone(phone: str) -> str:
	if not phone:
		frappe.throw(_("Phone number is required."))
	phone = phone.strip().replace(" ", "").replace("-", "")
	if not phone.startswith("+"):
		default_cc = frappe.get_cached_doc("Nominations Settings").default_country_code or "+91"
		if phone.startswith("0"):
			phone = phone[1:]
		phone = f"{default_cc}{phone}"
	if not E164_RE.match(phone):
		frappe.throw(_("Phone number is not in a valid format."))
	return phone


# Trusted proxy networks whose X-Forwarded-For values we accept. Localhost is
# included so dev setups behind nginx still resolve to the real client.
_TRUSTED_PROXY_PREFIXES = ("127.", "10.", "192.168.", "172.16.", "172.17.",
	"172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
	"172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
	"172.30.", "172.31.", "::1")


def _client_ip() -> str:
	"""Return the best-effort public IP for the current request.

	Falls back to ``frappe.local.request_ip`` if no proxy headers are present.
	Honors ``X-Forwarded-For`` / ``X-Real-IP`` when the immediate peer is a
	trusted proxy (localhost or RFC1918), so we don't trust spoofed headers
	from arbitrary public clients.
	"""
	req = getattr(frappe.local, "request", None)
	peer = getattr(frappe.local, "request_ip", None) or ""

	if req is not None:
		# Only trust forwarding headers when the immediate peer looks like a proxy.
		if any(peer.startswith(p) for p in _TRUSTED_PROXY_PREFIXES):
			xff = req.headers.get("X-Forwarded-For", "")
			if xff:
				# Left-most entry is the original client.
				candidate = xff.split(",")[0].strip()
				if candidate:
					return candidate
			real_ip = req.headers.get("X-Real-IP", "").strip()
			if real_ip:
				return real_ip
	return peer


def _get_campaign(slug: str):
	row = frappe.db.get_value(
		"Campaign",
		{"slug": slug},
		[
			"name",
			"slug",
			"title",
			"description",
			"status",
			"cover_image",
			"nomination_start",
			"nomination_end",
			"voting_start",
			"voting_end",
			"total_nominations",
			"total_votes",
		],
		as_dict=True,
	)
	if not row or row.status == "Draft":
		frappe.local.response.http_status_code = 404
		frappe.throw(_("Campaign not found."))
	return row


def _award_payload(award_row: dict, include_finalists: bool, include_winner: bool) -> dict:
	out = {
		"name": award_row.name,
		"slug": award_row.slug,
		"award_name": award_row.award_name,
		"description": award_row.description,
		"icon_or_image": award_row.icon_or_image,
		"sequence": award_row.sequence or 0,
		"max_finalists": award_row.max_finalists or 5,
		"winner_nomination": award_row.winner_nomination if include_winner else None,
		"finalists": [],
	}
	if include_finalists:
		finalists = frappe.get_all(
			"Nomination",
			filters={"award": award_row.name, "is_finalist": 1, "status": "Submitted"},
			fields=["name", "nominee_name", "nominee_photo", "justification", "vote_count"],
			order_by="vote_count DESC, submitted_at ASC",
		)
		# Pull designation/organization from the linked Nomination Finalist
		# (the public Nomination doc doesn't carry these fields itself).
		extras: dict[str, dict] = {}
		if finalists:
			for fin in frappe.get_all(
				"Nomination Finalist",
				filters={"nomination": ["in", [f.name for f in finalists]]},
				fields=["nomination", "designation", "organization"],
			):
				extras[fin.nomination] = {
					"designation": (fin.designation or "").strip(),
					"organization": (fin.organization or "").strip(),
				}
		total = sum(f.vote_count or 0 for f in finalists) or 0
		for f in finalists:
			pct = round((f.vote_count or 0) / total * 100, 1) if total else 0.0
			extra = extras.get(f.name, {})
			out["finalists"].append(
				{
					"name": f.name,
					"nominee_name": f.nominee_name,
					"nominee_photo": f.nominee_photo,
					"justification": f.justification,
					"vote_count": f.vote_count or 0,
					"vote_percentage": pct,
					"designation": extra.get("designation", ""),
					"organization": extra.get("organization", ""),
				}
			)
	return out


def _public_settings():
	s = frappe.get_cached_doc("Nominations Settings")
	return {
		"brand_name": s.public_brand_name or "Nominations",
		"logo": s.public_logo,
		"primary_color": s.public_primary_color or "#1F4E79",
		"default_country_code": s.default_country_code or "+91",
		"otp_length": cint(s.otp_length) or 6,
		"otp_enabled": bool(cint(s.otp_enabled)) if s.get("otp_enabled") is not None else True,
		"header_bg": s.get("public_header_bg") or "",
		"header_gradient_end": s.get("public_header_gradient_end") or "",
		"gradient_direction": s.get("public_gradient_direction") or "to right",
		"page_bg": s.get("public_page_bg") or "",
		"header_text_color": s.get("public_header_text_color") or "",
	}


# ---------------------------------------------------------------------------
# 4.1 get_campaign
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def get_campaign(slug: str):
	campaign = _get_campaign(slug)
	awards_rows = frappe.get_all(
		"Award",
		filters={"campaign": campaign.name},
		fields=[
			"name",
			"slug",
			"award_name",
			"description",
			"icon_or_image",
			"sequence",
			"max_finalists",
			"winner_nomination",
		],
		order_by="sequence ASC, award_name ASC",
	)
	include_finalists = campaign.status in ("Voting Open", "Closed")
	include_winner = campaign.status == "Closed"
	awards = [_award_payload(frappe._dict(a), include_finalists, include_winner) for a in awards_rows]
	return {
		"campaign": campaign,
		"awards": awards,
		"settings": _public_settings(),
	}


# ---------------------------------------------------------------------------
# 4.2 get_award
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def get_award(campaign_slug: str, award_slug: str):
	campaign = _get_campaign(campaign_slug)
	award_row = frappe.db.get_value(
		"Award",
		{"campaign": campaign.name, "slug": award_slug},
		[
			"name",
			"slug",
			"award_name",
			"description",
			"icon_or_image",
			"sequence",
			"max_finalists",
			"winner_nomination",
		],
		as_dict=True,
	)
	if not award_row:
		frappe.local.response.http_status_code = 404
		frappe.throw(_("Award not found."))
	include_finalists = campaign.status in ("Voting Open", "Closed")
	include_winner = campaign.status == "Closed"
	return {
		"campaign": campaign,
		"award": _award_payload(award_row, include_finalists, include_winner),
		"settings": _public_settings(),
	}


# ---------------------------------------------------------------------------
# 4.3 request_otp
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
@rate_limit(key="phone", limit=3, seconds=600)
def request_otp(phone: str, purpose: str, campaign_slug: str, award_slug: str | None = None):
	if purpose not in ("nominate", "vote"):
		frappe.throw(_("Invalid purpose."))
	phone = _normalize_phone(phone)
	campaign = _get_campaign(campaign_slug)

	if purpose == "nominate" and campaign.status != "Nominations Open":
		frappe.throw(_("Nominations are not currently open."))
	if purpose == "vote" and campaign.status != "Voting Open":
		frappe.throw(_("Voting is not currently open."))

	award_name = None
	if purpose == "vote":
		if not award_slug:
			frappe.throw(_("Award is required for voting."))
		award_name = frappe.db.get_value(
			"Award", {"campaign": campaign.name, "slug": award_slug}, "name"
		)
		if not award_name:
			frappe.throw(_("Award not found."))
		if frappe.db.exists(
			"Vote",
			{"award": award_name, "voter_phone_hash": _otp.hash_phone(phone)},
		):
			frappe.local.response.http_status_code = 409
			frappe.throw(_("You have already voted for this award."))

	settings = frappe.get_cached_doc("Nominations Settings")
	otp_enabled = bool(cint(settings.get("otp_enabled", 1)))
	ttl = int(settings.otp_ttl_seconds or 600)

	if not otp_enabled:
		# Skip OTP entirely: issue the verification token immediately with the
		# phone signed into the payload so downstream submits don't need a
		# server-side OTP record.
		token = security.issue_token(
			{
				"phone": phone,
				"phone_hash": _otp.hash_phone(phone),
				"purpose": purpose,
				"campaign": campaign.name,
				"award_slug": award_slug,
			},
			ttl_seconds=300,
		)
		return {
			"otp_enabled": False,
			"verification_token": token,
			"expires_in": 300,
			"phone_masked": _otp.mask_phone(phone),
		}

	otp = _otp.generate_otp()

	# Drop any prior pending OTPs for this mobile so only the latest is valid.
	frappe.db.delete("Nomination OTP", {"mobile_no": phone})
	doc = frappe.get_doc(
		{
			"doctype": "Nomination OTP",
			"mobile_no": phone,
			"otp": otp,
			"purpose": purpose,
			"campaign": campaign.name,
			"award": award_name,
			"award_slug": award_slug,
		}
	).insert(ignore_permissions=True)

	return {
		"otp_enabled": True,
		"request_id": doc.name,
		"expires_in": ttl,
		"phone_masked": _otp.mask_phone(phone),
	}


# ---------------------------------------------------------------------------
# 4.4 verify_otp
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
@rate_limit(key="request_id", limit=10, seconds=600)
def verify_otp(request_id: str, otp: str):
	settings = frappe.get_cached_doc("Nominations Settings")

	try:
		doc = frappe.get_doc("Nomination OTP", request_id)
	except frappe.DoesNotExistError:
		frappe.local.response.http_status_code = 400
		frappe.throw(_("This verification code is no longer valid."))

	ttl = int(settings.otp_ttl_seconds or 600)
	if get_datetime(doc.creation) + timedelta(seconds=ttl) < now_datetime():
		frappe.delete_doc("Nomination OTP", doc.name, ignore_permissions=True, force=True)
		frappe.local.response.http_status_code = 400
		frappe.throw(_("Verification code has expired."))

	if not _otp.constant_time_eq(str(doc.otp or ""), str(otp or "")):
		frappe.local.response.http_status_code = 400
		frappe.throw(_("Incorrect code."))

	phone = doc.mobile_no
	purpose = doc.get("purpose")
	campaign = doc.get("campaign")
	award_slug = doc.get("award_slug")

	# Single-use: drop the OTP once consumed.
	frappe.delete_doc("Nomination OTP", doc.name, ignore_permissions=True, force=True)

	token = security.issue_token(
		{
			"phone": phone,
			"phone_hash": _otp.hash_phone(phone),
			"purpose": purpose,
			"campaign": campaign,
			"award_slug": award_slug,
		},
		ttl_seconds=300,
	)
	return {"verification_token": token, "expires_in": 300}


# ---------------------------------------------------------------------------
# 4.5 submit_nomination
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
@rate_limit(key="verification_token", limit=3, seconds=600)
def submit_nomination(
	verification_token: str,
	award_slug: str,
	nominee_name: str,
	justification: str,
	nominee_photo_url: str | None = None,
	hp_field: str | None = None,
	open_ms: int | None = None,
):
	# Honeypot + timing
	if hp_field:
		frappe.local.response.http_status_code = 400
		frappe.throw(_("Submission rejected."))
	if open_ms is not None and cint(open_ms) < 2000:
		frappe.local.response.http_status_code = 400
		frappe.throw(_("Submission rejected."))

	payload = security.verify_token(verification_token)
	if payload.get("purpose") != "nominate":
		frappe.throw(_("Verification token is for a different action."))

	campaign_name = payload.get("campaign")
	campaign_status = frappe.db.get_value("Campaign", campaign_name, "status")
	if campaign_status != "Nominations Open":
		frappe.throw(_("Nominations are not currently open."))

	award_name = frappe.db.get_value(
		"Award", {"campaign": campaign_name, "slug": award_slug}, "name"
	)
	if not award_name:
		frappe.throw(_("Award not found."))

	# Phone comes straight from the signed verification token now (was a
	# secondary lookup against OTP Request previously).
	phone_raw = payload.get("phone")
	if not phone_raw:
		frappe.throw(_("Verification expired. Please request a new code."))

	doc = frappe.get_doc(
		{
			"doctype": "Nomination",
			"campaign": campaign_name,
			"award": award_name,
			"nominee_name": nominee_name,
			"nominee_photo": nominee_photo_url,
			"justification": justification,
			"nominator_phone": phone_raw,
			"nominator_phone_hash": payload.get("phone_hash"),
			"submitted_from_ip": _client_ip(),
		}
	).insert(ignore_permissions=True)
	return {
		"nomination_id": doc.name,
		"thank_you_message": "Your nomination is in!",
	}


# ---------------------------------------------------------------------------
# 4.6 submit_vote
# ---------------------------------------------------------------------------

_VOTE_CATEGORIES = {"Farmer", "Pollen Officer", "Technician", "Back Office", "Factory", "Management"}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="verification_token", limit=3, seconds=600)
def submit_vote(
	verification_token: str,
	nomination_id: str,
	business_name: str,
	contact_person_name: str,
	category: str,
	via: str = "campaign",
):
	payload = security.verify_token(verification_token)
	if payload.get("purpose") != "vote":
		frappe.throw(_("Verification token is for a different action."))

	business_name = (business_name or "").strip()
	contact_person_name = (contact_person_name or "").strip()
	category = (category or "").strip()
	if not business_name:
		frappe.throw(_("Business name is required."))
	if not contact_person_name:
		frappe.throw(_("Contact person name is required."))
	if category not in _VOTE_CATEGORIES:
		frappe.throw(_("Please select a valid category."))

	nomination = frappe.db.get_value(
		"Nomination",
		nomination_id,
		["name", "campaign", "award", "is_finalist", "status", "vote_count"],
		as_dict=True,
	)
	if not nomination:
		frappe.throw(_("Nomination not found."))

	campaign_status = frappe.db.get_value("Campaign", nomination.campaign, "status")
	if campaign_status != "Voting Open":
		frappe.throw(_("Voting is not currently open."))
	if not nomination.is_finalist or nomination.status != "Submitted":
		frappe.throw(_("This nominee is not a finalist."))

	award_slug = frappe.db.get_value("Award", nomination.award, "slug")
	if payload.get("award_slug") and payload["award_slug"] != award_slug:
		frappe.throw(_("Verification token cannot be used for this award."))
	if payload.get("campaign") != nomination.campaign:
		frappe.throw(_("Verification token does not match this campaign."))

	voted_via = "Award URL" if (via or "").lower() == "award" else "Campaign URL"

	try:
		vote = frappe.get_doc(
			{
				"doctype": "Vote",
				"nomination": nomination.name,
				"award": nomination.award,
				"business_name": business_name,
				"contact_person_name": contact_person_name,
				"category": category,
				"voter_phone_hash": payload.get("phone_hash"),
				"voted_from_ip": _client_ip(),
				"voted_via": voted_via,
			}
		).insert(ignore_permissions=True)
	except frappe.db.DuplicateEntryError:
		frappe.local.response.http_status_code = 409
		frappe.throw(_("You have already voted for this award."))
	except Exception as e:
		# Some adapters raise raw IntegrityError; treat duplicates as 409.
		if "Duplicate" in str(e) or "1062" in str(e):
			frappe.local.response.http_status_code = 409
			frappe.throw(_("You have already voted for this award."))
		raise

	frappe.db.sql(
		"UPDATE `tabNomination` SET vote_count = vote_count + 1 WHERE name=%s",
		(nomination.name,),
	)
	frappe.db.sql(
		"UPDATE `tabCampaign` SET total_votes = total_votes + 1 WHERE name=%s",
		(nomination.campaign,),
	)

	# Recompute percentage
	total = (
		frappe.db.sql(
			"SELECT COALESCE(SUM(vote_count),0) FROM `tabNomination` "
			"WHERE award=%s AND is_finalist=1 AND status='Submitted'",
			(nomination.award,),
		)[0][0]
		or 0
	)
	new_count = (nomination.vote_count or 0) + 1
	pct = round(new_count / total * 100, 1) if total else 0.0

	return {
		"vote_id": vote.name,
		"new_vote_count": new_count,
		"new_vote_percentage": pct,
		"thank_you_message": "Your vote is counted!",
	}


# ---------------------------------------------------------------------------
# 4.7 upload_nominee_photo (guest-safe image upload)
# ---------------------------------------------------------------------------

_ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MB


@frappe.whitelist(allow_guest=True)
@rate_limit(key="submitted_from_ip", limit=20, seconds=600)
def upload_nominee_photo():
	"""Accept a single image file from anonymous users for nomination photos.

	Returns ``{"file_url": "/files/..."}``. The uploaded File is public and
	unattached; it gets linked to a Nomination only after OTP verification.
	"""
	files = frappe.request.files
	if not files or "file" not in files:
		frappe.throw(_("No file uploaded."))

	f = files["file"]
	filename = (f.filename or "photo").rsplit("/", 1)[-1]
	content_type = (f.mimetype or "").lower()
	if content_type not in _ALLOWED_PHOTO_TYPES:
		frappe.throw(_("Only JPEG, PNG, WebP or GIF images are allowed."))

	content = f.read()
	if not content:
		frappe.throw(_("Uploaded file is empty."))
	if len(content) > _MAX_PHOTO_BYTES:
		frappe.throw(_("Image must be 5 MB or smaller."))

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 0,
			"folder": "Home",
		}
	).insert(ignore_permissions=True)
	return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}


# ---------------------------------------------------------------------------
# 4.8 get_nominee — public, single finalist details for the vote-detail view
# ---------------------------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def get_nominee(nomination_id: str):
	row = frappe.db.get_value(
		"Nomination",
		nomination_id,
		[
			"name",
			"campaign",
			"award",
			"nominee_name",
			"nominee_photo",
			"justification",
			"vote_count",
			"is_finalist",
			"status",
		],
		as_dict=True,
	)
	if not row or not row.is_finalist or row.status != "Submitted":
		frappe.local.response.http_status_code = 404
		frappe.throw(_("Nominee not found."))
	award = frappe.db.get_value(
		"Award", row.award, ["award_name", "slug", "icon_or_image"], as_dict=True
	)
	extra = frappe.db.get_value(
		"Nomination Finalist",
		{"nomination": row.name},
		["designation", "organization"],
		as_dict=True,
	) or {}
	row["designation"] = (extra.get("designation") or "").strip()
	row["organization"] = (extra.get("organization") or "").strip()
	return {"finalist": row, "award": award}


# ---------------------------------------------------------------------------
# 4.9 Admin / dashboard endpoints (login required)
# ---------------------------------------------------------------------------

def _require_manager():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	roles = set(frappe.get_roles(frappe.session.user))
	if not (roles & {"System Manager", "Nominations Manager"}):
		frappe.throw(_("Not permitted."), frappe.PermissionError)


@frappe.whitelist()
def get_award_voters(award: str, limit: int = 200):
	_require_manager()
	rows = frappe.get_all(
		"Vote",
		filters={"award": award},
		fields=[
			"name",
			"nomination",
			"business_name",
			"contact_person_name",
			"category",
			"voted_at",
			"voted_via",
		],
		order_by="voted_at DESC",
		limit=cint(limit) or 200,
	)
	nom_names = list({r.nomination for r in rows if r.nomination})
	nominees = {}
	if nom_names:
		for n in frappe.get_all(
			"Nomination",
			filters={"name": ("in", nom_names)},
			fields=["name", "nominee_name"],
		):
			nominees[n.name] = n.nominee_name
	for r in rows:
		r["nominee_name"] = nominees.get(r.nomination, "")
	total = frappe.db.count("Vote", {"award": award})
	return {"voters": rows, "total": total}


@frappe.whitelist()
def get_campaign_dashboard(campaign: str):
	_require_manager()
	camp = frappe.db.get_value(
		"Campaign",
		campaign,
		[
			"name",
			"title",
			"status",
			"total_nominations",
			"total_votes",
			"nomination_start",
			"nomination_end",
			"voting_start",
			"voting_end",
		],
		as_dict=True,
	)
	if not camp:
		frappe.throw(_("Campaign not found."))

	awards = frappe.get_all(
		"Award",
		filters={"campaign": campaign},
		fields=["name", "award_name", "slug", "sequence", "winner_nomination"],
		order_by="sequence ASC, award_name ASC",
	)
	for a in awards:
		a["total_votes"] = frappe.db.sql(
			"SELECT COALESCE(SUM(vote_count),0) FROM `tabNomination` "
			"WHERE award=%s AND is_finalist=1 AND status='Submitted'",
			(a.name,),
		)[0][0] or 0
		a["finalists"] = frappe.get_all(
			"Nomination",
			filters={"award": a.name, "is_finalist": 1, "status": "Submitted"},
			fields=["name", "nominee_name", "nominee_photo", "vote_count"],
			order_by="vote_count DESC, submitted_at ASC",
		)
		a["nomination_count"] = frappe.db.count("Nomination", {"award": a.name})

	# Category breakdown across the campaign
	cat_rows = frappe.db.sql(
		"""
		SELECT v.category, COUNT(*) AS c
		FROM `tabVote` v JOIN `tabNomination` n ON v.nomination = n.name
		WHERE n.campaign = %s
		GROUP BY v.category ORDER BY c DESC
		""",
		(campaign,),
		as_dict=True,
	)

	recent_votes = frappe.db.sql(
		"""
		SELECT v.business_name, v.contact_person_name, v.category, v.voted_at,
		       n.nominee_name, a.award_name
		FROM `tabVote` v
		JOIN `tabNomination` n ON v.nomination = n.name
		JOIN `tabAward` a ON v.award = a.name
		WHERE n.campaign = %s
		ORDER BY v.voted_at DESC LIMIT 25
		""",
		(campaign,),
		as_dict=True,
	)

	return {
		"campaign": camp,
		"awards": awards,
		"categories": cat_rows,
		"recent_votes": recent_votes,
	}


@frappe.whitelist()
def list_active_campaigns():
	_require_manager()
	return frappe.get_all(
		"Campaign",
		filters={"status": ("!=", "Draft")},
		fields=["name", "title", "status"],
		order_by="modified DESC",
	)


@frappe.whitelist()
def get_campaign_awards(campaign: str):
	"""List of awards for a campaign with quick stats — used by the Campaign Awards tab."""
	_require_manager()
	awards = frappe.get_all(
		"Award",
		filters={"campaign": campaign},
		fields=[
			"name",
			"award_name",
			"slug",
			"sequence",
			"icon_or_image",
			"winner_nomination",
			"total_finalists",
		],
		order_by="sequence ASC, award_name ASC",
	)
	for a in awards:
		a["nomination_count"] = frappe.db.count("Nomination", {"award": a.name})
		a["finalist_count"] = frappe.db.count(
			"Nomination", {"award": a.name, "is_finalist": 1, "status": "Submitted"}
		)
		a["vote_count"] = frappe.db.count("Vote", {"award": a.name})
	return awards


@frappe.whitelist()
def get_award_nominations(award: str, finalists_only: int = 0):
	"""All nominations for an award with finalist flag."""
	_require_manager()
	filters = {"award": award}
	if cint(finalists_only):
		filters["is_finalist"] = 1
	rows = frappe.get_all(
		"Nomination",
		filters=filters,
		fields=[
			"name",
			"nominee_name",
			"nominee_photo",
			"justification",
			"vote_count",
			"is_finalist",
			"status",
			"submitted_at",
		],
		order_by="is_finalist DESC, vote_count DESC, submitted_at DESC",
	)
	return {
		"nominations": rows,
		"total": frappe.db.count("Nomination", {"award": award}),
		"finalists": frappe.db.count(
			"Nomination", {"award": award, "is_finalist": 1, "status": "Submitted"}
		),
	}


@frappe.whitelist()
def set_nomination_finalist(nomination: str, value: int):
	"""Toggle the is_finalist flag on a Nomination."""
	_require_manager()
	if not frappe.db.exists("Nomination", nomination):
		frappe.throw(_("Nomination not found."))
	frappe.db.set_value("Nomination", nomination, "is_finalist", 1 if cint(value) else 0)
	return {"name": nomination, "is_finalist": 1 if cint(value) else 0}


@frappe.whitelist()
def get_award_votes_by_category(award: str):
	"""Vote totals grouped by Vote.category for one Award."""
	_require_manager()
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(NULLIF(TRIM(category), ''), '—') AS category, COUNT(*) AS c
		FROM `tabVote`
		WHERE award = %s
		GROUP BY category
		ORDER BY c DESC
		""",
		(award,),
		as_dict=True,
	)
	total = sum(r.c for r in rows) or 0
	return {"categories": rows, "total": total}


# ---------------------------------------------------------------------------
# Nomination Finalist — manager actions
# ---------------------------------------------------------------------------

@frappe.whitelist()
def regenerate_finalist_token(name: str):
	_require_manager()
	from nominations.nominations.doctype.nomination_finalist.nomination_finalist import (
		regenerate_token,
	)
	return {"public_url": regenerate_token(name)}


@frappe.whitelist()
def mark_finalist_sent(name: str):
	_require_manager()
	doc = frappe.get_doc("Nomination Finalist", name)
	doc.mark_sent()
	return {"status": doc.status, "sent_at": doc.sent_at}


@frappe.whitelist()
def mark_finalist_evaluated(name: str):
	_require_manager()
	doc = frappe.get_doc("Nomination Finalist", name)
	doc.mark_evaluated()
	return {"status": doc.status, "evaluated_at": doc.evaluated_at}


@frappe.whitelist()
def preview_finalist_push(name: str, selection: str | dict | None = None):
	"""Return a rendered preview of the Nomination payload for the push dialog."""
	_require_manager()
	if isinstance(selection, str) and selection.strip():
		try:
			selection = frappe.parse_json(selection)
		except Exception:
			selection = None
	doc = frappe.get_doc("Nomination Finalist", name)
	return doc.preview_push(selection=selection if isinstance(selection, dict) else None)


@frappe.whitelist()
def push_finalist_to_voting(name: str, selection: str | dict | None = None, justification: str | None = None):
	"""Create a `Nomination` (is_finalist=1) for this finalist so it appears in voting.

	``selection`` is an optional JSON string (or dict) describing which criteria
	rows and which nominee detail fields to copy into the resulting Nomination.
	See ``NominationFinalist.push_to_voting`` for the schema.

	``justification`` (HTML) is an optional manager-edited override used in
	place of the auto-built justification.
	"""
	_require_manager()
	if isinstance(selection, str) and selection.strip():
		try:
			selection = frappe.parse_json(selection)
		except Exception:
			selection = None
	doc = frappe.get_doc("Nomination Finalist", name)
	nomination_name = doc.push_to_voting(
		selection=selection if isinstance(selection, dict) else None,
		justification_override=justification or None,
	)
	return {"nomination": nomination_name}


@frappe.whitelist()
def mark_finalist_winner(name: str):
	"""Manually mark a finalist as the winner of its award."""
	_require_manager()
	doc = frappe.get_doc("Nomination Finalist", name)
	doc.mark_winner()
	return {
		"status": doc.status,
		"is_winner": doc.is_winner,
		"award": doc.award,
		"nomination": doc.nomination,
	}


@frappe.whitelist()
def unmark_finalist_winner(name: str):
	"""Reverse a previous winner marking."""
	_require_manager()
	doc = frappe.get_doc("Nomination Finalist", name)
	doc.unmark_winner()
	return {"status": doc.status, "is_winner": doc.is_winner}


# ---------------------------------------------------------------------------
# Nomination Finalist — public submission endpoints (token-gated, no login)
# ---------------------------------------------------------------------------

_ALLOWED_FINALIST_TYPES = {
	"image/jpeg", "image/png", "image/webp", "image/gif",
	"video/mp4", "video/webm", "video/quicktime",
	"application/pdf",
	"application/msword",
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	"application/vnd.ms-excel",
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	"application/vnd.ms-powerpoint",
	"application/vnd.openxmlformats-officedocument.presentationml.presentation",
	"text/plain",
}
_MAX_FINALIST_BYTES = 100 * 1024 * 1024  # 100 MB per file


def _classify_file_type(content_type: str) -> str:
	ct = (content_type or "").lower()
	if ct.startswith("image/"):
		return "Image"
	if ct.startswith("video/"):
		return "Video"
	if ct in (
		"application/pdf",
		"application/msword",
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		"application/vnd.ms-excel",
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		"application/vnd.ms-powerpoint",
		"application/vnd.openxmlformats-officedocument.presentationml.presentation",
		"text/plain",
	):
		return "Document"
	return "Other"


def _get_finalist_by_token(token: str):
	if not token:
		frappe.local.response.http_status_code = 404
		frappe.throw(_("Submission link is invalid."))
	name = frappe.db.get_value("Nomination Finalist", {"submission_token": token}, "name")
	if not name:
		frappe.local.response.http_status_code = 404
		frappe.throw(_("Submission link is invalid or has been revoked."))
	return frappe.get_doc("Nomination Finalist", name)


def _finalist_locked(status: str) -> bool:
	# Once the nominee submits, the public page becomes read-only.
	return status in ("Submitted", "Evaluated", "Winner", "Not Selected")


def _parse_files(raw: str | None) -> list[dict]:
	import json as _json
	if not raw:
		return []
	try:
		data = _json.loads(raw)
		return data if isinstance(data, list) else []
	except Exception:
		return []


def _dump_files(items: list[dict]) -> str:
	import json as _json
	return _json.dumps(items)


@frappe.whitelist(allow_guest=True)
def get_finalist_submission(token: str):
	"""Public read of the finalist submission form (criteria + existing responses)."""
	doc = _get_finalist_by_token(token)
	campaign = frappe.db.get_value(
		"Campaign", doc.campaign, ["title", "slug", "cover_image", "description"], as_dict=True
	) or frappe._dict()
	award = frappe.db.get_value(
		"Award", doc.award, ["award_name", "slug", "icon_or_image", "description"], as_dict=True
	) or frappe._dict()

	# NOTE: max_marks / marks_awarded / evaluator_comments are deliberately
	# omitted — the public submission page must not reveal evaluation weights.
	criteria = [
		{
			"name": row.name,
			"idx": row.idx,
			"criteria_name": row.criteria_name,
			"description": row.description,
			"response_text": row.response_text or "",
			"response_files": _parse_files(row.response_files),
		}
		for row in (doc.criteria or [])
	]
	return {
		"finalist": {
			"name": doc.name,
			"nominee_name": doc.nominee_name,
			"nominee_photo": doc.nominee_photo,
			"organization": doc.organization,
			"designation": doc.designation,
			"status": doc.status,
			"intro_message": doc.intro_message,
			"locked": _finalist_locked(doc.status),
		},
		"campaign": campaign,
		"award": award,
		"criteria": criteria,
		"settings": _public_settings(),
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="token", limit=60, seconds=600)
def save_finalist_submission(token: str, responses=None, submit: int = 0):
	"""Save nominee's responses against each criteria.

	``responses`` is a list of ``{criteria_row, response_text}``
	(also accepted as a JSON string for form-encoded clients). When ``submit`` is
	truthy, the finalist's status is moved to ``Submitted``.
	"""
	import json as _json

	doc = _get_finalist_by_token(token)
	if _finalist_locked(doc.status):
		frappe.throw(_("This submission has already been evaluated and can no longer be edited."))

	if isinstance(responses, str):
		try:
			responses = _json.loads(responses)
		except Exception:
			frappe.throw(_("Invalid responses payload."))
	responses = responses or []

	by_row = {r.name: r for r in (doc.criteria or [])}
	for entry in responses:
		row_name = (entry or {}).get("criteria_row")
		row = by_row.get(row_name)
		if not row:
			continue
		text = (entry.get("response_text") or "").strip()
		if len(text) > 20000:
			text = text[:20000]
		row.response_text = text

	if doc.status == "Draft":
		doc.status = "Sent"
	if doc.status in ("Sent", "In Progress"):
		doc.status = "In Progress"
	if cint(submit):
		doc.status = "Submitted"
		doc.submitted_at = now_datetime()

	doc.save(ignore_permissions=True)
	return {"status": doc.status, "submitted_at": doc.submitted_at}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="token", limit=60, seconds=600)
def upload_finalist_attachment(token: str, criteria_row: str, caption: str | None = None):
	"""Upload a single file and append it to the given criteria row's files list."""
	doc = _get_finalist_by_token(token)
	if _finalist_locked(doc.status):
		frappe.throw(_("This submission has already been evaluated and can no longer be edited."))

	row = next((r for r in (doc.criteria or []) if r.name == criteria_row), None)
	if not row:
		frappe.throw(_("Criteria row not found."))

	files = frappe.request.files
	if not files or "file" not in files:
		frappe.throw(_("No file uploaded."))
	f = files["file"]
	filename = (f.filename or "upload").rsplit("/", 1)[-1]
	content_type = (f.mimetype or "").lower()
	if content_type not in _ALLOWED_FINALIST_TYPES:
		frappe.throw(_("This file type is not allowed."))
	content = f.read()
	if not content:
		frappe.throw(_("Uploaded file is empty."))
	if len(content) > _MAX_FINALIST_BYTES:
		frappe.throw(_("File must be 100 MB or smaller."))

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"is_private": 0,
			"folder": "Home",
			"attached_to_doctype": "Nomination Finalist",
			"attached_to_name": doc.name,
		}
	).insert(ignore_permissions=True)

	entry = {
		"file_url": file_doc.file_url,
		"file_type": _classify_file_type(content_type),
		"caption": (caption or "").strip(),
	}
	items = _parse_files(row.response_files)
	items.append(entry)
	row.response_files = _dump_files(items)

	if doc.status == "Draft":
		doc.status = "Sent"
	if doc.status in ("Sent",):
		doc.status = "In Progress"
	doc.save(ignore_permissions=True)
	return {"file": entry, "files": items}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="token", limit=60, seconds=600)
def delete_finalist_attachment(token: str, criteria_row: str, file_url: str):
	doc = _get_finalist_by_token(token)
	if _finalist_locked(doc.status):
		frappe.throw(_("This submission has already been evaluated and can no longer be edited."))
	row = next((r for r in (doc.criteria or []) if r.name == criteria_row), None)
	if not row:
		frappe.throw(_("Criteria row not found."))
	items = _parse_files(row.response_files)
	new_items = [it for it in items if it.get("file_url") != file_url]
	if len(new_items) == len(items):
		frappe.throw(_("File not found."))
	row.response_files = _dump_files(new_items)
	doc.save(ignore_permissions=True)
	return {"files": new_items}

