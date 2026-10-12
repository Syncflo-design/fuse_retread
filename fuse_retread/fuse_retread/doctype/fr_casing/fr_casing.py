import frappe
from frappe.model.document import Document

from fuse_retread import common


class FRCasing(Document):
	"""One tyre, for life. Its number is the manufacturer's serial or one the factory issued."""

	def before_insert(self):
		# Before naming: the record is named by its number, and staff type numbers both ways.
		self.serial = common.normalise(self.serial)
		if not self.company:
			self.company = frappe.db.get_single_value("FR Settings", "company")

	def validate(self):
		self.serial = common.normalise(self.serial)
		if not self.serial:
			frappe.throw("A tyre needs a number.")
		own = common.is_own_number(self.serial)
		if self.serial_source == "Manufacturer" and own:
			frappe.throw(
				f"{self.serial} has the shape of a number this factory issues ({common.own_prefix()} and digits). "
				"Choose Factory as the source, or check the serial.",
				title="Number clash",
			)
		if self.serial_source == "Factory" and not own:
			frappe.throw(
				f"A factory number is {common.own_prefix()} followed by digits. Issue one from the Receive at "
				"Branch screen rather than typing it.",
				title="Not a factory number",
			)
