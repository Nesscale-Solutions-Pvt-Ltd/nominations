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
