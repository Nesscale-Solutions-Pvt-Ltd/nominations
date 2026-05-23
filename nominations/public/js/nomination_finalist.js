// Desk UI for Nomination Finalist.
frappe.ui.form.on("Nomination Finalist", {
	refresh(frm) {
		render_summary(frm);

		if (frm.is_new()) return;

		if (frm.doc.public_url) {
			frm.add_custom_button(__("Copy Public URL"), () => {
				navigator.clipboard.writeText(frm.doc.public_url);
				frappe.show_alert({ message: __("Public URL copied"), indicator: "green" });
			});
			frm.add_custom_button(__("Open Public Page"), () => {
				window.open(frm.doc.public_url, "_blank");
			});
			frm.add_custom_button(__("Regenerate Token"), () => {
				frappe.confirm(
					__("This will invalidate the existing public URL. Continue?"),
					() => {
						frappe.call({
							method: "nominations.api.regenerate_finalist_token",
							args: { name: frm.doc.name },
							callback: () => frm.reload_doc(),
						});
					}
				);
			}, __("Actions"));
		}

		if (["Draft", "Sent", "In Progress"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Mark as Sent"), () => {
				frappe.call({
					method: "nominations.api.mark_finalist_sent",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc(),
				});
			}, __("Actions"));
		}
		if (frm.doc.status === "Submitted") {
			frm.add_custom_button(__("Mark as Evaluated"), () => {
				frappe.call({
					method: "nominations.api.mark_finalist_evaluated",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc(),
				});
			}, __("Actions"));
		}

		// Push to voting — creates a Nomination record (is_finalist=1) for the
		// public voting flow. Disabled if already pushed.
		if (!frm.doc.nomination) {
			frm
				.add_custom_button(__("Push to Voting"), () => {
					frappe.confirm(
						__("Create a Nomination from this finalist so it appears in the public voting flow?"),
						() => {
							frappe.call({
								method: "nominations.api.push_finalist_to_voting",
								args: { name: frm.doc.name },
								callback: (r) => {
									if (r.message && r.message.nomination) {
										frappe.show_alert({
											message: __("Nomination {0} created.", [r.message.nomination]),
											indicator: "green",
										});
									}
									frm.reload_doc();
								},
							});
						}
					);
				}, __("Actions"))
				.removeClass("btn-default")
				.addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Open Voting Nomination"), () => {
				frappe.set_route("Form", "Nomination", frm.doc.nomination);
			}, __("Actions"));
		}
	},

	criteria_on_form_rendered(frm) {
		render_summary(frm);
	},
});

function render_summary(frm) {
	const wrap = frm.fields_dict.submission_summary?.$wrapper;
	if (!wrap) return;
	const rows = frm.doc.criteria || [];
	if (!rows.length) {
		wrap.html('<div class="text-muted small">No criteria yet.</div>');
		return;
	}
	const html = rows
		.map((row) => {
			let files = [];
			try { files = JSON.parse(row.response_files || "[]"); } catch (_) { files = []; }
			const fileList = files
				.map((f) => {
					const icon = f.file_type === "Image" ? "image"
						: f.file_type === "Video" ? "video"
						: "file";
					const nameFromUrl = (f.file_url || "").split("/").pop();
					const caption = f.caption ? ` — <span class="text-muted">${frappe.utils.escape_html(f.caption)}</span>` : "";
					return `<li class="mb-1"><a href="${frappe.utils.escape_html(f.file_url)}" target="_blank" rel="noopener">${frappe.utils.icon(icon, "xs")} ${frappe.utils.escape_html(nameFromUrl)}</a>${caption}</li>`;
				})
				.join("");
			const text = row.response_text ? `<div class="mt-2" style="white-space:pre-wrap">${frappe.utils.escape_html(row.response_text)}</div>` : '<div class="text-muted small mt-2">No text response.</div>';
			const filesBlock = files.length
				? `<ul class="mt-2 mb-0 pl-3">${fileList}</ul>`
				: '<div class="text-muted small mt-2">No files.</div>';
			return `
				<div class="border rounded p-3 mb-3">
					<div class="d-flex justify-content-between">
						<strong>${frappe.utils.escape_html(row.criteria_name || "")}</strong>
						<span class="text-muted small">${row.marks_awarded || 0}/${row.max_marks || 0}</span>
					</div>
					${text}
					${filesBlock}
				</div>`;
		})
		.join("");
	wrap.html(html);
}

