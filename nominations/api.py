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
		total = sum(f.vote_count or 0 for f in finalists) or 0
		for f in finalists:
			pct = round((f.vote_count or 0) / total * 100, 1) if total else 0.0
			out["finalists"].append(
				{
					"name": f.name,
					"nominee_name": f.nominee_name,
					"nominee_photo": f.nominee_photo,
					"justification": f.justification,
					"vote_count": f.vote_count or 0,
					"vote_percentage": pct,
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

@frappe.whitelist(allow_guest=True)
@rate_limit(key="verification_token", limit=3, seconds=600)
def submit_vote(
	verification_token: str,
	nomination_id: str,
	business_name: str,
	contact_person_name: str,
	via: str = "campaign",
):
	payload = security.verify_token(verification_token)
	if payload.get("purpose") != "vote":
		frappe.throw(_("Verification token is for a different action."))

	business_name = (business_name or "").strip()
	contact_person_name = (contact_person_name or "").strip()
	if not business_name:
		frappe.throw(_("Business name is required."))
	if not contact_person_name:
		frappe.throw(_("Contact person name is required."))

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
