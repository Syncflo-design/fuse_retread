import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FRJobCard(Document):
	"""One tyre's visit, from the branch through the factory and back. Called Job Card on screen.

	Not ERPNext's Job Card: that one hangs off a Work Order, a BOM and a finished item, none of
	which a customer's tyre has. Its stage, next stages and result move only through
	fuse_retread.floor.record_stage, which asks the route engine first.
	"""

	def before_insert(self):
		if not self.company:
			self.company = frappe.db.get_single_value("FR Settings", "company")
		if not self.received_on:
			self.received_on = now_datetime()

	def validate(self):
		if self.casing and not self.customer:
			self.customer = frappe.db.get_value("FR Casing", self.casing, "customer")
