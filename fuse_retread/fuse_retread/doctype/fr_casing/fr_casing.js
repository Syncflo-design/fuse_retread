// A tyre's whole life: every visit, who built it, every inspection. The evidence the Factory
// Manager looks at when a claim comes in.

frappe.ui.form.on('FR Casing', {
	refresh(frm) {
		if (frm.is_new()) return;
		const $wrap = frm.get_field('history_html').$wrapper;
		frappe.call({ method: 'fuse_retread.office.casing_history', args: { casing: frm.doc.name } }).then((r) => {
			const esc = frappe.utils.escape_html;
			const when = (v) => (v ? frappe.datetime.str_to_user(v) : '');
			const visits = (r.message || []).map((job) => [
				'<div style="border:1px solid var(--border-color);border-radius:10px;padding:12px 14px;margin-bottom:10px">',
				'<div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">',
				'<b><a href="/desk/fr-job-card/' + encodeURIComponent(job.name) + '">' + esc(job.name) + '</a></b>',
				'<span>' + esc(job.customer_name) + ' · ' + esc(job.branch || '') + '</span></div>',
				'<div class="text-muted small">' + __('In') + ' ' + esc(when(job.received_on)) +
					(job.delivered_on ? ' · ' + __('Back') + ' ' + esc(when(job.delivered_on)) : '') +
					' · ' + esc([job.route, job.tread_pattern].filter(Boolean).join(' · ')) + ' · <b>' + esc(job.result || job.status) + '</b>' +
					(job.built_by ? ' · ' + __('Built by {0}', [esc(job.built_by)]) : '') + '</div>',
				'<table class="table table-sm" style="margin:8px 0 0"><tbody>',
				(job.events || []).map((e) => '<tr><td>' + esc(e.stage) + '</td><td>' + esc(e.outcome) + (e.reason ? ' · ' + esc(e.reason) : '') +
					'</td><td>' + esc(e.operator || '') + '</td><td class="text-right text-muted">' + esc(when(e.at)) + '</td></tr>').join(''),
				'</tbody></table></div>',
			].join('')).join('');
			$wrap.html(visits || '<p class="text-muted">' + __('No visits yet.') + '</p>');
		});
	},
});
