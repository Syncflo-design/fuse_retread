import re

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class FRSettings(Document):
	def validate(self):
		self.own_prefix = (self.own_prefix or "").strip().upper()
		if not re.fullmatch(r"[A-Z]{1,4}", self.own_prefix):
			frappe.throw("The own-number prefix is one to four letters, such as P.")
		if cint(self.next_own_number) < 1:
			frappe.throw("The next own number must be 1 or more.")
		if cint(self.daily_target) < 0:
			frappe.throw("The daily target cannot be negative.")

	def on_update(self):
		frappe.clear_document_cache("FR Settings", "FR Settings")
