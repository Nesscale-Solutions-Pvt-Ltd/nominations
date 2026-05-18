"""Install / post-install hooks."""
import secrets

import frappe


def after_install():
	# Role used in DocType permissions
	if not frappe.db.exists("Role", "Nominations Manager"):
		frappe.get_doc(
			{"doctype": "Role", "role_name": "Nominations Manager", "desk_access": 1}
		).insert(ignore_permissions=True)

	settings = frappe.get_doc("Nominations Settings")
	if not settings.site_salt:
		settings.site_salt = secrets.token_hex(32)
	if not settings.public_brand_name:
		settings.public_brand_name = "Nominations"
	settings.save(ignore_permissions=True)
	frappe.db.commit()
