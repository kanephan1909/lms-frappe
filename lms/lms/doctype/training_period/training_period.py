# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TrainingPeriod(Document):
	def validate(self):
		self.validate_dates()
	
	def validate_dates(self):
		if self.start_date and self.end_date:
			if self.end_date < self.start_date:
				frappe.throw(_("End Date cannot be earlier than Start Date"))

