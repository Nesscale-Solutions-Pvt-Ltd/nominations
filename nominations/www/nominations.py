import frappe

no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	# Exposed on window.* by frappe-ui's jinjaBootData plugin in the built HTML.
	context.boot = {
		"csrf_token": csrf_token,
		"site_name": frappe.local.site,
	}
	return context
