import frappe
from frappe.model.document import Document


class FRDispatch(Document):
	"""One load from the factory back to one branch. Open while it fills, Sent when it goes."""

	def before_insert(self):
		if not self.company:
			self.company = frappe.db.get_single_value("FR Settings", "company")
