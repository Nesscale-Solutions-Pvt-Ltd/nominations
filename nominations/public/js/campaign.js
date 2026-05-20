frappe.ui.form.on("Campaign", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Copy Nomination Link"), () => {
			navigator.clipboard.writeText(frm.doc.nomination_public_url || "");
			frappe.show_alert({ message: __("Copied"), indicator: "green" });
		});
		frm.add_custom_button(__("Copy Voting Link"), () => {
			navigator.clipboard.writeText(frm.doc.voting_public_url || "");
			frappe.show_alert({ message: __("Copied"), indicator: "green" });
		});

		frm.add_custom_button(__("Open Live Dashboard"), () => {
			window.location.href = `/app/nominations-dashboard?campaign=${encodeURIComponent(frm.doc.name)}`;
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

		render_awards_tab(frm);
	},
});

function render_awards_tab(frm) {
	const field = frm.fields_dict.awards_html;
	if (!field) return;
	const $wrap = field.$wrapper.empty();
	const $container = $(`<div class="nom-awards-tab"></div>`).appendTo($wrap);

	const load = () => {
		frappe.call({
			method: "nominations.api.get_campaign_awards",
			args: { campaign: frm.doc.name },
		}).then((r) => {
			const awards = (r && r.message) || [];
			$container.html(render_awards_html(awards));
			$container.find("[data-award]").on("click", function (e) {
				if ($(e.target).closest("a").length) return;
				frappe.set_route("Form", "Award", $(this).data("award"));
			});
		});
	};
	load();

	const onEvt = (m) => { if (m && m.campaign === frm.doc.name) load(); };
	frappe.realtime.on("nominations:vote", onEvt);
	frappe.realtime.on("nominations:nomination", onEvt);
}

function render_awards_html(awards) {
	const header = `
		<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
			<div>
				<div style="font-weight:600;font-size:14px;">${__("Awards in this Campaign")}</div>
				<div style="color:var(--text-muted);font-size:12px;">${awards.length} ${__("awards")}</div>
			</div>
		</div>
	`;
	if (!awards.length) {
		return header + `<div style="color:var(--text-muted);font-size:13px;padding:16px;border:1px dashed var(--border-color);border-radius:6px;">${__("No awards yet. Create one via the Award doctype.")}</div>`;
	}
	const cards = awards.map((a) => {
		const img = a.icon_or_image
			? `<img src="${frappe.utils.escape_html(a.icon_or_image)}" style="width:64px;height:64px;border-radius:6px;object-fit:cover;flex-shrink:0;background:var(--bg-light);" />`
			: `<div style="width:64px;height:64px;border-radius:6px;background:var(--bg-light);display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:11px;flex-shrink:0;">${__("No image")}</div>`;
		const winner = a.winner_nomination
			? `<span class="indicator-pill orange" style="margin-left:6px;">${__("Winner picked")}</span>` : "";
		return `
			<div style="display:flex;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;margin-bottom:8px;cursor:pointer;background:var(--card-bg,#fff);" data-award="${frappe.utils.escape_html(a.name)}">
				${img}
				<div style="flex:1;min-width:0;">
					<div style="font-weight:600;">${frappe.utils.escape_html(a.award_name)}${winner}</div>
					<div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
						${a.nomination_count || 0} ${__("nominations")} ·
						${a.finalist_count || 0} ${__("finalists")} ·
						${a.vote_count || 0} ${__("votes")}
					</div>
				</div>
				<a href="/app/award/${encodeURIComponent(a.name)}" class="btn btn-xs btn-default">${__("Open")}</a>
			</div>
		`;
	}).join("");
	return header + cards;
}
