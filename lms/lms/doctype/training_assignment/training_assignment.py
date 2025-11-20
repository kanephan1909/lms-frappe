# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate


class TrainingAssignment(Document):
	def validate(self):
		self.update_status()
		self.sync_lms_progress()
	
	def update_status(self):
		"""Update status based on progress and deadline"""
		if self.status == "Completed":
			return
		
		if self.completion_date:
			if getdate(self.completion_date) < getdate(today()) and self.progress < 100:
				self.status = "Overdue"
			elif self.progress > 0 and self.progress < 100:
				self.status = "In Progress"
			elif self.progress == 0:
				self.status = "Pending"
	
	def sync_lms_progress(self):
		"""Sync progress from LMS Enrollment"""
		if not self.employee or not self.lms_course:
			return
		
		# Get employee user_id
		user_id = frappe.db.get_value("Employee", self.employee, "user_id")
		if not user_id:
			return
		
		# Get progress from LMS Enrollment
		progress = frappe.db.get_value(
			"LMS Enrollment",
			{
				"member": user_id,
				"course": self.lms_course
			},
			"progress"
		)
		
		if progress is not None:
			self.progress = progress
			if progress == 100:
				self.status = "Completed"
	
	def on_update(self):
		# Auto-update status when progress changes
		if self.has_value_changed("progress"):
			self.update_status()

