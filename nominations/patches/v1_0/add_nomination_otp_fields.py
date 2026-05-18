"""Add purpose/campaign/award/award_slug Custom Fields to the Nomination OTP
DocType so verify_otp can read flow context directly from the doc instead of
relying on a Redis cache entry.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if not frappe.db.exists("DocType", "Nomination OTP"):
		return

	create_custom_fields(
		{
			"Nomination OTP": [
				{
					"fieldname": "purpose",
					"label": "Purpose",
					"fieldtype": "Select",
					"options": "\nnominate\nvote",
					"insert_after": "otp",
				},
				{
					"fieldname": "campaign",
					"label": "Campaign",
					"fieldtype": "Link",
					"options": "Campaign",
					"insert_after": "purpose",
				},
				{
					"fieldname": "award",
					"label": "Award",
					"fieldtype": "Link",
					"options": "Award",
					"insert_after": "campaign",
				},
				{
					"fieldname": "award_slug",
					"label": "Award Slug",
					"fieldtype": "Data",
					"insert_after": "award",
				},
			]
		},
		update=True,
	)
