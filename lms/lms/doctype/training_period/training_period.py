# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TrainingPeriod(Document):
    def validate(self):
        # Validate Period Name đúng field (period_name)
        if not self.period_name or not str(self.period_name).strip():
            frappe.throw(
                _("Period Name is required. Please enter a name for this training period."),
                title=_("Missing Field")
            )

        if not self.start_date:
            frappe.throw(
                _("Start Date is required. Please select a start date for this training period."),
                title=_("Missing Field")
            )

        if not self.end_date:
            frappe.throw(
                _("End Date is required. Please select an end date for this training period."),
                title=_("Missing Field")
            )

        self.validate_dates()

    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            frappe.throw(
                _("End Date ({0}) cannot be earlier than Start Date ({1}). Please correct the dates.").format(
                    self.end_date, self.start_date
                ),
                title=_("Invalid Date Range")
            )