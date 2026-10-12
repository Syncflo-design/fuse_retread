import frappe
from frappe.model.document import Document
from frappe.utils import cint


class FRStage(Document):
	def validate(self):
		if cint(self.sequence) <= 0:
			frappe.throw("The order is a positive number. Leave gaps (10, 20, 30) so a stage can be added between.")
		if not (self.on_retread or self.on_repair):
			frappe.throw("A stage belongs to at least one route.")
