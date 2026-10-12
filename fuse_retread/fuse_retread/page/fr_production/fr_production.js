// Production — the retread line at a glance, for management.
//
// Built on numbers, not on one card per tyre: with hundreds of tyres in, a board of cards is a
// wall nobody reads. Every figure comes from fuse_retread.office.production and refreshes each
// minute while the page is open.

frappe.pages['fr-production'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: 'Production', single_column: true });
	const BUILD_MARKER = 'v0.1.0-2026-10-12-first';
	if (!document.getElementById('fuse-retread-stylesheet')) {
		const link = document.createElement('link');
		link.id = 'fuse-retread-stylesheet';
		link.rel = 'stylesheet';
		link.href = '/assets/fuse_retread/css/fuse_retread.css?v=' + encodeURIComponent(BUILD_MARKER);
		document.head.appendChild(link);
	}
	wrapper.frProduction = new RetreadProduction(page);
};

frappe.pages['fr-production'].on_page_show = function (wrapper) {
	if (wrapper.frProduction) wrapper.frProduction.load();
};

class RetreadProduction {
	constructor(page) {
		this.page = page;
		this.$root = $('<div class="fr-prod"></div>').appendTo(page.body);
		this.page.set_primary_action(__('Refresh'), () => this.load(), 'refresh');
		this.page.set_secondary_action(__('The four flows'), () => frappe.set_route('fr-flows'));
		this.range = 'today';
		this.load();
		this.timer = setInterval(() => {
			if (frappe.get_route_str() === 'fr-production') this.load();
		}, 60000);
	}

	load() {
		frappe.call({ method: 'fuse_retread.office.production' }).then((r) => {
			this.data = r.message;
			this.draw();
		});
	}

	esc(v) {
		return frappe.utils.escape_html(v == null ? '' : String(v));
	}

	draw() {
		const d = this.data;
		if (!d) return;
		const esc = (v) => this.esc(v);
		const pct = d.target ? Math.min(100, Math.round((d.output_today / d.target) * 100)) : 0;
		const tone = !d.target ? '' : pct >= 90 ? 'is-good' : pct >= 60 ? 'is-warn' : 'is-bad';
		const maxQueue = Math.max(1, ...d.queue.map((q) => q.count));
		const queue = d.queue.map((q) => [
			'<div class="fr-q-row">',
			'<span class="fr-q-name">' + esc(q.stage) + (q.suggested ? ' <i class="fr-badge">Suggested</i>' : '') + '</span>',
			'<span class="fr-q-bar"><span style="width:' + Math.round((q.count / maxQueue) * 100) + '%"></span></span>',
			'<span class="fr-q-count">' + q.count + '</span>',
			'</div>',
		].join('')).join('');

		const problems = (this.range === 'today' ? d.problems_today : d.problems_week);
		const label = { No: 'Not retreadable', Reject: 'A · Reject', Redo: 'B · Redo', Repair: 'C · Repair' };
		const problemRows = problems.length ? problems.map((p) => '<tr><td>' + esc(label[p.outcome] || p.outcome) + '</td><td>' + esc(p.reason) +
			'</td><td class="fr-num">' + p.count + '</td></tr>').join('') : '<tr><td colspan="3" class="fr-muted">None.</td></tr>';

		const waiting = d.waiting_longest.length ? d.waiting_longest.map((w) => '<tr data-job="' + esc(w.job) + '"><td><b>' + esc(w.serial) + '</b></td><td>' +
			esc(w.customer) + '</td><td>' + esc(w.waiting_for) + '</td><td class="fr-num">' + this.hours(w.hours) + '</td></tr>').join('') :
			'<tr><td colspan="4" class="fr-muted">Nothing waiting.</td></tr>';

		this.$root.html([
			'<div class="fr-kpis">',
			'  <div class="fr-kpi fr-kpi-main ' + tone + '"><span class="fr-kpi-label">Output today</span>',
			'    <span class="fr-kpi-value">' + d.output_today + '<small> / ' + d.target + '</small></span>',
			'    <span class="fr-kpi-track"><span style="width:' + pct + '%"></span></span>',
			'    <span class="fr-kpi-note">Tyres passed at Final Inspection, against the daily target</span></div>',
			this.kpi('In the factory', d.in_progress, 'Not yet back with their owner'),
			this.kpi('In the chambers', d.in_chambers, 'Curing now'),
			this.kpi('Booked in today', d.received_today, 'At every branch'),
			this.kpi('Dispatched today', d.dispatched_today, 'Back to the branches'),
			this.kpi('Redos today', d.redos_today, 'Sent back to the start of the line', d.redos_today ? 'is-warn' : ''),
			this.kpi('Rejects today', d.rejects_today, 'Including not retreadable', d.rejects_today ? 'is-bad' : ''),
			'</div>',
			'<div class="fr-panels">',
			'  <section class="fr-panel"><h3>Where the tyres are waiting</h3>' + queue + '</section>',
			'  <section class="fr-panel"><h3>Output, last 7 days</h3>' + this.chart(d.by_day, d.target) + '</section>',
			'  <section class="fr-panel"><div class="fr-panel-head"><h3>Rejects and redos</h3>',
			'    <span class="fr-toggle"><button type="button" data-range="today" class="' + (this.range === 'today' ? 'is-on' : '') + '">Today</button>',
			'    <button type="button" data-range="week" class="' + (this.range === 'week' ? 'is-on' : '') + '">7 days</button></span></div>',
			'    <table class="fr-table"><thead><tr><th>Outcome</th><th>Reason</th><th class="fr-num">Tyres</th></tr></thead><tbody>' + problemRows + '</tbody></table></section>',
			'  <section class="fr-panel"><h3>Waiting longest</h3>',
			'    <table class="fr-table fr-clickable"><thead><tr><th>Tyre</th><th>Customer</th><th>Waiting for</th><th class="fr-num">Waiting</th></tr></thead><tbody>' + waiting + '</tbody></table></section>',
			'</div>',
			'<p class="fr-asat">As at ' + esc(frappe.datetime.str_to_user(d.as_at)) + '. Refreshes every minute.</p>',
		].join(''));

		this.$root.find('[data-range]').on('click', (e) => { this.range = $(e.currentTarget).attr('data-range'); this.draw(); });
		this.$root.find('tr[data-job]').on('click', (e) => frappe.set_route('Form', 'FR Job Card', $(e.currentTarget).attr('data-job')));
	}

	kpi(label, value, note, tone) {
		return '<div class="fr-kpi ' + (tone || '') + '"><span class="fr-kpi-label">' + this.esc(label) + '</span><span class="fr-kpi-value">' +
			this.esc(value) + '</span><span class="fr-kpi-note">' + this.esc(note) + '</span></div>';
	}

	hours(h) {
		if (h >= 48) return Math.round(h / 24) + ' days';
		if (h >= 1) return Math.round(h) + ' h';
		return Math.max(1, Math.round(h * 60)) + ' min';
	}

	// Seven bars on one scale, the target as a dashed line across them.
	chart(days, target) {
		const W = 420, H = 170, left = 30, bottom = 24, top = 10;
		const max = Math.max(target || 0, ...days.map((d) => d.output), 1);
		const scale = (v) => (H - bottom) - ((H - bottom - top) * v) / max;
		const slot = (W - left) / days.length;
		const bars = days.map((d, i) => {
			const x = left + i * slot + slot * 0.18;
			const w = slot * 0.64;
			const y = scale(d.output);
			const day = frappe.datetime.str_to_obj(d.date);
			const name = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][day.getDay()];
			const today = i === days.length - 1;
			return '<rect class="fr-bar' + (today ? ' is-today' : '') + '" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) +
				'" height="' + Math.max(0, (H - bottom) - y).toFixed(1) + '" rx="3"></rect>' +
				'<text class="fr-bar-value" x="' + (x + w / 2).toFixed(1) + '" y="' + (y - 4).toFixed(1) + '" text-anchor="middle">' + d.output + '</text>' +
				'<text class="fr-bar-day" x="' + (x + w / 2).toFixed(1) + '" y="' + (H - 6) + '" text-anchor="middle">' + name + '</text>';
		}).join('');
		const ty = scale(target || 0);
		const line = target ? '<line class="fr-target" x1="' + left + '" x2="' + W + '" y1="' + ty.toFixed(1) + '" y2="' + ty.toFixed(1) + '"></line>' +
			'<text class="fr-target-label" x="' + (left - 4) + '" y="' + (ty + 4).toFixed(1) + '" text-anchor="end">' + target + '</text>' : '';
		return '<svg class="fr-chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Tyres passed at Final Inspection each day for the last seven days, against the daily target of ' +
			(target || 0) + '">' + line + bars + '</svg>';
	}
}
