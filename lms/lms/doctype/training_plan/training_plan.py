# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class TrainingPlan(Document):
	def validate(self):
		self.validate_plan_details()
		self.calculate_total_cost()
		self.validate_status_change()
	
	def validate_plan_details(self):
		if not self.plan_details:
			frappe.throw(_("Please add at least one item in Plan Details"))
		
		for item in self.plan_details:
			if item.completion_date:
				# Validate completion date is within period
				period = frappe.get_doc("Training Period", self.period)
				completion_date = getdate(item.completion_date)
				if completion_date < period.start_date or completion_date > period.end_date:
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
	
	def validate_status_change(self):
		"""Validate that Training HR can only set status to Draft or Submitted"""
		user_roles = frappe.get_roles()
		
		# Training HR chỉ có thể set status = Draft hoặc Submitted
		if "Training HR" in user_roles and "Training Manager" not in user_roles and "Training Approver" not in user_roles:
			if self.status in ["Approved", "Rejected"]:
				frappe.throw(
					_("Training HR không có quyền approve hoặc reject Training Plan. Vui lòng submit để Training Manager duyệt."),
					title=_("Không có quyền")
				)
		
		# Training Manager/Approver chỉ có thể approve/reject khi status = Submitted
		if ("Training Manager" in user_roles or "Training Approver" in user_roles) and "Training HR" not in user_roles:
			if self.status == "Approved" and self.has_value_changed("status"):
				# Chỉ cho phép approve từ Submitted
				if self.get_doc_before_save() and self.get_doc_before_save().status != "Submitted":
					frappe.throw(
						_("Chỉ có thể approve Training Plan từ trạng thái Submitted."),
						title=_("Lỗi trạng thái")
					)
			elif self.status == "Rejected" and self.has_value_changed("status"):
				# Chỉ cho phép reject từ Submitted
				if self.get_doc_before_save() and self.get_doc_before_save().status != "Submitted":
					frappe.throw(
						_("Chỉ có thể reject Training Plan từ trạng thái Submitted."),
						title=_("Lỗi trạng thái")
					)
	
	def on_trash(self):
		"""Validate deletion - Training HR chỉ có thể xóa Draft hoặc Submitted plans"""
		user_roles = frappe.get_roles()
		
		# Training HR chỉ có thể xóa Draft hoặc Submitted plans
		if "Training HR" in user_roles and "Training Manager" not in user_roles and "Training Approver" not in user_roles:
			if self.status in ["Approved", "Rejected"]:
				frappe.throw(
					_("Không thể xóa Training Plan đã được approve hoặc reject. Chỉ có thể xóa các plan ở trạng thái Draft hoặc Submitted."),
					title=_("Không thể xóa")
				)
	
	def on_update(self):
		# Send notification when status changes to Submitted
		if self.status == "Submitted" and self.has_value_changed("status"):
			self.send_submission_notification()
		
		# When status changes to Approved, create Training Assignments
		if self.status == "Approved" and self.has_value_changed("status"):
			self.create_training_assignments()
	
	def send_submission_notification(self):
		"""Send notification to Training Manager when plan is submitted"""
		if self.training_manager:
			# Create notification
			frappe.publish_realtime(
				event="notification",
				message={
					"type": "alert",
					"title": _("Training Plan cần duyệt"),
					"message": _("Training Plan {0} đã được gửi để duyệt").format(
						frappe.bold(self.name)
					),
					"indicator": "blue"
				},
				user=self.training_manager
			)
			
			# Create notification document
			try:
				notification = frappe.get_doc({
					"doctype": "Notification Log",
					"for_user": self.training_manager,
					"type": "Alert",
					"document_type": "Training Plan",
					"document_name": self.name,
					"subject": _("Training Plan {0} cần duyệt").format(self.name),
					"email_content": _("Training Plan {0} ({1}) đã được gửi để duyệt. Vui lòng kiểm tra và phê duyệt.").format(
						self.name, self.plan_name
					)
				})
				notification.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Failed to create notification: {str(e)}")
	
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

