frappe.pages["nominations-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Nominations Dashboard"),
		single_column: true,
	});

	const state = { campaign: null, data: null };

	const $campaign_field = page.add_field({
		fieldname: "campaign",
		fieldtype: "Link",
		label: __("Campaign"),
		options: "Campaign",
		change() {
			const v = $campaign_field.get_value();
			if (v && v !== state.campaign) {
				state.campaign = v;
				update_route();
				load();
			}
		},
	});

	page.set_secondary_action(__("Refresh"), () => load(), "refresh");

	const $container = $(`
		<div class="nom-dash" style="padding:8px 0;">
			<div class="nom-dash-empty" style="padding:40px;text-align:center;color:var(--text-muted);">
				${__("Select a campaign to see live results.")}
			</div>
			<div class="nom-dash-body" style="display:none;"></div>
		</div>
	`).appendTo(page.main);

	const $empty = $container.find(".nom-dash-empty");
	const $body = $container.find(".nom-dash-body");

	function update_route() {
		frappe.route_options = { campaign: state.campaign };
		frappe.router.push_state(`/app/nominations-dashboard?campaign=${encodeURIComponent(state.campaign || "")}`);
	}

	function load() {
		if (!state.campaign) return;
		frappe.call({
			method: "nominations.api.get_campaign_dashboard",
			args: { campaign: state.campaign },
		}).then((r) => {
			if (!r || !r.message) return;
			state.data = r.message;
			$empty.hide();
			$body.show().html(render(state.data));
			$body.find("[data-award]").on("click", function () {
				frappe.set_route("Form", "Award", $(this).data("award"));
			});
		});
	}

	function render(d) {
		const c = d.campaign;
		const aw = d.awards || [];
		const totalFinalists = aw.reduce((s, a) => s + ((a.finalists || []).length), 0);
		const stats = `
			<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px;">
				${stat_card(__("Status"), c.status)}
				${stat_card(__("Awards"), aw.length)}
				${stat_card(__("Nominations"), c.total_nominations || 0)}
				${stat_card(__("Finalists"), totalFinalists)}
				${stat_card(__("Votes"), c.total_votes || 0)}
			</div>
		`;
		const awards = (d.awards || []).map(render_award).join("");
		const categories = render_categories(d.categories || []);
		const recent = render_recent(d.recent_votes || []);
		return `
			${stats}
			<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;">
				<div>
					<h4 style="margin:0 0 8px;">${__("Awards")}</h4>
					${awards || `<div style="color:var(--text-muted);">${__("No awards.")}</div>`}
				</div>
				<div>
					<h4 style="margin:0 0 8px;">${__("Votes by Category")}</h4>
					${categories}
					<h4 style="margin:16px 0 8px;">${__("Recent Votes")}</h4>
					${recent}
				</div>
			</div>
		`;
	}

	function stat_card(label, value) {
		return `
			<div style="padding:12px;border:1px solid var(--border-color);border-radius:8px;background:var(--card-bg,#fff);">
				<div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;">${frappe.utils.escape_html(label)}</div>
				<div style="font-weight:600;font-size:18px;margin-top:2px;">${frappe.utils.escape_html(String(value))}</div>
			</div>
		`;
	}

	function render_award(a) {
		const finalists = (a.finalists || []);
		const total = a.total_votes || 0;
		const bars = finalists.map((f) => {
			const pct = total ? Math.round((f.vote_count || 0) / total * 100) : 0;
			const winner_badge = a.winner_nomination === f.name
				? `<span class="indicator-pill orange" style="margin-left:6px;">${__("Winner")}</span>` : "";
			return `
				<div style="margin-top:8px;">
					<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
						<span>${frappe.utils.escape_html(f.nominee_name)}${winner_badge}</span>
						<span style="color:var(--text-muted);">${f.vote_count || 0} (${pct}%)</span>
					</div>
					<div style="height:6px;background:var(--bg-color, #f1f1f1);border-radius:3px;overflow:hidden;">
						<div style="height:100%;width:${pct}%;background:var(--primary, #1f4e79);"></div>
					</div>
				</div>
			`;
		}).join("");
		return `
			<div style="padding:12px;border:1px solid var(--border-color);border-radius:8px;margin-bottom:10px;background:var(--card-bg,#fff);">
				<div style="display:flex;justify-content:space-between;align-items:center;cursor:pointer;" data-award="${frappe.utils.escape_html(a.name)}">
					<div style="font-weight:600;">${frappe.utils.escape_html(a.award_name)}</div>
					<div style="font-size:12px;color:var(--text-muted);">
						${a.nomination_count || 0} ${__("noms")} ·
						${finalists.length} ${__("finalists")} ·
						${total} ${__("votes")}
					</div>
				</div>
				${bars || `<div style="color:var(--text-muted);font-size:12px;margin-top:6px;">${__("No finalists yet.")}</div>`}
			</div>
		`;
	}

	function render_categories(rows) {
		if (!rows.length) {
			return `<div style="color:var(--text-muted);font-size:13px;">${__("No votes yet.")}</div>`;
		}
		const total = rows.reduce((s, r) => s + r.c, 0) || 1;
		return rows.map((r) => {
			const pct = Math.round(r.c / total * 100);
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

	function render_recent(rows) {
		if (!rows.length) {
			return `<div style="color:var(--text-muted);font-size:13px;">${__("No votes yet.")}</div>`;
		}
		return `<div style="max-height:320px;overflow:auto;border:1px solid var(--border-color);border-radius:6px;">
			${rows.map((v) => `
				<div style="padding:8px 10px;border-bottom:1px solid var(--border-color);font-size:12px;">
					<div style="display:flex;justify-content:space-between;">
						<span style="font-weight:600;">${frappe.utils.escape_html(v.contact_person_name || "")}</span>
						<span style="color:var(--text-muted);">${frappe.datetime.comment_when(v.voted_at)}</span>
					</div>
					<div style="color:var(--text-muted);">${frappe.utils.escape_html(v.business_name || "")} · ${frappe.utils.escape_html(v.category || "")}</div>
					<div style="color:var(--text-muted);">${__("voted for")} <b>${frappe.utils.escape_html(v.nominee_name)}</b> — ${frappe.utils.escape_html(v.award_name)}</div>
				</div>
			`).join("")}
		</div>`;
	}

	// initial population
	frappe.call({ method: "nominations.api.list_active_campaigns" }).then((r) => {
		const list = (r && r.message) || [];
		const route_camp = frappe.route_options && frappe.route_options.campaign;
		const initial = route_camp || (list[0] && list[0].name);
		if (initial) {
			$campaign_field.set_value(initial);
		}
	});

	// realtime subscriptions
	const onEvent = (m) => { if (m && m.campaign === state.campaign) load(); };
	frappe.realtime.on("nominations:vote", onEvent);
	frappe.realtime.on("nominations:nomination", onEvent);
};
