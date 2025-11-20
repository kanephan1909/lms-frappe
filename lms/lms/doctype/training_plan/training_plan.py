# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class TrainingPlan(Document):
	def validate(self):
		self.validate_plan_details()
		self.calculate_total_cost()
	
	def validate_plan_details(self):
		if not self.plan_details:
			frappe.throw(_("Please add at least one item in Plan Details"))
		
		for item in self.plan_details:
			if item.completion_date:
				# Validate completion date is within period
				period = frappe.get_doc("Training Period", self.period)
				if item.completion_date < period.start_date or item.completion_date > period.end_date:
					frappe.throw(
						_("Completion Date for course {0} must be within the training period ({1} to {2})").format(
							item.lms_course, period.start_date, period.end_date
						)
					)
	
	def calculate_total_cost(self):
		total = 0
		for item in self.plan_details:
			total += flt(item.estimated_cost or 0)
		self.total_estimated_cost = total
	
	def on_update(self):
		# When status changes to Approved, create Training Assignments
		if self.status == "Approved" and self.has_value_changed("status"):
			self.create_training_assignments()
	
	def create_training_assignments(self):
		"""Create Training Assignment records for all employees matching the plan criteria"""
		assignments_created = 0
		
		for item in self.plan_details:
			# Build employee filters
			employee_filters = {
				"designation": item.designation,
				"status": "Active"
			}
			
			# Add department filter if specified
			if self.department:
				employee_filters["department"] = self.department
			
			# Find all employees with matching designation
			employees = frappe.get_all(
				"Employee",
				filters=employee_filters,
				fields=["name", "user_id"]
			)
			
			for employee in employees:
				# Check if assignment already exists
				existing = frappe.db.exists(
					"Training Assignment",
					{
						"employee": employee.name,
						"lms_course": item.lms_course,
						"training_plan": self.name
					}
				)
				
				if not existing:
					assignment = frappe.get_doc({
						"doctype": "Training Assignment",
						"employee": employee.name,
						"lms_course": item.lms_course,
						"training_plan": self.name,
						"status": "Pending",
						"completion_date": item.completion_date
					})
					assignment.insert(ignore_permissions=True)
					assignments_created += 1
					
					# Enroll employee in LMS course if user_id exists
					if employee.user_id:
						self.enroll_in_lms_course(employee.user_id, item.lms_course)
		
		if assignments_created > 0:
			frappe.msgprint(_("Created {0} training assignment(s)").format(assignments_created))
	
	def enroll_in_lms_course(self, user, course):
		"""Enroll user in LMS course"""
		# Check if enrollment already exists
		existing = frappe.db.exists(
			"LMS Enrollment",
			{
				"member": user,
				"course": course
			}
		)
		
		if not existing:
			try:
				enrollment = frappe.get_doc({
					"doctype": "LMS Enrollment",
					"member": user,
					"course": course,
					"member_type": "Student"
				})
				enrollment.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Failed to enroll {user} in course {course}: {str(e)}")

