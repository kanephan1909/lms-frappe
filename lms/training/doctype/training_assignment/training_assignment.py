# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate, flt


class TrainingAssignment(Document):
	def validate(self):
		# Store old progress before syncing
		old_progress = self.progress
		self.sync_lms_progress()
		# Only auto-update status if progress has changed (from LMS sync)
		# This allows manual status changes to be preserved
		if old_progress != self.progress:
			self.update_status()
	
	def update_status(self):
		"""Update status based on progress and deadline"""
		# Don't override if status is already "Completed"
		if self.status == "Completed":
			return
		
		# Handle None progress
		progress = flt(self.progress) or 0
		
		# Auto-update based on progress and deadline
		if self.completion_date:
			if getdate(self.completion_date) < getdate(today()) and progress < 100:
				self.status = "Overdue"
			elif progress > 0 and progress < 100:
				self.status = "In Progress"
			elif progress == 0:
				self.status = "Pending"
		else:
			# If no completion_date, update based on progress only
			if progress == 100:
				self.status = "Completed"
			elif progress > 0:
				self.status = "In Progress"
			else:
				self.status = "Pending"
	
	def sync_lms_progress(self):
		"""Sync progress from LMS Enrollment"""
		if not self.employee or not self.lms_course:
			return
		
		# Get employee user_id
		user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if not user_id:
			return
		
		# Get progress from LMS Enrollment using SQL query to avoid filter issues
		progress = frappe.db.sql("""
			SELECT progress
			FROM `tabLMS Enrollment`
			WHERE member = %s AND course = %s
			LIMIT 1
		""", (user_id, self.lms_course), as_dict=True)
		
		if progress and progress[0].get("progress") is not None:
			self.progress = progress[0].get("progress")
			# Only auto-set to Completed if progress is 100
			# Status will be updated in update_status() if needed
	
	def on_update(self):
		# Auto-update status when progress changes
		if self.has_value_changed("progress"):
			self.update_status()


@frappe.whitelist()
def add_employees_to_course(employees, lms_course, training_plan=None, completion_date=None):
	"""
	API đã được chuyển sang `lms.training.api.add_employees_to_course`.

	Hàm này giữ lại để tránh lỗi nếu còn chỗ gọi cũ
	và sẽ gọi tiếp sang API mới.
	"""
	from lms.lms.training import api as training_api

	return training_api.add_employees_to_course(
		employees=employees,
		lms_course=lms_course,
		training_plan=training_plan,
		completion_date=completion_date,
	)


@frappe.whitelist()
def enroll_employee_in_lms(assignment_name):
	"""
	API đã được chuyển sang `lms.training.api.enroll_employee_in_lms`.

	Hàm này chỉ giữ lại để tránh lỗi nếu còn chỗ gọi cũ,
	và sẽ gọi tiếp sang API mới.
	"""
	from lms.lms.training import api as training_api

	return training_api.enroll_employee_in_lms(assignment_name)

