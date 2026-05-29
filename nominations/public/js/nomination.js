frappe.listview_settings["Nomination"] = {
	add_fields: ["is_finalist", "vote_count", "award", "status"],
	get_indicator(doc) {
		if (doc.status === "Rejected") return [__("Rejected"), "red", "status,=,Rejected"];
		if (doc.is_finalist) return [__("Finalist"), "green", "is_finalist,=,1"];
		return [__("Submitted"), "blue", "status,=,Submitted"];
	},
	onload(listview) {
		listview.page.add_action_item(__("Mark as Finalist"), () => {
			const items = listview.get_checked_items();
			frappe.call({
				method: "frappe.client.set_value",
				args: {},
			});
			Promise.all(
				items.map((d) =>
					frappe.db.set_value("Nomination", d.name, "is_finalist", 1)
				)
			).then(() => {
				frappe.show_alert({ message: __("Marked as finalist"), indicator: "green" });
				listview.refresh();
			});
		});
		listview.page.add_action_item(__("Remove from Finalist"), () => {
			const items = listview.get_checked_items();
			Promise.all(
				items.map((d) =>
					frappe.db.set_value("Nomination", d.name, "is_finalist", 0)
				)
			).then(() => listview.refresh());
		});
		listview.page.add_action_item(__("Reject as Spam"), () => {
			const items = listview.get_checked_items();
			Promise.all(
				items.map((d) =>
					frappe.db.set_value("Nomination", d.name, "status", "Rejected")
				)
			).then(() => listview.refresh());
		});
	},
};

frappe.ui.form.on("Nomination", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.award) return;

		// Find the linked Nomination Finalist (if any) so we can mark/unmark winner.
		frappe.db.get_value(
			"Nomination Finalist",
			{ nomination: frm.doc.name },
			["name", "is_winner"]
		).then((r) => {
			const fin = r && r.message;
			if (!fin || !fin.name) return;

			if (!fin.is_winner) {
				frm.add_custom_button(__("Mark as Winner"), () => {
					frappe.confirm(
						__("Mark {0} as the winner of {1}? Any existing winner will be replaced.",
							[frm.doc.nominee_name || frm.doc.name, frm.doc.award]),
						() => {
							frappe.call({
								method: "nominations.api.mark_finalist_winner",
								args: { name: fin.name },
								callback: () => {
									frappe.show_alert({ message: __("Winner marked."), indicator: "green" });
									frm.reload_doc();
								},
							});
						}
					);
				}, __("Actions"));
			} else {
				frm.add_custom_button(__("Unmark Winner"), () => {
					frappe.call({
						method: "nominations.api.unmark_finalist_winner",
						args: { name: fin.name },
						callback: () => {
							frappe.show_alert({ message: __("Winner unmarked."), indicator: "orange" });
							frm.reload_doc();
						},
					});
				}, __("Actions"));
			}

			frm.add_custom_button(__("Open Nomination Finalist"), () => {
				frappe.set_route("Form", "Nomination Finalist", fin.name);
			}, __("Actions"));
		});
	},
});
