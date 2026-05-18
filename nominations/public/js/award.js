frappe.ui.form.on("Award", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.public_voting_url) {
			frm.add_custom_button(__("Copy Award Voting Link"), () => {
				navigator.clipboard.writeText(frm.doc.public_voting_url);
				frappe.show_alert({ message: __("Copied"), indicator: "green" });
			});
		}
	},
});
