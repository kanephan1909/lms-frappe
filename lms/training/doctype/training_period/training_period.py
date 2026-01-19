# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TrainingPeriod(Document):
    def autoname(self):
        """
        Override autoname để đảm bảo name luôn được set từ period_name.
        Điều này giúp hiển thị period_name thay vì ID trong Link fields.
        """
        if self.period_name:
            # Làm sạch period_name: loại bỏ khoảng trắng thừa
            period_name = str(self.period_name).strip()
            
            # Frappe không cho phép một số ký tự trong name, cần sanitize
            # Thay thế khoảng trắng và ký tự đặc biệt không hợp lệ
            import re
            # Giữ lại chữ cái, số, dấu gạch ngang, dấu gạch dưới
            period_name = re.sub(r'[^\w\-]', '-', period_name)
            period_name = re.sub(r'-+', '-', period_name)  # Loại bỏ nhiều dấu gạch ngang liên tiếp
            period_name = period_name.strip('-')
            
            # Đảm bảo name không trống và hợp lệ
            if period_name:
                self.name = period_name
    
    def before_insert(self):
        """
        Đảm bảo name được set từ period_name trước khi insert.
        """
        if self.period_name and not self.name:
            self.autoname()
    
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
        
        # Đảm bảo name được set từ period_name cho record mới
        # Điều này quan trọng để hiển thị period_name thay vì ID trong Link fields
        if self.is_new() and self.period_name:
            # Luôn đảm bảo name được set từ period_name cho record mới
            # Nếu name chưa được set hoặc name khác period_name (có thể là ID tự động)
            if not self.name or self.name != str(self.period_name).strip():
                self.autoname()

    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            frappe.throw(
                _("End Date ({0}) cannot be earlier than Start Date ({1}). Please correct the dates.").format(
                    self.end_date, self.start_date
                ),
                title=_("Invalid Date Range")
            )