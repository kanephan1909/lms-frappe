"""
File này chứa tất cả các API (@frappe.whitelist) cho module Training.
Các API này được gọi từ frontend (JavaScript) hoặc từ các DocType khác.

Location: apps/lms/lms/training/api.py
Import path: lms.training.api
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_training_dashboard_stats():
	"""
	Trả về thống kê tổng quan cho module Training.

	Được gọi từ:
	- Dashboard hoặc các trang thống kê frontend
	
	Cách gọi:
		method: 'lms.training.api.get_training_dashboard_stats'
	
	Returns:
		dict với keys:
		- total_assignments: Tổng số Training Assignment
		- status_counts: Dict số lượng theo từng trạng thái (Pending / In Progress / Completed / Overdue)
	"""
	# Kiểm tra quyền: Chỉ Training HR, Training Manager, Training Approver và System Manager
	user_roles = frappe.get_roles()
	allowed_roles = ["Training HR", "Training Manager", "Training Approver", "System Manager"]
	if not any(role in user_roles for role in allowed_roles):
		frappe.throw(_("Bạn không có quyền xem thống kê Training Dashboard"), frappe.PermissionError)
	# Tổng số assignment
	total_assignments = frappe.db.count("Training Assignment")

	# Đếm theo trạng thái
	status_rows = frappe.get_all(
		"Training Assignment",
		fields=["status", "count(name) as count"],
		group_by="status",
		as_list=False,
	)

	status_counts = {
		"Pending": 0,
		"In Progress": 0,
		"Completed": 0,
		"Overdue": 0,
	}

	for row in status_rows:
		if row.get("status") in status_counts:
			status_counts[row["status"]] = row.get("count", 0) or 0

	return {
		"total_assignments": total_assignments,
		"status_counts": status_counts,
	}

def _enroll_in_lms_course(user, course):
	"""
	Helper function: Enroll user vào LMS course.
	
	Không phải API public, chỉ được gọi nội bộ bởi các hàm khác trong module này.
	Không có @frappe.whitelist() nên không thể gọi trực tiếp từ frontend.
	
	Returns:
		bool: True nếu enroll thành công, False nếu đã tồn tại, raise Exception nếu lỗi
	"""
	# Check if enrollment already exists using SQL query
	existing = frappe.db.sql(
		"""
		SELECT name
		FROM `tabLMS Enrollment`
		WHERE member = %s AND course = %s
		LIMIT 1
		""",
		(user, course),
	)

	if existing:
		return False  # Đã tồn tại enrollment

	# Validate user và course tồn tại
	if not frappe.db.exists("User", user):
		raise ValueError(f"User {user} không tồn tại")
	if not frappe.db.exists("LMS Course", course):
		raise ValueError(f"LMS Course {course} không tồn tại")
	
	try:
		enrollment = frappe.get_doc(
			{
				"doctype": "LMS Enrollment",
				"member": user,
				"course": course,
				"member_type": "Student",
			}
		)
		enrollment.insert(ignore_permissions=True)
		return True  # Enroll thành công
	except Exception as e:
		# Log error nhưng vẫn raise để caller biết
		frappe.log_error(f"Failed to enroll {user} in course {course}: {str(e)}")
		raise


@frappe.whitelist()
def add_employees_to_course(employees, lms_course, training_plan=None, completion_date=None):
	"""
	Thêm nhiều nhân viên vào một khóa học.

	Được gọi từ:
		File: apps/lms/lms/training/doctype/training_assignment/training_assignment.js
		Hàm: add_employees_to_course(values)
		Khi: User click nút "Thêm nhân viên vào khóa học" trong Training Assignment form
	
	Cách gọi từ JS:
		frappe.call({
			method: 'lms.training.api.add_employees_to_course',
			args: {
				employees: employees,
				lms_course: values.lms_course,
				training_plan: values.training_plan || null,
				completion_date: values.completion_date
			}
		})

	Args:
		employees: List hoặc JSON/string danh sách employee name
		lms_course: Tên LMS Course
		training_plan: Tên Training Plan (optional)
		completion_date: Deadline
	
	Returns:
		dict với keys:
		- added: Số nhân viên đã thêm thành công
		- skipped: Số nhân viên đã bỏ qua (đã tồn tại assignment)
	"""
	# Kiểm tra quyền: Chỉ Training HR và System Manager
	user_roles = frappe.get_roles()
	if "Training HR" not in user_roles and "System Manager" not in user_roles:
		frappe.throw(_("Bạn không có quyền thêm nhân viên vào khóa học"), frappe.PermissionError)
	
	# Validate LMS Course tồn tại
	if not frappe.db.exists("LMS Course", lms_course):
		frappe.throw(_("Khóa học {0} không tồn tại").format(lms_course))
	if isinstance(employees, str):
		import json

		try:
			employees = json.loads(employees)
		except Exception:
			employees = [e.strip() for e in employees.split(",")]

	added = 0
	skipped = 0

	for employee in employees:
		# Check if assignment already exists
		existing = frappe.db.exists(
			"Training Assignment",
			{
				"employee": employee,
				"lms_course": lms_course,
				"training_plan": training_plan or "",
			},
		)

		if existing:
			skipped += 1
			continue

		# Create new assignment
		assignment = frappe.get_doc(
			{
				"doctype": "Training Assignment",
				"employee": employee,
				"lms_course": lms_course,
				"training_plan": training_plan or "",
				"status": "Pending",
				"completion_date": completion_date,
			}
		)
		assignment.insert(ignore_permissions=True)
		added += 1

		# Enroll employee in LMS course if user_id exists
		user_id = frappe.db.get_value("Employee", employee, "user_id")
		if user_id:
			try:
				_enroll_in_lms_course(user_id, lms_course)
			except Exception as e:
				# Log lỗi nhưng không dừng quá trình thêm assignment
				# Vì assignment đã được tạo thành công, chỉ là enroll thất bại
				frappe.log_error(
					f"Failed to enroll employee {employee} (user: {user_id}) in course {lms_course}: {str(e)}",
					"Training Assignment Enrollment Error"
				)

	return {
		"added": added,
		"skipped": skipped,
	}


@frappe.whitelist()
def enroll_employee_in_lms(assignment_name):
	"""
	Enroll nhân viên vào LMS course từ Training Assignment.

	Được gọi từ:
		File: apps/lms/lms/training/doctype/training_assignment/training_assignment.js
		Hàm: enroll_employee_in_course(frm)
		Khi: User click nút "Enroll vào LMS" trong Training Assignment form
	
	Cách gọi từ JS:
		frappe.call({
			method: 'lms.training.api.enroll_employee_in_lms',
			args: {
				assignment_name: frm.doc.name
			}
		})

	Args:
		assignment_name: Tên của Training Assignment document
	
	Returns:
		dict với key "success": True nếu thành công
	"""
	# Kiểm tra quyền: Chỉ Training HR và System Manager
	user_roles = frappe.get_roles()
	if "Training HR" not in user_roles and "System Manager" not in user_roles:
		frappe.throw(_("Bạn không có quyền enroll nhân viên vào LMS"), frappe.PermissionError)
	
	# Kiểm tra quyền đọc Training Assignment
	if not frappe.has_permission("Training Assignment", "read", assignment_name):
		frappe.throw(_("Bạn không có quyền truy cập Training Assignment này"), frappe.PermissionError)
	assignment = frappe.get_doc("Training Assignment", assignment_name)

	if not assignment.employee or not assignment.lms_course:
		frappe.throw(_("Employee và LMS Course là bắt buộc"))

	user_id = frappe.db.get_value("Employee", assignment.employee, "user_id")
	if not user_id:
		frappe.throw(
			_("Nhân viên này chưa có user_id. Vui lòng liên kết user với employee.")
		)

	# Enroll và xử lý kết quả
	try:
		enrolled = _enroll_in_lms_course(user_id, assignment.lms_course)
		if enrolled:
			return {"success": True, "message": _("Đã enroll nhân viên vào khóa học thành công")}
		else:
			return {"success": True, "message": _("Nhân viên đã được enroll vào khóa học này trước đó")}
	except Exception as e:
		frappe.throw(_("Không thể enroll nhân viên vào khóa học: {0}").format(str(e)))


@frappe.whitelist()
def export_training_plan(plan_name):
	"""
	Export Training Plan ra file Excel/CSV.

	Được gọi từ:
		File: apps/lms/lms/training/doctype/training_plan/training_plan.js
		Hàm: export_training_plan(frm)
		Khi: User click nút "Export" trong Training Plan form (chỉ Training HR và System Manager)
	
	Cách gọi từ JS:
		frappe.call({
			method: 'lms.training.api.export_training_plan',
			args: {
				plan_name: frm.doc.name
			}
		})

	Args:
		plan_name: Tên của Training Plan document
	
	Returns:
		dict với keys:
		- file_url: URL của file đã export
		- filename: Tên file
	"""
	# Kiểm tra quyền: Chỉ Training HR và System Manager
	user_roles = frappe.get_roles()
	if "Training HR" not in user_roles and "System Manager" not in user_roles:
		frappe.throw(_("Bạn không có quyền export Training Plan"), frappe.PermissionError)
	
	# Kiểm tra quyền đọc Training Plan
	if not frappe.has_permission("Training Plan", "read", plan_name):
		frappe.throw(_("Bạn không có quyền truy cập Training Plan này"), frappe.PermissionError)
	from frappe.utils import get_files_path, now_datetime
	from frappe.utils.xlsxutils import make_xlsx
	import os

	plan = frappe.get_doc("Training Plan", plan_name)

	# Prepare data
	data = []
	headers = [
		"Plan Name",
		"Period",
		"Department",
		"Training Manager",
		"Status",
		"Total Cost",
		"LMS Course",
		"Designation",
		"Training Mode",
		"Is Mandatory",
		"Completion Date",
		"Estimated Cost",
	]

	# Add plan details rows
	for item in plan.plan_details:
		row = [
			plan.plan_name,
			plan.period,
			plan.department or "",
			plan.training_manager,
			plan.status,
			plan.total_estimated_cost or 0,
			item.lms_course,
			item.designation,
			item.training_mode,
			1 if item.is_mandatory else 0,
			item.completion_date or "",
			item.estimated_cost or 0,
		]
		data.append(row)

	# Create xlsx file
	xlsx_data = [headers] + data
	xlsx_file = make_xlsx(xlsx_data, "Training Plan")

	# Save file
	timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
	filename = f"Training_Plan_{plan_name}_{timestamp}.xlsx"
	filepath = os.path.join(get_files_path(), filename)

	with open(filepath, "wb") as f:
		f.write(xlsx_file.getvalue())

	# Create file document - File phải là private để bảo mật thông tin
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"file_url": f"/files/{filename}",
			"is_private": 1,  # Đặt là private để bảo mật
			"attached_to_doctype": "Training Plan",
			"attached_to_name": plan_name,
		}
	)
	file_doc.insert(ignore_permissions=True)

	return {
		"file_url": file_doc.file_url,
		"filename": filename,
	}


@frappe.whitelist()
def import_training_plan(file_url, update_existing=0):
	"""
	Import Training Plan từ file Excel/CSV.

	Được gọi từ:
		File: apps/lms/lms/training/doctype/training_plan/training_plan.js
		Hàm: import_training_plan(values, frm, listview)
		Khi: User click nút "Import" trong Training Plan List View (chỉ Training HR và System Manager)
	
	Cách gọi từ JS:
		frappe.call({
			method: 'lms.training.api.import_training_plan',
			args: {
				file_url: values.import_file,
				update_existing: values.update_existing || 0
			}
		})

	Args:
		file_url: URL của file Excel/CSV đã upload
		update_existing: 0 hoặc 1 - có cập nhật plan đã tồn tại không
	
	Returns:
		dict với keys:
		- imported: Số plan đã import mới
		- updated: Số plan đã cập nhật
	"""
	# Kiểm tra quyền: Chỉ Training HR và System Manager
	user_roles = frappe.get_roles()
	if "Training HR" not in user_roles and "System Manager" not in user_roles:
		frappe.throw(_("Bạn không có quyền import Training Plan"), frappe.PermissionError)
	from frappe.utils.csvutils import read_csv_content
	from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
	from frappe.utils import flt

	# Get file doc to check extension
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	extension = file_doc.get_extension()[1].lstrip(".")

	# Read file based on extension
	if extension in ("xlsx", "xls"):
		try:
			rows = read_xlsx_file_from_attached_file(file_url=file_url)
		except Exception as e:
			frappe.throw(_("Không thể đọc file Excel: {0}").format(str(e)))
	elif extension == "csv":
		try:
			content = file_doc.get_content()
			rows = read_csv_content(content)
		except Exception as e:
			frappe.throw(_("Không thể đọc file CSV: {0}").format(str(e)))
	else:
		frappe.throw(
			_("File phải có định dạng Excel (.xlsx, .xls) hoặc CSV (.csv)")
		)

	if not rows or len(rows) < 2:
		frappe.throw(_("File không có dữ liệu"))

	# Get headers
	headers = [h.strip() if isinstance(h, str) else str(h) for h in rows[0]]

	# Validate required columns
	required_columns = [
		"Plan Name",
		"LMS Course",
		"Designation",
		"Training Mode",
		"Completion Date",
	]
	missing_columns = [col for col in required_columns if col not in headers]
	if missing_columns:
		frappe.throw(
			_("File thiếu các cột bắt buộc: {0}").format(", ".join(missing_columns))
		)

	imported = 0
	updated = 0

	# Group data by Plan Name
	plan_data = {}
	for row in rows[1:]:
		if len(row) < len(headers):
			continue

		row_dict = dict(zip(headers, row))
		plan_name = (
			str(row_dict.get("Plan Name", "")).strip()
			if row_dict.get("Plan Name")
			else ""
		)

		if not plan_name:
			continue

		if plan_name not in plan_data:
			plan_data[plan_name] = []
		plan_data[plan_name].append(row_dict)

	# Process each plan
	for plan_name, plan_rows in plan_data.items():
		# Get plan data from first row
		first_row = plan_rows[0]

		# Check if plan exists
		existing_plan = frappe.db.exists(
			"Training Plan", {"plan_name": plan_name}
		)

		if existing_plan and not update_existing:
			continue

		# Create or update plan
		if existing_plan:
			plan = frappe.get_doc("Training Plan", existing_plan)
			# Bảo vệ: Không cho phép cập nhật Training Plan đã được Approved
			# Chỉ cho phép cập nhật Draft hoặc Submitted
			if plan.status == "Approved":
				frappe.throw(
					_("Không thể cập nhật Training Plan '{0}' đã được Approved. Vui lòng tạo plan mới hoặc chỉnh sửa plan ở trạng thái Draft/Submitted.").format(plan_name),
					title=_("Không thể cập nhật")
				)
			# Kiểm tra quyền cập nhật
			if not frappe.has_permission("Training Plan", "write", existing_plan):
				frappe.throw(
					_("Bạn không có quyền cập nhật Training Plan '{0}'").format(plan_name),
					frappe.PermissionError
				)
			updated += 1
		else:
			plan = frappe.new_doc("Training Plan")
			plan.plan_name = plan_name
			imported += 1

		# Set plan fields
		if first_row.get("Period"):
			period = str(first_row.get("Period")).strip()
			if frappe.db.exists("Training Period", period):
				plan.period = period

		if first_row.get("Department"):
			dept = str(first_row.get("Department")).strip()
			if frappe.db.exists("Department", dept):
				plan.department = dept

		if first_row.get("Training Manager"):
			manager = str(first_row.get("Training Manager")).strip()
			if frappe.db.exists("User", manager):
				plan.training_manager = manager

		# Xử lý status: Kiểm tra quyền của user
		user_roles = frappe.get_roles()
		file_status = str(first_row.get("Status", "")).strip() if first_row.get("Status") else ""
		
		# Nếu user là Training HR (không có quyền Manager/Approver)
		if "Training HR" in user_roles and "Training Manager" not in user_roles and "Training Approver" not in user_roles:
			# Training HR chỉ có thể set Draft hoặc Submitted
			if file_status in ["Approved", "Rejected"]:
				# Tự động chuyển về Draft nếu file có status không hợp lệ
				plan.status = "Draft"
			elif file_status in ["Draft", "Submitted"]:
				plan.status = file_status
			else:
				plan.status = "Draft"
		else:
			# System Manager hoặc Training Manager/Approver có thể set bất kỳ status nào
			if file_status:
				plan.status = file_status
			else:
				plan.status = "Draft"

		# Clear existing plan_details
		plan.plan_details = []

		# Add plan details
		for row in plan_rows:
			lms_course = (
				str(row.get("LMS Course", "")).strip()
				if row.get("LMS Course")
				else ""
			)
			designation = (
				str(row.get("Designation", "")).strip()
				if row.get("Designation")
				else ""
			)

			if not lms_course or not designation:
				continue
			
			# Kiểm tra xem LMS Course có tồn tại không
			if not frappe.db.exists("LMS Course", lms_course):
				frappe.log_error(
					f"LMS Course '{lms_course}' không tồn tại, bỏ qua dòng này",
					"Training Plan Import"
				)
				continue
			
			# Kiểm tra xem Designation có tồn tại không
			if not frappe.db.exists("Designation", designation):
				frappe.log_error(
					f"Designation '{designation}' không tồn tại, bỏ qua dòng này",
					"Training Plan Import"
				)
				continue

			plan.append(
				"plan_details",
				{
					"lms_course": lms_course,
					"designation": designation,
					"training_mode": str(
						row.get("Training Mode", "")
					).strip()
					if row.get("Training Mode")
					else "Online",
					"is_mandatory": 1
					if str(row.get("Is Mandatory", "0")).strip()
					in ["1", "True", "true", "Yes", "yes"]
					else 0,
					"completion_date": row.get("Completion Date") or None,
					"estimated_cost": flt(row.get("Estimated Cost", 0)),
				},
			)

		# Kiểm tra xem plan có ít nhất một plan_detail không
		if not plan.plan_details or len(plan.plan_details) == 0:
			frappe.log_error(
				f"Plan '{plan_name}' không có plan_details hợp lệ, bỏ qua",
				"Training Plan Import"
			)
			continue
		
		# Save plan
		try:
			if not existing_plan:
				plan.insert(ignore_permissions=True)
			else:
				plan.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(
				f"Error importing plan {plan_name}: {str(e)}"
			)
			frappe.throw(
				_("Lỗi khi import kế hoạch {0}: {1}").format(
					plan_name, str(e)
				)
			)

	return {
		"imported": imported,
		"updated": updated,
	}
