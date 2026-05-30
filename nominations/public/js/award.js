frappe.ui.form.on("Award", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.public_voting_url) {
			frm.add_custom_button(__("Copy Award Voting Link"), () => {
				navigator.clipboard.writeText(frm.doc.public_voting_url);
				frappe.show_alert({ message: __("Copied"), indicator: "green" });
			});
		}

		const has_winner = !!frm.doc.winner_nomination;
		frm.add_custom_button(
			has_winner ? __("Change Winner") : __("Set Winner"),
			() => open_winner_picker(frm),
			__("Actions"),
		);
		if (has_winner) {
			frm.add_custom_button(__("Clear Winner"), () => {
				frappe.confirm(__("Remove the current winner for this award?"), () => {
					clear_award_winner(frm);
				});
			}, __("Actions"));
		}

		render_nominations_tab(frm);
		render_votes_tab(frm);
	},
});

// ---------------------------------------------------------------------------
// Winner picker — list all finalists with a radio to switch winner in 1 click
// ---------------------------------------------------------------------------

function open_winner_picker(frm) {
	frappe.db.get_list("Nomination Finalist", {
		filters: { award: frm.doc.name },
		fields: [
			"name", "nominee_name", "nominee_photo", "designation", "organization",
			"is_winner", "nomination", "status", "score_percentage",
			"total_marks_awarded", "total_max_marks",
		],
		order_by: "is_winner desc, score_percentage desc, nominee_name asc",
		limit: 200,
	}).then((rows) => {
		if (!rows || !rows.length) {
			frappe.msgprint(__("No finalists found for this award."));
			return;
		}
		const current = frm.doc.winner_nomination;
		const current_fin = (rows.find((r) => r.nomination && r.nomination === current) || {}).name || "";

		const list_html = rows.map((r) => {
			const photo = r.nominee_photo
				? `<img src="${frappe.utils.escape_html(r.nominee_photo)}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;flex-shrink:0;" />`
				: `<div style="width:40px;height:40px;border-radius:50%;background:var(--bg-light);display:flex;align-items:center;justify-content:center;color:var(--text-muted);flex-shrink:0;font-weight:600;">${(r.nominee_name || "?").charAt(0).toUpperCase()}</div>`;
			const meta_bits = [];
			if (r.designation) meta_bits.push(`<span style="color:#0f766e;font-weight:500;">${frappe.utils.escape_html(r.designation)}</span>`);
			if (r.organization) meta_bits.push(`<span style="color:var(--text-muted);">${frappe.utils.escape_html(r.organization)}</span>`);
			const score = r.total_max_marks
				? `<span style="font-size:12px;color:var(--text-muted);">${r.total_marks_awarded || 0} / ${r.total_max_marks} (${(r.score_percentage || 0).toFixed(1)}%)</span>`
				: "";
			const winner_pill = r.is_winner
				? `<span class="indicator-pill yellow" style="margin-left:6px;">${__("Current winner")}</span>` : "";
			return `
				<label style="display:flex;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;margin-bottom:8px;cursor:pointer;background:var(--card-bg,#fff);">
					<input type="radio" name="winner-pick" value="${frappe.utils.escape_html(r.name)}" ${r.name === current_fin ? "checked" : ""} style="margin-right:4px;" />
					${photo}
					<div style="flex:1;min-width:0;">
						<div style="font-weight:600;">${frappe.utils.escape_html(r.nominee_name || "")}${winner_pill}</div>
						<div style="font-size:12px;margin-top:2px;">${meta_bits.join(" • ")}</div>
					</div>
					${score}
				</label>
			`;
		}).join("");

		const d = new frappe.ui.Dialog({
			title: __("Set / Change Winner"),
			size: "large",
			fields: [
				{ fieldtype: "HTML", fieldname: "list", options: `<div style="max-height:60vh;overflow:auto;">${list_html}</div>` },
			],
			primary_action_label: __("Set as Winner"),
			primary_action() {
				const picked = d.$wrapper.find("input[name='winner-pick']:checked").val();
				if (!picked) {
					frappe.msgprint(__("Select a finalist first."));
					return;
				}
				frappe.call({
					method: "nominations.api.mark_finalist_winner",
					args: { name: picked },
					freeze: true,
					freeze_message: __("Updating winner…"),
					callback: () => {
						frappe.show_alert({ message: __("Winner updated."), indicator: "green" });
						d.hide();
						frm.reload_doc();
					},
				});
			},
		});
		d.show();
	});
}

function clear_award_winner(frm) {
	const current = frm.doc.winner_nomination;
	if (!current) return;
	frappe.db.get_value("Nomination Finalist",
		{ award: frm.doc.name, nomination: current },
		"name",
	).then((r) => {
		const fin = r && r.message && r.message.name;
		if (!fin) {
			// Fallback: clear the award field directly.
			frappe.db.set_value("Award", frm.doc.name, "winner_nomination", null)
				.then(() => frm.reload_doc());
			return;
		}
		frappe.call({
			method: "nominations.api.unmark_finalist_winner",
			args: { name: fin },
			callback: () => {
				frappe.show_alert({ message: __("Winner cleared."), indicator: "orange" });
				frm.reload_doc();
			},
		});
	});
}

// ---------------------------------------------------------------------------
// Nominations tab — list with favorite toggle + "favorites only" filter
// ---------------------------------------------------------------------------

function render_nominations_tab(frm) {
	const field = frm.fields_dict.nominations_html;
	if (!field) return;
	const $wrap = field.$wrapper.empty();
	const $container = $(`
		<div class="nom-nominations-tab">
			<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:10px;flex-wrap:wrap;">
				<div>
					<div style="font-weight:600;">${__("Nominations for this Award")}</div>
					<div class="nom-nom-summary" style="color:var(--text-muted);font-size:12px;"></div>
				</div>
				<div style="display:flex;align-items:center;gap:8px;">
					<label style="display:flex;align-items:center;gap:6px;font-size:12px;margin:0;cursor:pointer;">
						<input type="checkbox" class="nom-finalists-only" /> ${__("Show finalists only")}
					</label>
					<button class="btn btn-xs btn-default nom-nom-refresh">${__("Refresh")}</button>
				</div>
			</div>
			<div class="nom-nom-body"></div>
		</div>
	`).appendTo($wrap);

	const $body = $container.find(".nom-nom-body");
	const $summary = $container.find(".nom-nom-summary");
	const $only = $container.find(".nom-finalists-only");

	const load = () => {
		frappe.call({
			method: "nominations.api.get_award_nominations",
			args: {
				award: frm.doc.name,
				finalists_only: $only.is(":checked") ? 1 : 0,
			},
		}).then((r) => {
			if (!r || !r.message) return;
			const { nominations, total, finalists } = r.message;
			$summary.text(`${total} ${__("total")} · ${finalists} ${__("finalists")}`);
			$body.html(render_nominations_html(nominations));
			$body.find("[data-nomination]").on("click", function (e) {
				if ($(e.target).closest(".nom-fin-toggle").length) return;
				frappe.set_route("Form", "Nomination", $(this).data("nomination"));
			});
			$body.find(".nom-fin-toggle").on("click", function (e) {
				e.stopPropagation();
				const $btn = $(this);
				const name = $btn.data("nomination");
				const value = $btn.data("value") ? 0 : 1;
				frappe.call({
					method: "nominations.api.set_nomination_finalist",
					args: { nomination: name, value },
				}).then(() => load());
			});
		});
	};

	$only.on("change", load);
	$container.find(".nom-nom-refresh").on("click", load);
	load();

	const onEvt = (m) => { if (m && m.award === frm.doc.name) load(); };
	frappe.realtime.on("nominations:nomination", onEvt);
	frappe.realtime.on("nominations:vote", onEvt);
}

function render_nominations_html(rows) {
	if (!rows || !rows.length) {
		return `<div style="color:var(--text-muted);font-size:13px;padding:16px;border:1px dashed var(--border-color);border-radius:6px;">${__("No nominations.")}</div>`;
	}
	return rows.map((n) => {
		const photo = n.nominee_photo
			? `<img src="${frappe.utils.escape_html(n.nominee_photo)}" style="width:48px;height:48px;border-radius:50%;object-fit:cover;flex-shrink:0;" />`
			: `<div style="width:48px;height:48px;border-radius:50%;background:var(--bg-light);display:flex;align-items:center;justify-content:center;color:var(--text-muted);flex-shrink:0;">${(n.nominee_name || "?").charAt(0).toUpperCase()}</div>`;
		const status_badge = n.status === "Rejected"
			? `<span class="indicator-pill red" style="margin-left:6px;">${__("Rejected")}</span>` : "";
		const fin_active = !!n.is_finalist;
		const fin_color = fin_active ? "#2563eb" : "var(--text-muted)";
		const fin_label = fin_active ? __("Finalist") : __("Mark finalist");
		return `
			<div style="display:flex;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;margin-bottom:8px;cursor:pointer;background:var(--card-bg,#fff);" data-nomination="${frappe.utils.escape_html(n.name)}">
				${photo}
				<div style="flex:1;min-width:0;">
					<div style="font-weight:600;">${frappe.utils.escape_html(n.nominee_name || "")}${status_badge}</div>
					<div style="font-size:12px;color:var(--text-muted);margin-top:2px;">${frappe.utils.escape_html((n.justification || "").slice(0, 140))}${(n.justification || "").length > 140 ? "…" : ""}</div>
				</div>
				<div style="text-align:right;font-size:12px;color:var(--text-muted);">
					<div><b style="color:var(--text-color);font-size:14px;">${n.vote_count || 0}</b> ${__("votes")}</div>
				</div>
				<button class="btn btn-xs btn-default nom-fin-toggle" title="${fin_label}" data-nomination="${frappe.utils.escape_html(n.name)}" data-value="${fin_active ? 1 : 0}" style="border-color:${fin_color};color:${fin_color};">
					${fin_active ? __("✓ Finalist") : __("+ Finalist")}
				</button>
			</div>
		`;
	}).join("");
}

// ---------------------------------------------------------------------------
// Votes tab — category breakdown + voters list
// ---------------------------------------------------------------------------

function render_votes_tab(frm) {
	const field = frm.fields_dict.votes_html;
	if (!field) return;
	const $wrap = field.$wrapper.empty();
	const $container = $(`
		<div class="nom-votes-tab">
			<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
				<div>
					<div style="font-weight:600;">${__("Votes")}</div>
					<div class="nom-votes-summary" style="color:var(--text-muted);font-size:12px;"></div>
				</div>
				<button class="btn btn-xs btn-default nom-votes-refresh">${__("Refresh")}</button>
			</div>
			<div style="display:grid;grid-template-columns:1fr;gap:14px;">
				<div>
					<div style="font-weight:600;font-size:13px;margin-bottom:6px;">${__("Votes by Category")}</div>
					<div class="nom-votes-categories"></div>
				</div>
				<div>
					<div style="font-weight:600;font-size:13px;margin-bottom:6px;">${__("All Votes")}</div>
					<div class="nom-votes-list"></div>
				</div>
			</div>
		</div>
	`).appendTo($wrap);

	const $summary = $container.find(".nom-votes-summary");
	const $cats = $container.find(".nom-votes-categories");
	const $list = $container.find(".nom-votes-list");

	const load = () => {
		Promise.all([
			frappe.call({
				method: "nominations.api.get_award_votes_by_category",
				args: { award: frm.doc.name },
			}),
			frappe.call({
				method: "nominations.api.get_award_voters",
				args: { award: frm.doc.name, limit: 500 },
			}),
		]).then(([catR, votersR]) => {
			const catData = (catR && catR.message) || { categories: [], total: 0 };
			const votersData = (votersR && votersR.message) || { voters: [], total: 0 };
			$summary.text(`${votersData.total} ${__("total votes")} · ${catData.categories.length} ${__("categories")}`);
			$cats.html(render_category_bars(catData.categories, catData.total));
			$list.html(render_voters_table(votersData.voters));
			$list.find("[data-vote]").on("click", function () {
				frappe.set_route("Form", "Vote", $(this).data("vote"));
			});
		});
	};

	$container.find(".nom-votes-refresh").on("click", load);
	load();

	const onEvt = (m) => { if (m && m.award === frm.doc.name) load(); };
	frappe.realtime.on("nominations:vote", onEvt);
}

function render_category_bars(rows, total) {
	if (!rows || !rows.length) {
		return `<div style="color:var(--text-muted);font-size:13px;">${__("No votes yet.")}</div>`;
	}
	const denom = total || 1;
	return rows.map((r) => {
		const pct = Math.round((r.c / denom) * 100);
		return `
			<div style="margin-bottom:8px;">
				<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px;">
					<span>${frappe.utils.escape_html(r.category || "—")}</span>
					<span style="color:var(--text-muted);">${r.c} (${pct}%)</span>
				</div>
				<div style="height:6px;background:var(--bg-color,#f1f1f1);border-radius:3px;overflow:hidden;">
					<div style="height:100%;width:${pct}%;background:#6366f1;"></div>
				</div>
			</div>
		`;
	}).join("");
}

function render_voters_table(rows) {
	if (!rows || !rows.length) {
		return `<div style="color:var(--text-muted);font-size:13px;">${__("No votes yet.")}</div>`;
	}
	const head = `
		<tr style="background:var(--fg-color);">
			<th style="text-align:left;padding:6px 8px;">${__("When")}</th>
			<th style="text-align:left;padding:6px 8px;">${__("Contact")}</th>
			<th style="text-align:left;padding:6px 8px;">${__("Business")}</th>
			<th style="text-align:left;padding:6px 8px;">${__("Category")}</th>
			<th style="text-align:left;padding:6px 8px;">${__("Voted For")}</th>
		</tr>`;
	const body = rows.map((v) => `
		<tr data-vote="${frappe.utils.escape_html(v.name)}" style="cursor:pointer;border-top:1px solid var(--border-color);">
			<td style="padding:6px 8px;color:var(--text-muted);white-space:nowrap;">${frappe.datetime.comment_when(v.voted_at)}</td>
			<td style="padding:6px 8px;font-weight:500;">${frappe.utils.escape_html(v.contact_person_name || "")}</td>
			<td style="padding:6px 8px;">${frappe.utils.escape_html(v.business_name || "")}</td>
			<td style="padding:6px 8px;">${frappe.utils.escape_html(v.category || "")}</td>
			<td style="padding:6px 8px;">${frappe.utils.escape_html(v.nominee_name || "")}</td>
		</tr>
	`).join("");
	return `<div style="overflow:auto;max-height:480px;border:1px solid var(--border-color);border-radius:6px;">
		<table style="width:100%;font-size:13px;border-collapse:collapse;">${head}${body}</table>
	</div>`;
}
