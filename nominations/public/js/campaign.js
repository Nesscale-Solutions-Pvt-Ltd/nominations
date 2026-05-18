frappe.ui.form.on("Campaign", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Copy Nomination Link"), () => {
				navigator.clipboard.writeText(frm.doc.nomination_public_url || "");
				frappe.show_alert({ message: __("Copied"), indicator: "green" });
			});
			frm.add_custom_button(__("Copy Voting Link"), () => {
				navigator.clipboard.writeText(frm.doc.voting_public_url || "");
				frappe.show_alert({ message: __("Copied"), indicator: "green" });
			});

			const transitions = {
				"Draft": ["Nominations Open", "Open Nominations"],
				"Nominations Open": ["Shortlisting", "Close Nominations"],
				"Shortlisting": ["Voting Open", "Open Voting"],
				"Voting Open": ["Closed", "Close Voting"],
			};
			const t = transitions[frm.doc.status];
			if (t) {
				const [next, label] = t;
				frm.add_custom_button(__(label), () => {
					frappe.confirm(__("Move campaign to '{0}'?", [next]), () => {
						frm.call("transition_to", { new_status: next }).then(() => frm.reload_doc());
					});
				}, __("Actions"));
			}

			frm.add_custom_button(__("Clone Campaign"), () => {
				frm.call("clone_campaign").then((r) => {
					if (r.message) frappe.set_route("Form", "Campaign", r.message);
				});
			}, __("Actions"));
		}
	},
});
