frappe.listview_settings['FR Job Card'] = {
	add_fields: ['status', 'result', 'stage'],
	get_indicator(doc) {
		if (doc.result === 'Rejected' || doc.result === 'Not Retreadable') {
			return [__(doc.result), 'red', 'result,=,' + doc.result];
		}
		const colour = { 'In Progress': 'blue', Dispatched: 'orange', Invoiced: 'purple', Delivered: 'green' }[doc.status] || 'gray';
		return [__(doc.status), colour, 'status,=,' + doc.status];
	},
	onload(listview) {
		// The demo loader, on the Fuse demo site only (site config fuse_demo_site) and for a
		// System Manager. It never appears on a client's site.
		if (!frappe.user.has_role('System Manager') || !frappe.boot.fuse_demo_site) return;
		listview.page.add_menu_item(__('Load Retread Demo'), () => {
			const dialog = new frappe.ui.Dialog({
				title: __('Load Retread Demo'),
				fields: [
					{
						fieldname: 'presenter', fieldtype: 'Data', label: __('Presenter login'), options: 'Email',
						description: __('An existing user. It is given the retread presenter roles, profile and company.'),
					},
					{
						fieldname: 'reset', fieldtype: 'Check', label: __('Start again'),
						description: __('Removes every tyre, job, chamber load and dispatch first, so the dates are fresh for today.'),
					},
				],
				primary_action_label: __('Load'),
				primary_action(values) {
					dialog.hide();
					frappe.call({
						method: 'fuse_retread.demo.retread.load', args: values, freeze: true,
						freeze_message: __('Loading the retread demo…'),
					}).then((r) => {
						frappe.msgprint({ title: __('Retread demo loaded'), message: r.message.summary, indicator: 'green' });
						listview.refresh();
					});
				},
			});
			dialog.show();
		});
	},
};
