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
		"""
		Hàm này được gọi TỰ ĐỘNG mỗi khi Training Plan được lưu (save)
		Chạy sau khi validate() thành công
		"""
		# TRƯỜNG HỢP 1: Khi status chuyển thành "Submitted"
		# Training HR vừa submit kế hoạch để duyệt
		if self.status == "Submitted" and self.has_value_changed("status"):
			# Gửi thông báo cho Training Manager
			self.send_submission_notification()
		
		# TRƯỜNG HỢP 2: Khi status chuyển thành "Approved" ← QUAN TRỌNG!
		# Training Manager vừa approve kế hoạch
		if self.status == "Approved" and self.has_value_changed("status"):
			# TỰ ĐỘNG tạo Training Assignment cho tất cả nhân viên phù hợp
			# Đây là nơi gọi hàm create_training_assignments()
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
		"""
		Tự động tạo Training Assignment cho tất cả nhân viên phù hợp với tiêu chí của kế hoạch
		
		Hàm này được gọi TỰ ĐỘNG khi Training Plan được Approve (trong on_update)
		
		Quy trình:
		1. Duyệt qua từng khóa học trong plan_details
		2. Tìm tất cả nhân viên có designation khớp
		3. Tạo Training Assignment cho mỗi nhân viên + mỗi khóa học
		4. Tự động enroll vào LMS nếu nhân viên có user_id
		"""
		assignments_created = 0  # Đếm số lượng Assignment đã tạo
		
		# BƯỚC 1: Duyệt qua từng khóa học trong plan_details
		# Ví dụ: plan_details có 2 khóa học:
		#   - Python Basics (dành cho Developer)
		#   - SQL Advanced (dành cho Developer)
		for item in self.plan_details:
			# BƯỚC 2: Xây dựng bộ lọc để tìm nhân viên phù hợp
			# Bắt đầu với các điều kiện cơ bản
			employee_filters = {
				"designation": item.designation,  # Chức danh phải khớp (ví dụ: "Developer")
				"status": "Active"                 # Chỉ nhân viên đang làm việc
			}
			
			# BƯỚC 3: Thêm điều kiện phòng ban nếu Training Plan có chọn department
			# Nếu plan.department = "IT" thì chỉ tìm nhân viên trong phòng IT
			# Nếu plan.department = None thì tìm tất cả phòng ban
			if self.department:
				employee_filters["department"] = self.department
			
			# BƯỚC 4: Tìm tất cả nhân viên khớp với bộ lọc
			# Ví dụ: Tìm tất cả Employee có:
			#   - designation = "Developer"
			#   - status = "Active"
			#   - department = "IT" (nếu có)
			employees = frappe.get_all(
				"Employee",
				filters=employee_filters,
				fields=["name", "user_id"]  # Chỉ lấy name và user_id để tối ưu
			)
			# Kết quả: employees = [
			#   {"name": "EMP001", "user_id": "user1@example.com"},
			#   {"name": "EMP002", "user_id": "user2@example.com"},
			#   {"name": "EMP003", "user_id": None}  # Nhân viên chưa có tài khoản
			# ]
			
			# BƯỚC 5: Duyệt qua từng nhân viên để tạo Training Assignment
			for employee in employees:
				# BƯỚC 6: Kiểm tra xem Assignment đã tồn tại chưa
				# Tránh tạo duplicate nếu hàm này được gọi nhiều lần
				existing = frappe.db.exists(
					"Training Assignment",
					{
						"employee": employee.name,           # Nhân viên
						"lms_course": item.lms_course,        # Khóa học
						"training_plan": self.name           # Kế hoạch đào tạo
					}
				)
				# existing = True nếu đã có, False nếu chưa có
				
				# BƯỚC 7: Chỉ tạo mới nếu chưa tồn tại
				if not existing:
					# Tạo document Training Assignment mới
					assignment = frappe.get_doc({
						"doctype": "Training Assignment",
						"employee": employee.name,                    # Nhân viên
						"lms_course": item.lms_course,                 # Khóa học
						"training_plan": self.name,                    # Link đến Training Plan
						"status": "Pending",                            # Trạng thái ban đầu
						"completion_date": item.completion_date         # Deadline từ plan_details
					})
					# Lưu vào database
					assignment.insert(ignore_permissions=True)
					assignments_created += 1  # Tăng số lượng đã tạo
					
					# BƯỚC 8: Tự động enroll nhân viên vào LMS course nếu có user_id
					# Chỉ enroll nếu nhân viên đã có tài khoản (user_id không None)
					if employee.user_id:
						# Gọi hàm enroll để tạo LMS Enrollment
						# Nhân viên có thể vào học ngay trên hệ thống LMS
						self.enroll_in_lms_course(employee.user_id, item.lms_course)
					# Nếu không có user_id, Assignment vẫn được tạo nhưng chưa enroll vào LMS
					# Có thể enroll thủ công sau
		
		# BƯỚC 9: Hiển thị thông báo số lượng Assignment đã tạo
		if assignments_created > 0:
			frappe.msgprint(_("Created {0} training assignment(s)").format(assignments_created))
		
		# Ví dụ kết quả:
		# - Plan có 2 khóa học (Python, SQL)
		# - Tìm được 3 nhân viên Developer
		# - Tạo được: 3 x 2 = 6 Training Assignments
		# - Thông báo: "Created 6 training assignment(s)"
	
	def enroll_in_lms_course(self, user, course):
		"""Enroll user in LMS course"""
		# Check if enrollment already exists using SQL query
		existing = frappe.db.sql("""
			SELECT name
			FROM `tabLMS Enrollment`
			WHERE member = %s AND course = %s
			LIMIT 1
		""", (user, course))
		
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


