import frappe
from frappe.model.document import Document


class FRChamberLoad(Document):
	"""One cure in one chamber. Loaded, then curing, then done; moved only from the floor screen."""

	def before_insert(self):
		if not self.company:
			self.company = frappe.db.get_single_value("FR Settings", "company")
