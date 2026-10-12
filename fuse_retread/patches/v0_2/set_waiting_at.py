import frappe

from fuse_retread import common, floor


def execute():
	"""Fill Waiting At on Job Cards recorded before the field existed."""
	for job in frappe.get_all("FR Job Card", filters={"status": ["!=", "Delivered"]}, fields=["name", "next_stages"]):
		frappe.db.set_value(
			"FR Job Card", job.name, "waiting_at", floor.waiting_at(common.split(job.next_stages)), update_modified=False
		)
