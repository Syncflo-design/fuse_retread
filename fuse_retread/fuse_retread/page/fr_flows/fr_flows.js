// The Four Flows — one screen showing that claims, own stock and casing credits run on the same
// factory line as customer retreads. Only the way a tyre comes in and the way it leaves differ.
//
// The line itself is read from the site's own stage list, so it always shows the stages this
// factory actually has. The entry and exit steps of the other three flows are the client's own
// drawing; they are not built in this version, and the page says so.

frappe.pages['fr-flows'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: 'The Four Flows', single_column: true });
	const BUILD_MARKER = 'v0.1.0-2026-10-12-first';
	if (!document.getElementById('fuse-retread-stylesheet')) {
		const link = document.createElement('link');
		link.id = 'fuse-retread-stylesheet';
		link.rel = 'stylesheet';
		link.href = '/assets/fuse_retread/css/fuse_retread.css?v=' + encodeURIComponent(BUILD_MARKER);
		document.head.appendChild(link);
	}
	const $root = $('<div class="fr-flows"></div>').appendTo(page.body);
	frappe.call({ method: 'frappe.client.get_list', args: { doctype: 'FR Stage', fields: ['stage', 'sequence', 'screen', 'on_retread'], order_by: 'sequence asc', limit_page_length: 0 } })
		.then((r) => draw_flows($root, r.message || []));
};

const FR_FLOWS = [
	{
		name: 'Customer retreads', shown: true,
		comes_in: [['Collection from Customer', 0], ['Receive at Branch', 1]],
		goes_out: [['Dispatch', 1], ['Return to Branch', 0], ['Invoice', 1], ['Deliver to Customer', 2]],
	},
	{
		name: 'Customer claims',
		comes_in: [['Receive at Branch', 1], ['Factory Manager', 1]],
		goes_out: [['Dispatch', 1], ['Return to Branch', 0], ['Invoice', 1], ['Deliver to Customer', 2]],
		note: 'The Factory Manager decides No Claim, Adjust, Redo or Repair FOC, with the tyre\'s history in front of them.',
	},
	{
		name: 'Own stock',
		comes_in: [['PO & GRV: Casings', 0], ['Store', 0], ['Store to Factory (SNF)', 1]],
		goes_out: [['Send to Warehouse', 0], ['Store', 1]],
		note: 'A casing that fails the first inspection goes back to the supplier: RTS, then a credit note.',
	},
	{
		name: 'Casing credits',
		comes_in: [['Receive at Branch', 1]],
		goes_out: [['Credit Note for Casing', 0], ['Tyre to Warehouse', 1], ['Store', 1], ['Document to Branch', 1]],
		note: 'Kept as stock: the customer is credited for the casing. Rejected: it goes back to them.',
	},
];

function draw_flows($root, stages) {
	const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));
	// 0 = physical step, 1 = recorded in Fuse, 2 = suggested recording point.
	const step = (pair) => '<span class="fr-step fr-step-' + pair[1] + '">' + esc(pair[0]) + '</span>';
	const entry = stages.find((s) => s.screen === 'Inspection');
	const final = stages.filter((s) => s.screen === 'Inspection').pop();
	const line = stages.filter((s) => s.on_retread && entry && final && s.sequence >= entry.sequence && s.sequence <= final.sequence)
		.map((s) => '<span class="' + (s.screen === 'None' ? '' : 'is-rec') + '">' + esc(s.stage) + '</span>').join('<i>›</i>');

	const rows = FR_FLOWS.map((f) => [
		'<div class="fr-flow-row' + (f.shown ? ' is-shown' : '') + '">',
		'  <div class="fr-flow-name">' + esc(f.name) + (f.shown ? '<span class="fr-badge fr-badge-go">In this demo</span>' : '') + '</div>',
		'  <div class="fr-flow-cell">' + f.comes_in.map(step).join('') + '</div>',
		'  <div class="fr-flow-arrow" aria-hidden="true">→</div>',
		'  <div class="fr-flow-line">The same line</div>',
		'  <div class="fr-flow-arrow" aria-hidden="true">→</div>',
		'  <div class="fr-flow-cell">' + f.goes_out.map(step).join('') + '</div>',
		f.note ? '  <div class="fr-flow-note">' + esc(f.note) + '</div>' : '',
		'</div>',
	].join('')).join('');

	$root.html([
		'<div class="fr-flows-intro">',
		'  <h2>Four flows, one factory line</h2>',
		'  <p>Every tyre, whoever owns it and however it arrived, passes through the same line. Only the way it comes in and the way it leaves are different. ',
		'  So the screens shown today for customer retreads are the screens claims, own stock and casing credits use too.</p>',
		'</div>',
		'<div class="fr-the-line"><span class="fr-sub">The line</span><div>' + line + '</div></div>',
		'<div class="fr-flow-head"><span>Flow</span><span>Comes in</span><span></span><span></span><span></span><span>Goes out</span></div>',
		rows,
		'<div class="fr-flows-legend"><span class="fr-step fr-step-1">Recorded in Fuse</span><span class="fr-step fr-step-0">Physical step</span>',
		'<span class="fr-step fr-step-2">Suggested</span></div>',
	].join(''));
}
