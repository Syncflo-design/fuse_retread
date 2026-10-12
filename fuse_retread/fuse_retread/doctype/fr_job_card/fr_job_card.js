// Job Card: one tyre's visit. The stages are recorded from the floor screens; the office
// approves the invoice here. In this version the invoice is a preview and nothing posts to
// Sage Intacct.

const FR_STATUS_COLOUR = { 'In Progress': 'blue', Dispatched: 'orange', Invoiced: 'purple', Delivered: 'green' };

frappe.ui.form.on('FR Job Card', {
	refresh(frm) {
		if (frm.is_new()) return;
		const next = (frm.doc.next_stages || '').split('\n').filter(Boolean);
		frm.page.set_indicator(__(frm.doc.status), FR_STATUS_COLOUR[frm.doc.status] || 'gray');
		frm.set_intro(next.length ? __('Next for this tyre: {0}', [next.join(' or ')]) : __('Back with its owner.'),
			next.length ? 'blue' : 'green');
		if (frm.doc.result === 'Rejected' || frm.doc.result === 'Not Retreadable') {
			frm.dashboard.set_headline_alert(__('Result: {0}', [frm.doc.result]), 'red');
		}
		frm.add_custom_button(__('Tyre History'), () => frappe.set_route('Form', 'FR Casing', frm.doc.casing));
		fr_invoice_preview(frm, next);
	},
});

function fr_invoice_preview(frm, next) {
	const $wrap = frm.get_field('invoice_html').$wrapper;
	if (!(next.includes('Invoice') || ['Invoiced', 'Delivered'].includes(frm.doc.status))) {
		$wrap.html('<p class="text-muted">' + __('The invoice is ready once the tyre is dispatched back to its branch.') + '</p>');
		return;
	}
	frappe.call({ method: 'fuse_retread.office.invoice_preview', args: { job: frm.doc.name } }).then((r) => {
		const p = r.message;
		const money = (v) => format_currency(v, frappe.defaults.get_default('currency') || 'ZAR');
		const esc = frappe.utils.escape_html;
		$wrap.html([
			'<div style="border:1px solid var(--border-color);border-radius:10px;padding:14px 16px;max-width:640px">',
			'<div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap">',
			'<div><div class="text-muted small">' + __('Sales invoice to') + '</div><b>' + esc(p.customer_name) + '</b></div>',
			'<div class="text-right"><div class="text-muted small">' + __('Branch') + '</div>' + esc(p.branch || '') + '</div></div>',
			'<table class="table table-sm" style="margin:12px 0 6px"><thead><tr><th>' + __('Item') + '</th><th>' + __('Description') +
				'</th><th class="text-right">' + __('Qty') + '</th><th class="text-right">' + __('Price') + '</th></tr></thead><tbody>',
			p.lines.map((l) => '<tr><td>' + esc(l.item) + '</td><td>' + esc(l.description) + '</td><td class="text-right">' + l.qty +
				'</td><td class="text-right">' + money(l.price) + '</td></tr>').join(''),
			'</tbody></table>',
			'<div class="text-right">' + __('Net') + ' ' + money(p.net) + '<br>' + __('VAT {0}%', [p.vat_percent]) + ' ' + money(p.vat) +
				'<br><b>' + __('Total') + ' ' + money(p.total) + '</b></div>',
			'<p class="text-muted small" style="margin:10px 0 0">' +
				__('Preview of what would go to Sage Intacct as a sales invoice. Nothing is posted in this version.') + '</p>',
			'</div>',
		].join(''));
		if (next.includes('Invoice') && !p.invoiced) {
			frm.add_custom_button(__('Approve Invoice'), () => {
				frappe.call({ method: 'fuse_retread.office.approve_invoice', args: { job: frm.doc.name } }).then(() => {
					frappe.show_alert({ message: __('Invoice approved'), indicator: 'green' });
					frm.reload_doc();
				});
			}).addClass('btn-primary');
		}
	});
}
