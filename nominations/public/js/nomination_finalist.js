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
					open_push_to_voting_dialog(frm);
				}, __("Actions"))
				.removeClass("btn-default")
				.addClass("btn-primary");
		} else {
			frm.add_custom_button(__("Open Voting Nomination"), () => {
				frappe.set_route("Form", "Nomination", frm.doc.nomination);
			}, __("Actions"));

			if (!frm.doc.is_winner) {
				frm.add_custom_button(__("Mark as Winner"), () => {
					frappe.confirm(
						__("Mark this finalist as the winner of {0}? Any existing winner for this award will be replaced.", [frm.doc.award]),
						() => {
							frappe.call({
								method: "nominations.api.mark_finalist_winner",
								args: { name: frm.doc.name },
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
						args: { name: frm.doc.name },
						callback: () => frm.reload_doc(),
					});
				}, __("Actions"));
			}
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

function open_push_to_voting_dialog(frm) {
	const rows = (frm.doc.criteria || []).filter((r) => (r.response_text || "").trim());
	if (!rows.length) {
		frappe.msgprint({
			title: __("Nothing to push"),
			message: __("This finalist has no answered criteria yet."),
			indicator: "orange",
		});
		return;
	}

	// Build one Check field per criteria row, default checked.
	const criteria_fields = rows.map((row) => ({
		fieldtype: "Check",
		fieldname: `crit__${row.name}`,
		label: row.criteria_name || row.name,
		default: 1,
		description: (row.response_text || "").slice(0, 140) + ((row.response_text || "").length > 140 ? "…" : ""),
	}));

	const dialog = new frappe.ui.Dialog({
		title: __("Push to Voting — Select what to include"),
		size: "large",
		fields: [
			{
				fieldtype: "Section Break",
				label: __("Nominee Details"),
			},
			{
				fieldtype: "Check",
				fieldname: "include_photo",
				label: __("Include Photo"),
				default: frm.doc.nominee_photo ? 1 : 0,
				read_only: frm.doc.nominee_photo ? 0 : 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Check",
				fieldname: "include_designation",
				label: __("Include Designation"),
				default: (frm.doc.designation || "").trim() ? 1 : 0,
				read_only: (frm.doc.designation || "").trim() ? 0 : 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Check",
				fieldname: "include_organization",
				label: __("Include Organization"),
				default: (frm.doc.organization || "").trim() ? 1 : 0,
				read_only: (frm.doc.organization || "").trim() ? 0 : 1,
			},
			{
				fieldtype: "Section Break",
				label: __("Criteria Responses"),
				description: __("Pick the criteria responses to combine into the public justification."),
			},
			{
				fieldtype: "Check",
				fieldname: "include_intro",
				label: __("Include intro message"),
				default: (frm.doc.intro_message || "").trim() ? 1 : 0,
				read_only: (frm.doc.intro_message || "").trim() ? 0 : 1,
			},
			...criteria_fields,
			{
				fieldtype: "Section Break",
				label: __("Preview & Edit"),
				description: __("Edit the justification below if needed. This is exactly what voters will see."),
			},
			{
				fieldtype: "HTML",
				fieldname: "photo_preview",
			},
			{
				fieldtype: "Text Editor",
				fieldname: "justification",
				label: __("Justification (editable)"),
			},
			{
				fieldtype: "Button",
				fieldname: "regenerate",
				label: __("Regenerate from selection"),
			},
		],
		primary_action_label: __("Push to Voting"),
		primary_action(values) {
			const selection = collect_selection(values, rows);
			if (!selection.criteria.length) {
				frappe.msgprint({
					title: __("Select at least one criterion"),
					message: __("Please tick at least one criterion to include."),
					indicator: "orange",
				});
				return;
			}
			const justification = (values.justification || "").trim();
			if (!justification) {
				frappe.msgprint({
					title: __("Justification required"),
					message: __("Please add or regenerate the justification before pushing."),
					indicator: "orange",
				});
				return;
			}
			frappe.call({
				method: "nominations.api.push_finalist_to_voting",
				args: {
					name: frm.doc.name,
					selection: JSON.stringify(selection),
					justification: justification,
				},
				freeze: true,
				freeze_message: __("Creating Nomination…"),
				callback: (r) => {
					if (r.message && r.message.nomination) {
						frappe.show_alert({
							message: __("Nomination {0} created.", [r.message.nomination]),
							indicator: "green",
						});
					}
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});

	const photo_wrap = dialog.get_field("photo_preview").$wrapper;
	let user_edited = false;

	function render_photo(values) {
		const has_photo = !!values.include_photo && !!frm.doc.nominee_photo;
		const img = has_photo
			? `<img src="${frappe.utils.escape_html(frm.doc.nominee_photo)}" alt="" style="width:80px;height:80px;object-fit:cover;border-radius:8px;border:1px solid var(--border-color);flex-shrink:0;">`
			: `<div style="width:80px;height:80px;border-radius:8px;background:var(--bg-light-gray);display:flex;align-items:center;justify-content:center;color:var(--text-muted);flex-shrink:0;">${frappe.utils.icon("camera", "md")}</div>`;
		photo_wrap.html(`
			<div style="display:flex;gap:12px;align-items:center;padding:10px;border:1px solid var(--border-color);border-radius:8px;background:var(--bg-color);margin-bottom:8px;">
				${img}
				<div>
					<div style="font-weight:600">${frappe.utils.escape_html(frm.doc.nominee_name || "")}</div>
					<div class="text-muted small">${has_photo ? __("Photo will be shown to voters.") : __("No photo will be shown.")}</div>
				</div>
			</div>
		`);
	}

	function regenerate_justification(force) {
		if (user_edited && !force) return;
		const values = dialog.get_values(true) || {};
		const selection = collect_selection(values, rows);
		frappe.call({
			method: "nominations.api.preview_finalist_push",
			args: { name: frm.doc.name, selection: JSON.stringify(selection) },
			callback: (r) => {
				const m = r.message || {};
				dialog.set_value("justification", m.justification || "");
				user_edited = false;
			},
		});
	}

	function refresh_all() {
		const values = dialog.get_values(true) || {};
		render_photo(values);
		regenerate_justification(false);
	}

	const debounced_refresh = frappe.utils.debounce(refresh_all, 250);

	// Hook every selection checkbox to refresh photo + (maybe) justification.
	const watched = ["include_photo", "include_designation", "include_organization", "include_intro", ...rows.map((r) => `crit__${r.name}`)];
	watched.forEach((fn) => {
		const f = dialog.get_field(fn);
		if (f && f.df) f.df.onchange = debounced_refresh;
	});

	// Detect manual edits to the justification so we don't clobber them on
	// the next selection change.
	const just_field = dialog.get_field("justification");
	if (just_field && just_field.df) {
		just_field.df.onchange = () => { user_edited = true; };
	}

	// "Regenerate from selection" button — force overwrite of any edits.
	const regen_btn = dialog.get_field("regenerate");
	if (regen_btn) {
		regen_btn.$input.on("click", () => {
			if (user_edited) {
				frappe.confirm(
					__("Discard your edits and regenerate from current selection?"),
					() => regenerate_justification(true)
				);
			} else {
				regenerate_justification(true);
			}
		});
	}

	dialog.show();
	refresh_all();
}

function collect_selection(values, rows) {
	const chosen = rows.map((r) => r.name).filter((n) => values[`crit__${n}`]);
	return {
		criteria: chosen,
		include_photo: !!values.include_photo,
		include_designation: !!values.include_designation,
		include_organization: !!values.include_organization,
		include_intro: !!values.include_intro,
	};
}

