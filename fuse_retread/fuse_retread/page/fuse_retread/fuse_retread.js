// Fuse Retread — the floor screens, for a tablet or phone.
//
// One pattern everywhere: type the last digits of the tyre number, check the tyre, tap one big
// button. Problems are picture buttons, never a form. Every tap goes through
// fuse_retread.floor, which asks the route engine whether the tyre is due there — so a stage
// cannot be skipped from here any more than from the desk.
//
// Mounted in page.body (a jQuery object in v16, per CoWork_Helper gotcha
// 2026-05-10-frappe-v16-page-api-drift). Server text always goes through esc() or .text().

frappe.pages['fuse-retread'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: 'Retread Floor', single_column: true });

	const BUILD_MARKER = 'v0.1.0-2026-10-12-first';
	if (!document.getElementById('fuse-retread-stylesheet')) {
		const link = document.createElement('link');
		link.id = 'fuse-retread-stylesheet';
		link.rel = 'stylesheet';
		link.href = '/assets/fuse_retread/css/fuse_retread.css?v=' + encodeURIComponent(BUILD_MARKER);
		document.head.appendChild(link);
	}
	wrapper.fuseRetread = new RetreadFloor(page);
};

frappe.pages['fuse-retread'].on_page_show = function (wrapper) {
	if (wrapper.fuseRetread) wrapper.fuseRetread.refresh_home();
};

const FR = 'fuse_retread.floor.';

// Lucide paths, one stroke weight. Every icon sits beside text, so all are aria-hidden.
const FR_ICONS = {
	back: 'M19 12H5M12 19l-7-7 7-7',
	tick: 'M20 6 9 17l-5-5',
	x: 'M18 6 6 18M6 6l12 12',
	alert: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
	cut: 'M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12',
	layers: 'm12 2 10 5-10 5L2 7l10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
	flame: 'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z',
	circle: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
	ruler: 'M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0zM14.5 12.5l2-2M11.5 9.5l2-2M8.5 6.5l2-2M17.5 15.5l2-2',
	droplet: 'M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z',
	nail: 'M12 2v14M8 2h8M12 16l-2 6h4z',
	clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2',
	wrench: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z',
	user: 'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
	tyre: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v6M12 16v6M2 12h6M16 12h6',
	camera: 'M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
	truck: 'M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2M15 18H9M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14M7 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
	hand: 'M18 11V6a2 2 0 0 0-4 0v1M14 10V4a2 2 0 0 0-4 0v2M10 10.5V6a2 2 0 0 0-4 0v8M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15',
	inbox: 'M22 12h-6l-2 3h-4l-2-3H2M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
	search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
	del: 'M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM18 9l-6 6M12 9l6 6',
};

// What each screen type is on the home grid.
const FR_SCREEN_ICON = {
	Receive: 'inbox', Inspection: 'search', 'Number Pad': 'wrench', Chambers: 'flame',
	Dispatch: 'truck', Deliver: 'hand',
};

function fr_icon(name, cls) {
	return '<svg class="fr-icon ' + (cls || '') + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
		'<path d="' + (FR_ICONS[name] || FR_ICONS.alert) + '"></path></svg>';
}

function esc(value) {
	return frappe.utils.escape_html(value == null ? '' : String(value));
}

function fr_get(key) {
	try { return localStorage.getItem('fuse_retread:' + key) || ''; } catch (e) { return ''; }
}

function fr_set(key, value) {
	try { localStorage.setItem('fuse_retread:' + key, value || ''); } catch (e) { /* a locked-down browser is not a reason to stop */ }
}

// The typed digits shown inside the full number, so the operator sees what matched.
function fr_serial(serial, digits) {
	serial = String(serial || '');
	if (digits && serial.endsWith(digits)) {
		return esc(serial.slice(0, serial.length - digits.length)) + '<b>' + esc(digits) + '</b>';
	}
	return esc(serial);
}

function fr_call(method, args) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: FR + method,
			args: args || {},
			freeze: false,
			callback: (r) => resolve(r.message),
			error: (e) => reject(e),
		});
	});
}

class RetreadFloor {
	constructor(page) {
		this.page = page;
		this.ctx = null;
		this.$root = $('<div class="fr-root"></div>').appendTo(page.body);
		this.page.set_secondary_action(__('Home'), () => this.home(), 'home');
		this.refresh_home();
	}

	get operator() {
		return fr_get('operator');
	}

	refresh_home() {
		fr_call('bootstrap').then((ctx) => {
			this.ctx = ctx;
			if (!this.screen || this.screen === 'home') this.home();
		});
	}

	render(html) {
		this.$root.html(html);
		window.scrollTo(0, 0);
	}

	toast(message, indicator) {
		frappe.show_alert({ message: esc(message), indicator: indicator || 'green' }, 4);
	}

	operator_bar() {
		const who = this.operator;
		return '<button type="button" class="fr-who" data-act="who">' + fr_icon('user') +
			'<span>' + (who ? 'Working as <b>' + esc(who) + '</b>' : '<b>Tap to say who is working</b>') + '</span></button>';
	}

	need_operator(then) {
		if (this.operator) return then();
		this.pick_operator(then);
	}

	pick_operator(then) {
		const ops = (this.ctx && this.ctx.operators) || [];
		this.screen = 'who';
		this.render([
			'<div class="fr-head"><h2>Who is working?</h2></div>',
			'<p class="fr-lead">Each stage records who did it. Choose your name once; this device remembers it.</p>',
			'<div class="fr-tiles">',
			ops.map((op) => '<button type="button" class="fr-tile" data-op="' + esc(op) + '">' + fr_icon('user') + '<span>' + esc(op) + '</span></button>').join(''),
			'</div>',
		].join(''));
		this.$root.find('[data-op]').on('click', (e) => {
			fr_set('operator', $(e.currentTarget).attr('data-op'));
			if (then) then(); else this.home();
		});
	}

	// ── home ────────────────────────────────────────────────────────────────

	home() {
		this.screen = 'home';
		if (!this.ctx) return this.render('<p class="fr-lead">Loading…</p>');
		const tiles = this.ctx.screens.map((s) => [
			'<button type="button" class="fr-stage" data-stage="' + esc(s.stage) + '" data-screen="' + esc(s.screen) + '">',
			'  <span class="fr-stage-icon">' + fr_icon(FR_SCREEN_ICON[s.screen] || 'tyre') + '</span>',
			'  <span class="fr-stage-name">' + esc(s.stage) + (s.suggested ? ' <i class="fr-badge">Suggested</i>' : '') + '</span>',
			'  <span class="fr-stage-count" aria-label="' + s.waiting + ' due">' + (s.screen === 'Receive' ? '' : s.waiting) + '</span>',
			'</button>',
		].join('')).join('');
		this.render([
			this.operator_bar(),
			'<div class="fr-stages">', tiles, '</div>',
		].join(''));
		this.$root.find('[data-act="who"]').on('click', () => this.pick_operator());
		this.$root.find('[data-stage]').on('click', (e) => {
			const $b = $(e.currentTarget);
			const stage = $b.attr('data-stage');
			const screen = $b.attr('data-screen');
			this.need_operator(() => this.open(stage, screen));
		});
	}

	open(stage, screen) {
		if (screen === 'Receive') return this.receive(stage);
		if (screen === 'Chambers') return this.chambers(stage);
		if (screen === 'Dispatch') return this.dispatch(stage);
		if (screen === 'Deliver') return this.deliver(stage);
		return this.pad(stage, screen);
	}

	header(title, sub) {
		return '<div class="fr-head"><button type="button" class="fr-back" data-act="home" aria-label="Back">' +
			fr_icon('back') + '</button><div><h2>' + esc(title) + '</h2>' + (sub ? '<p>' + esc(sub) + '</p>' : '') + '</div></div>';
	}

	bind_back() {
		this.$root.find('[data-act="home"]').on('click', () => { this.screen = 'home'; this.refresh_home(); this.home(); });
	}

	// ── the number pad ──────────────────────────────────────────────────────

	keypad_html() {
		const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'clear', '0', 'del'];
		return '<div class="fr-pad">' + keys.map((k) => {
			if (k === 'del') return '<button type="button" class="fr-key fr-key-soft" data-key="del" aria-label="Delete">' + fr_icon('del') + '</button>';
			if (k === 'clear') return '<button type="button" class="fr-key fr-key-soft" data-key="clear">Clear</button>';
			return '<button type="button" class="fr-key" data-key="' + k + '">' + k + '</button>';
		}).join('') + '</div>';
	}

	bind_keypad(onchange) {
		this.digits = '';
		const $display = this.$root.find('.fr-digits');
		const show = () => $display.text(this.digits || '—');
		this.$root.find('[data-key]').on('click', (e) => {
			const key = $(e.currentTarget).attr('data-key');
			if (key === 'del') this.digits = this.digits.slice(0, -1);
			else if (key === 'clear') this.digits = '';
			else if (this.digits.length < 8) this.digits += key;
			show();
			clearTimeout(this.search_timer);
			this.search_timer = setTimeout(() => onchange(this.digits), 220);
		});
		show();
	}

	pad(stage, screen) {
		this.screen = 'pad';
		this.stage = stage;
		const hint = screen === 'Inspection' ? 'Type the last digits of the tyre number, then check the tyre.' :
			'Type the last digits of the tyre number, then tap Done.';
		this.render([
			this.header(stage, hint),
			'<div class="fr-entry"><span class="fr-entry-label">Tyre number ends</span><span class="fr-digits" aria-live="polite">—</span></div>',
			this.keypad_html(),
			'<div class="fr-results" aria-live="polite"></div>',
		].join(''));
		this.bind_back();
		this.bind_keypad((digits) => this.search(stage, digits));
	}

	search(stage, digits) {
		const $out = this.$root.find('.fr-results');
		if (!digits || digits.length < 2) return $out.empty();
		fr_call('find', { stage: stage, digits: digits }).then((found) => {
			if (digits !== this.digits) return;
			if (!found || !found.length) {
				$out.html('<p class="fr-none">No tyre in the factory ends in ' + esc(digits) + '.</p>');
				return;
			}
			$out.html(found.map((t, i) => this.tyre_card(t, digits, i)).join(''));
			$out.find('[data-pick]').on('click', (e) => this.act(stage, found[+$(e.currentTarget).attr('data-pick')]));
			if (found.length === 1 && found[0].due) this.act(stage, found[0]);
		});
	}

	tyre_card(t, digits, index) {
		const photo = t.photo ? '<img class="fr-photo" src="' + esc(t.photo) + '" alt="">' :
			'<span class="fr-photo fr-photo-none">' + fr_icon('tyre') + '</span>';
		const where = t.due ? '<span class="fr-due">Due here</span>' :
			'<span class="fr-notdue">Not due here. Next: ' + esc((t.next || []).join(' or ') || 'nothing') + '</span>';
		return [
			'<button type="button" class="fr-card' + (t.due ? '' : ' is-off') + '" data-pick="' + index + '"' + (t.due ? '' : ' disabled') + '>',
			photo,
			'<span class="fr-card-body">',
			'  <span class="fr-card-serial">' + fr_serial(t.serial, digits) + '</span>',
			'  <span class="fr-card-meta">' + esc(t.customer_name) + '</span>',
			'  <span class="fr-card-meta">' + esc([t.size, t.brand].filter(Boolean).join(' · ')) + '</span>',
			'  ' + where,
			'</span>',
			'</button>',
		].join('');
	}

	// The one decision for a tyre at this stage: big buttons, reasons as pictures.
	act(stage, t) {
		const outcomes = (t.outcomes || {})[stage] || [];
		const screen = (this.ctx.screens.find((s) => s.stage === stage) || {}).screen;
		const first = screen === 'Inspection' && outcomes.indexOf('Yes') !== -1;
		const buttons = [];
		if (first) {
			buttons.push('<button type="button" class="fr-go" data-out="Yes" data-route="Retread">' + fr_icon('tick') + 'Yes: retread</button>');
			buttons.push('<button type="button" class="fr-alt" data-out="Yes" data-route="Repair Only">' + fr_icon('wrench') + 'Yes: repair only</button>');
			buttons.push('<button type="button" class="fr-bad" data-out="No">' + fr_icon('x') + 'No: not retreadable</button>');
		} else {
			outcomes.forEach((o) => {
				if (o === 'Pass' || o === 'Done') buttons.push('<button type="button" class="fr-go" data-out="' + o + '">' + fr_icon('tick') + esc(o) + '</button>');
				else if (o === 'Reject') buttons.push('<button type="button" class="fr-bad" data-out="Reject">A · Reject</button>');
				else if (o === 'Redo') buttons.push('<button type="button" class="fr-warn" data-out="Redo">B · Redo</button>');
				else if (o === 'Repair') buttons.push('<button type="button" class="fr-warn" data-out="Repair">C · Repair</button>');
			});
		}
		const patterns = stage === 'Building' ? this.pattern_tiles(t) : '';
		const $sheet = $([
			'<div class="fr-sheet" role="dialog" aria-label="' + esc(stage) + '">',
			'  <div class="fr-sheet-card">',
			'    <div class="fr-sheet-tyre">' + this.tyre_card(Object.assign({}, t, { due: true }), this.digits, 0).replace('<button', '<div').replace('</button>', '</div>') + '</div>',
			patterns,
			'    <div class="fr-actions">' + buttons.join('') + '</div>',
			'    <div class="fr-reasons" hidden></div>',
			'    <button type="button" class="fr-cancel">Not this tyre</button>',
			'  </div>',
			'</div>',
		].join(''));
		this.$root.find('.fr-sheet').remove();
		this.$root.append($sheet);
		$sheet.find('.fr-cancel').on('click', () => $sheet.remove());
		$sheet.find('[data-pattern]').on('click', (e) => {
			$sheet.find('[data-pattern]').removeClass('is-on').attr('aria-pressed', 'false');
			$(e.currentTarget).addClass('is-on').attr('aria-pressed', 'true');
			fr_set('pattern', $(e.currentTarget).attr('data-pattern'));
		});
		$sheet.find('[data-out]').on('click', (e) => {
			const outcome = $(e.currentTarget).attr('data-out');
			const route = $(e.currentTarget).attr('data-route');
			const reasonsFor = { No: 'Not Retreadable', Reject: 'Reject', Redo: 'Redo', Repair: 'Repair' }[outcome];
			if (reasonsFor) return this.ask_reason($sheet, reasonsFor, (reason) => this.save(stage, t, outcome, { reason: reason }, $sheet));
			const extra = { route: route };
			if (stage === 'Building') extra.tread_pattern = $sheet.find('[data-pattern].is-on').attr('data-pattern') || '';
			this.save(stage, t, outcome, extra, $sheet);
		});
	}

	pattern_tiles(t) {
		const remembered = t.tread_pattern || fr_get('pattern');
		const tiles = (this.ctx.patterns || []).map((p) => {
			const on = p.name === remembered;
			return '<button type="button" class="fr-chip' + (on ? ' is-on' : '') + '" aria-pressed="' + on + '" data-pattern="' + esc(p.name) + '">' + esc(p.name) + '</button>';
		}).join('');
		return tiles ? '<div class="fr-sub">Tread pattern</div><div class="fr-chips">' + tiles + '</div>' : '';
	}

	ask_reason($sheet, outcome, then) {
		const reasons = (this.ctx.reasons || {})[outcome] || [];
		const $box = $sheet.find('.fr-reasons');
		$sheet.find('.fr-actions').attr('hidden', true);
		$box.removeAttr('hidden').html([
			'<div class="fr-sub">Why?</div>',
			'<div class="fr-reason-grid">',
			reasons.map((r) => '<button type="button" class="fr-reason" data-reason="' + esc(r.reason) + '">' + fr_icon(r.icon, 'fr-icon-lg') + '<span>' + esc(r.reason) + '</span></button>').join(''),
			'</div>',
		].join(''));
		$box.find('[data-reason]').on('click', (e) => then($(e.currentTarget).attr('data-reason')));
	}

	save(stage, t, outcome, extra, $sheet) {
		$sheet.find('button').prop('disabled', true);
		fr_call('record', Object.assign({ job: t.name, stage: stage, outcome: outcome, operator: this.operator }, extra || {}))
			.then(() => {
				$sheet.remove();
				this.toast(t.serial + ': ' + stage + ' · ' + outcome);
				this.digits = '';
				this.$root.find('.fr-digits').text('—');
				this.$root.find('.fr-results').empty();
			})
			.catch(() => $sheet.find('button').prop('disabled', false));
	}

	// ── Receive at Branch ───────────────────────────────────────────────────

	receive(stage) {
		this.screen = 'receive';
		this.form = { branch: fr_get('branch'), source: 'Manufacturer' };
		const ctx = this.ctx;
		const branches = ctx.branches.map((b) => '<button type="button" class="fr-chip' + (b === this.form.branch ? ' is-on' : '') + '" data-branch="' + esc(b) + '">' + esc(b) + '</button>').join('');
		const sizes = ctx.sizes.map((s) => '<button type="button" class="fr-chip" data-size="' + esc(s) + '">' + esc(s) + '</button>').join('');
		const brands = ctx.brands.map((b) => '<button type="button" class="fr-chip" data-brand="' + esc(b) + '">' + esc(b) + '</button>').join('');
		this.render([
			this.header(stage, 'Book a customer\'s tyre in. One identity for life.'),
			'<div class="fr-form">',
			'<label class="fr-sub" for="fr-customer">Customer</label>',
			'<input id="fr-customer" class="fr-input" autocomplete="off" placeholder="Start typing the customer\'s name">',
			'<div class="fr-picklist" data-list="customer"></div>',
			'<div class="fr-sub">Branch</div><div class="fr-chips">' + branches + '</div>',
			'<label class="fr-sub" for="fr-serial">Tyre number</label>',
			'<div class="fr-row"><input id="fr-serial" class="fr-input fr-input-big" autocomplete="off" autocapitalize="characters" placeholder="Serial on the sidewall">',
			'<button type="button" class="fr-alt fr-small" data-act="issue">No serial: issue ours</button></div>',
			'<div class="fr-known" aria-live="polite"></div>',
			'<div class="fr-sub">Size</div><div class="fr-chips" data-group="size">' + sizes + '</div>',
			'<div class="fr-sub">Brand</div><div class="fr-chips" data-group="brand">' + brands + '</div>',
			'<div class="fr-sub">Photo</div>',
			'<label class="fr-photo-btn">' + fr_icon('camera') + '<span>Take a photo of the tyre</span>',
			'<input type="file" accept="image/*" capture="environment" id="fr-photo" hidden></label>',
			'<div class="fr-photo-preview"></div>',
			'<button type="button" class="fr-go fr-wide" data-act="book">' + fr_icon('tick') + 'Book the tyre in</button>',
			'</div>',
		].join(''));
		this.bind_back();
		const $r = this.$root;

		let timer = null;
		$r.find('#fr-customer').on('input', (e) => {
			clearTimeout(timer);
			const txt = e.target.value;
			this.form.customer = null;
			timer = setTimeout(() => fr_call('customers', { txt: txt }).then((rows) => {
				const $list = $r.find('[data-list="customer"]');
				$list.html((rows || []).slice(0, 8).map((c) => '<button type="button" class="fr-pick" data-customer="' + esc(c.name) + '">' + esc(c.customer_name) + '</button>').join(''));
				$list.find('[data-customer]').on('click', (ev) => {
					this.form.customer = $(ev.currentTarget).attr('data-customer');
					$r.find('#fr-customer').val($(ev.currentTarget).text());
					$list.empty();
				});
			}), 200);
		});
		$r.find('[data-branch]').on('click', (e) => {
			$r.find('[data-branch]').removeClass('is-on');
			$(e.currentTarget).addClass('is-on');
			this.form.branch = $(e.currentTarget).attr('data-branch');
			fr_set('branch', this.form.branch);
		});
		const choose = (group, value) => {
			this.form[group] = value;
			$r.find('[data-' + group + ']').each((i, el) => $(el).toggleClass('is-on', $(el).attr('data-' + group) === value));
		};
		$r.find('[data-size]').on('click', (e) => choose('size', $(e.currentTarget).attr('data-size')));
		$r.find('[data-brand]').on('click', (e) => choose('brand', $(e.currentTarget).attr('data-brand')));

		let lookupTimer = null;
		$r.find('#fr-serial').on('input', (e) => {
			this.form.source = 'Manufacturer';
			clearTimeout(lookupTimer);
			const serial = e.target.value;
			lookupTimer = setTimeout(() => this.show_known(serial, choose), 400);
		});
		$r.find('[data-act="issue"]').on('click', () => fr_call('issue_number').then((number) => {
			this.form.source = 'Factory';
			$r.find('#fr-serial').val(number);
			$r.find('.fr-known').html('<div class="fr-issued">Mark <b>' + esc(number) + '</b> on the tyre now.</div>');
		}));
		$r.find('#fr-photo').on('change', (e) => this.upload_photo(e.target.files && e.target.files[0]));
		$r.find('[data-act="book"]').on('click', () => this.book(stage));
	}

	show_known(serial, choose) {
		const $box = this.$root.find('.fr-known');
		if (!serial || serial.length < 4) return $box.empty();
		fr_call('lookup', { serial: serial }).then((info) => {
			if (!info) return $box.empty();
			if (!info.known) {
				$box.html(info.own_number ? '<div class="fr-warnbox">' + fr_icon('alert') + 'That looks like one of our own numbers, but it was never issued. Use “issue ours”.</div>' :
					'<div class="fr-newbox">New tyre. First visit.</div>');
				return;
			}
			if (info.size) choose('size', info.size);
			if (info.brand) choose('brand', info.brand);
			if (info.open_job) {
				$box.html('<div class="fr-warnbox">' + fr_icon('alert') + 'This tyre is already in, on ' + esc(info.open_job) + '.</div>');
				return;
			}
			$box.html(this.history_html(info));
		});
	}

	history_html(info) {
		const visits = (info.history || []).map((job) => {
			const final = (job.events || []).filter((e) => e.stage === 'Final Inspection').pop();
			return [
				'<li>',
				'<b>' + esc(frappe.datetime.str_to_user((job.received_on || '').slice(0, 10))) + '</b> · ' + esc(job.customer_name),
				'<span>' + esc([job.route, job.tread_pattern].filter(Boolean).join(' · ')) + '</span>',
				'<span>' + esc(job.built_by ? 'Built by ' + job.built_by : 'Not built') +
					(final ? ' · Final Inspection: ' + esc(final.outcome) + (final.operator ? ' (' + esc(final.operator) + ')' : '') : '') + '</span>',
				'<span>' + esc(job.result || job.status) + (job.redo_count ? ' · ' + job.redo_count + ' redo' : '') + '</span>',
				'</li>',
			].join('');
		}).join('');
		return '<div class="fr-history"><div class="fr-history-head">' + fr_icon('clock') + 'Been here before: ' +
			(info.history || []).length + ' visit' + ((info.history || []).length === 1 ? '' : 's') + '</div><ul>' + visits + '</ul></div>';
	}

	upload_photo(file) {
		if (!file) return;
		const data = new FormData();
		data.append('file', file, file.name || 'tyre.jpg');
		data.append('is_private', '0');
		data.append('folder', 'Home');
		const $preview = this.$root.find('.fr-photo-preview').text('Uploading…');
		fetch('/api/method/upload_file', {
			method: 'POST',
			headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token, Accept: 'application/json' },
			body: data,
		}).then((r) => r.json()).then((r) => {
			this.form.photo = r.message && r.message.file_url;
			$preview.html(this.form.photo ? '<img src="' + esc(this.form.photo) + '" alt="Tyre photo">' : 'The photo did not upload. Try again.');
		}).catch(() => $preview.text('The photo did not upload. Try again.'));
	}

	book(stage) {
		const f = this.form;
		f.serial = (this.$root.find('#fr-serial').val() || '').trim();
		const missing = [!f.customer && 'the customer', !f.branch && 'the branch', !f.serial && 'the tyre number',
			!f.size && 'the size', !f.brand && 'the brand'].filter(Boolean);
		if (missing.length) {
			frappe.msgprint({ title: __('Not yet'), message: 'Still needed: ' + esc(missing.join(', ')) + '.', indicator: 'orange' });
			return;
		}
		fr_call('receive', {
			customer: f.customer, branch: f.branch, serial: f.serial, source: f.source, size: f.size,
			brand: f.brand, operator: this.operator, photo: f.photo || null,
		}).then((job) => {
			this.render([
				this.header(stage),
				'<div class="fr-done">' + fr_icon('tick', 'fr-icon-xl'),
				'<h3>Booked in</h3>',
				'<p class="fr-done-serial">' + esc(job.serial) + '</p>',
				'<p>' + esc(job.customer_name) + ' · ' + esc(job.size) + ' · ' + esc(job.brand) + '</p>',
				'<p class="fr-lead">Job Card ' + esc(job.name) + '. Next: ' + esc((job.next || []).join(' or ')) + '.</p>',
				'<button type="button" class="fr-go fr-wide" data-act="again">' + fr_icon('inbox') + 'Book in the next tyre</button>',
				'</div>',
			].join(''));
			this.bind_back();
			this.$root.find('[data-act="again"]').on('click', () => this.receive(stage));
		});
	}

	// ── Chambers ────────────────────────────────────────────────────────────

	chambers(stage) {
		this.screen = 'chambers';
		fr_call('chamber_board').then((board) => this.draw_chambers(stage, board));
	}

	draw_chambers(stage, board) {
		const cards = board.chambers.map((c, i) => {
			const state = c.status === 'Curing' ? 'Curing · ' + (c.minutes_left || 0) + ' min left' :
				c.status === 'Loading' ? 'Loading · ' + c.tyres.length + ' of ' + c.capacity : 'Empty';
			return '<button type="button" class="fr-chamber is-' + esc(c.status.toLowerCase()) + '" data-ch="' + i + '">' +
				fr_icon('flame') + '<span class="fr-chamber-name">' + esc(c.chamber) + '</span><span>' + esc(state) + '</span></button>';
		}).join('');
		this.render([
			this.header(stage, 'Load tyres into a chamber, then start and end the cure.'),
			'<p class="fr-badge-line"><i class="fr-badge">Suggested</i> Not a recording point in the drawing. Proposed because chamber loading is where the line queues.</p>',
			'<div class="fr-chambers">' + cards + '</div>',
			'<div class="fr-sub">Waiting for a chamber: ' + board.waiting.length + '</div>',
			'<div class="fr-waitlist">' + board.waiting.map((w) => '<span>' + esc(w.serial) + '</span>').join('') + '</div>',
		].join(''));
		this.bind_back();
		this.$root.find('[data-ch]').on('click', (e) => this.chamber(stage, board.chambers[+$(e.currentTarget).attr('data-ch')]));
	}

	chamber(stage, c) {
		const curing = c.status === 'Curing';
		const tyres = c.tyres.map((t) => '<li><span>' + esc(t.serial) + '</span><span class="fr-muted">' + esc(t.customer) + '</span>' +
			(curing ? '' : '<button type="button" class="fr-x" data-out="' + esc(t.job_card) + '" aria-label="Take out">' + fr_icon('x') + '</button>') + '</li>').join('');
		this.render([
			this.header(c.chamber, curing ? 'Curing. ' + (c.minutes_left || 0) + ' minutes left.' : c.tyres.length + ' of ' + c.capacity + ' loaded'),
			'<ul class="fr-loadlist">' + (tyres || '<li class="fr-muted">No tyres in yet.</li>') + '</ul>',
			curing ? '<button type="button" class="fr-go fr-wide" data-act="end">' + fr_icon('tick') + 'End cure</button>' : [
				'<div class="fr-entry"><span class="fr-entry-label">Add a tyre: number ends</span><span class="fr-digits">—</span></div>',
				this.keypad_html(),
				'<div class="fr-results"></div>',
				c.tyres.length ? '<button type="button" class="fr-go fr-wide" data-act="start">' + fr_icon('flame') + 'Start cure</button>' : '',
			].join(''),
		].join(''));
		this.$root.find('[data-act="home"]').off('click').on('click', () => this.chambers(stage));
		const reload = (board) => this.chamber(stage, board.chambers.find((x) => x.chamber === c.chamber));
		this.$root.find('[data-act="end"]').on('click', () => fr_call('end_cure', { load: c.load, operator: this.operator }).then((b) => { this.toast(c.chamber + ': cure ended'); this.draw_chambers(stage, b); }));
		this.$root.find('[data-act="start"]').on('click', () => fr_call('start_cure', { load: c.load, operator: this.operator }).then((b) => { this.toast(c.chamber + ': curing'); this.draw_chambers(stage, b); }));
		this.$root.find('[data-out]').on('click', (e) => fr_call('unload_tyre', { load: c.load, job: $(e.currentTarget).attr('data-out') }).then(reload));
		if (!curing) {
			this.bind_keypad((digits) => {
				const $out = this.$root.find('.fr-results');
				if (!digits || digits.length < 2) return $out.empty();
				fr_call('find', { stage: stage, digits: digits }).then((found) => {
					found = (found || []).filter((t) => t.due && !t.in_chamber);
					$out.html(found.length ? found.map((t, i) => this.tyre_card(t, digits, i)).join('') : '<p class="fr-none">No tyre waiting for a chamber ends in ' + esc(digits) + '.</p>');
					$out.find('[data-pick]').on('click', (e) => {
						const t = found[+$(e.currentTarget).attr('data-pick')];
						fr_call('load_tyre', { chamber: c.chamber, job: t.name }).then((b) => { this.toast(t.serial + ' into ' + c.chamber); reload(b); });
					});
				});
			});
		}
	}

	// ── Dispatch ────────────────────────────────────────────────────────────

	dispatch(stage) {
		this.screen = 'dispatch';
		const branches = this.ctx.branches.map((b) => '<button type="button" class="fr-tile" data-branch="' + esc(b) + '">' + fr_icon('truck') + '<span>' + esc(b) + '</span></button>').join('');
		this.render([this.header(stage, 'Which branch is this load going to?'), '<div class="fr-tiles">' + branches + '</div>'].join(''));
		this.bind_back();
		this.$root.find('[data-branch]').on('click', (e) => {
			const branch = $(e.currentTarget).attr('data-branch');
			fr_call('dispatch_board', { branch: branch }).then((board) => this.draw_dispatch(stage, board));
		});
	}

	draw_dispatch(stage, board) {
		const result = (r) => r ? '<span class="fr-result fr-result-' + esc(r.toLowerCase().replace(/\s+/g, '-')) + '">' + esc(r) + '</span>' : '';
		const onLoad = board.tyres.map((t) => '<li><span>' + esc(t.serial) + '</span><span class="fr-muted">' + esc(t.customer) + '</span>' + result(t.result) +
			'<button type="button" class="fr-x" data-off="' + esc(t.job_card) + '" aria-label="Take off">' + fr_icon('x') + '</button></li>').join('');
		const ready = board.ready.map((t) => '<li><span>' + esc(t.serial) + '</span><span class="fr-muted">' + esc(t.customer) + '</span>' + result(t.result) +
			'<button type="button" class="fr-add" data-on="' + esc(t.job_card) + '">Add</button></li>').join('');
		this.render([
			this.header(stage, 'Load for ' + board.branch),
			'<div class="fr-sub">On this load: ' + board.tyres.length + '</div>',
			'<ul class="fr-loadlist">' + (onLoad || '<li class="fr-muted">Nothing on the load yet.</li>') + '</ul>',
			'<div class="fr-sub">Finished, for ' + esc(board.branch) + ': ' + board.ready.length + '</div>',
			'<ul class="fr-loadlist">' + (ready || '<li class="fr-muted">No finished tyres for this branch.</li>') + '</ul>',
			board.tyres.length ? '<button type="button" class="fr-go fr-wide" data-act="send">' + fr_icon('truck') + 'Send the load (' + board.tyres.length + ')</button>' : '',
		].join(''));
		this.$root.find('[data-act="home"]').off('click').on('click', () => this.dispatch(stage));
		const redraw = (b) => this.draw_dispatch(stage, b);
		this.$root.find('[data-on]').on('click', (e) => fr_call('add_to_dispatch', { branch: board.branch, job: $(e.currentTarget).attr('data-on') }).then(redraw));
		this.$root.find('[data-off]').on('click', (e) => fr_call('remove_from_dispatch', { dispatch: board.dispatch, job: $(e.currentTarget).attr('data-off') }).then(redraw));
		this.$root.find('[data-act="send"]').on('click', () => fr_call('send_dispatch', { dispatch: board.dispatch, operator: this.operator })
			.then((b) => { this.toast('Load sent to ' + board.branch); redraw(b); }));
	}

	// ── Deliver to Customer ─────────────────────────────────────────────────

	deliver(stage) {
		this.screen = 'deliver';
		this.render([
			this.header(stage, 'Hand a customer back their own tyres.'),
			'<p class="fr-badge-line"><i class="fr-badge">Suggested</i> Not a recording point in the drawing. Proposed so the wrong tyre can never leave.</p>',
			'<label class="fr-sub" for="fr-dcustomer">Customer</label>',
			'<input id="fr-dcustomer" class="fr-input" autocomplete="off" placeholder="Start typing the customer\'s name">',
			'<div class="fr-picklist" data-list="customer"></div>',
		].join(''));
		this.bind_back();
		let timer = null;
		this.$root.find('#fr-dcustomer').on('input', (e) => {
			clearTimeout(timer);
			const txt = e.target.value;
			timer = setTimeout(() => fr_call('customers', { txt: txt }).then((rows) => {
				const $list = this.$root.find('[data-list="customer"]');
				$list.html((rows || []).slice(0, 8).map((c) => '<button type="button" class="fr-pick" data-customer="' + esc(c.name) + '">' + esc(c.customer_name) + '</button>').join(''));
				$list.find('[data-customer]').on('click', (ev) => fr_call('delivery_list', { customer: $(ev.currentTarget).attr('data-customer') })
					.then((list) => this.draw_delivery(stage, list, new Set())));
			}), 200);
		});
	}

	draw_delivery(stage, list, ticked) {
		const rows = list.tyres.map((t) => {
			const on = ticked.has(t.job_card);
			const state = !t.due ? '<span class="fr-notdue">Waiting for its invoice</span>' : on ? '<span class="fr-due">Checked</span>' : '<span class="fr-muted">Check its number</span>';
			return '<li class="' + (on ? 'is-on' : '') + '">' + (on ? fr_icon('tick') : fr_icon('tyre')) + '<span>' + esc(t.serial) + '</span><span class="fr-muted">' +
				esc([t.size, t.brand].filter(Boolean).join(' · ')) + '</span>' + state + '</li>';
		}).join('');
		this.render([
			this.header(list.customer_name, list.tyres.length + ' tyre' + (list.tyres.length === 1 ? '' : 's') + ' at the branch for this customer'),
			'<ul class="fr-loadlist fr-deliverlist">' + (rows || '<li class="fr-muted">Nothing waiting for this customer.</li>') + '</ul>',
			'<div class="fr-refusal" role="alert" hidden></div>',
			'<div class="fr-entry"><span class="fr-entry-label">Check each tyre: number ends</span><span class="fr-digits">—</span></div>',
			this.keypad_html(),
			ticked.size ? '<button type="button" class="fr-go fr-wide" data-act="handover">' + fr_icon('hand') + 'Hand over ' + ticked.size + ' tyre' + (ticked.size === 1 ? '' : 's') + '</button>' : '',
		].join(''));
		this.$root.find('[data-act="home"]').off('click').on('click', () => this.deliver(stage));
		this.bind_keypad((digits) => {
			if (!digits || digits.length < 3) return;
			fr_call('check_delivery', { customer: list.customer, digits: digits }).then((r) => {
				const $refusal = this.$root.find('.fr-refusal');
				if (r.refused) {
					$refusal.removeAttr('hidden').html(fr_icon('x', 'fr-icon-lg') + '<span>' + esc(r.refused) + '</span>');
					return;
				}
				const match = list.tyres.find((t) => r.matches.indexOf(t.job_card) !== -1 && t.due);
				if (match) {
					ticked.add(match.job_card);
					this.draw_delivery(stage, list, ticked);
				}
			});
		});
		this.$root.find('[data-act="handover"]').on('click', () => fr_call('deliver', { customer: list.customer, jobs: Array.from(ticked), operator: this.operator })
			.then((r) => { this.toast('Handed over: ' + r.delivered.join(', ')); this.draw_delivery(stage, r.list, new Set()); }));
	}
}
