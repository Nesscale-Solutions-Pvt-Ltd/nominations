// Copyright (c) 2026, Nominations
// For license information, please see license.txt

frappe.ui.form.on("Campaign", {
	refresh(frm) {
		if (frm.is_new()) return;

		const reopen_targets = {
			"Nominations Open": ["Draft"],
			"Shortlisting": ["Nominations Open"],
			"Voting Open": ["Shortlisting", "Nominations Open"],
			"Closed": ["Voting Open", "Shortlisting", "Nominations Open"],
		};

		const targets = reopen_targets[frm.doc.status] || [];
		const roles = frappe.user_roles || [];
		const can_reopen =
			roles.includes("Nominations Manager") || roles.includes("System Manager");

		if (!targets.length || !can_reopen) return;

		targets.forEach((target) => {
			frm.add_custom_button(
				target,
				() => {
					frappe.confirm(
						__("Reopen this campaign and move it back to {0}?", [target]),
						() => {
							frm.call("reopen", { target_status: target }).then((r) => {
								if (!r.exc) {
									frappe.show_alert({
										message: __("Campaign reopened to {0}", [target]),
										indicator: "green",
									});
									frm.reload_doc();
								}
							});
						}
					);
				},
				__("Reopen")
			);
		});
	},
});
