# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 150
		},
		{
			"fieldname": "designation",
			"label": _("Designation"),
			"fieldtype": "Link",
			"options": "Designation",
			"width": 150
		},
		{
			"fieldname": "has_training",
			"label": _("Has Training"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "total_assignments",
			"label": _("Total Assignments"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "completed",
			"label": _("Completed"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "in_progress",
			"label": _("In Progress"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "pending",
			"label": _("Pending"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "overdue",
			"label": _("Overdue"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "avg_progress",
			"label": _("Avg Progress (%)"),
			"fieldtype": "Percent",
			"width": 120
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			emp.name as employee,
			emp.employee_name,
			emp.department,
			emp.designation,
			CASE 
				WHEN COUNT(DISTINCT ta.name) > 0 THEN 'Có'
				ELSE 'Chưa có'
			END as has_training,
			COUNT(DISTINCT ta.name) as total_assignments,
			SUM(CASE WHEN ta.status = 'Completed' THEN 1 ELSE 0 END) as completed,
			SUM(CASE WHEN ta.status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
			SUM(CASE WHEN ta.status = 'Pending' THEN 1 ELSE 0 END) as pending,
			SUM(CASE WHEN ta.status = 'Overdue' THEN 1 ELSE 0 END) as overdue,
			ROUND(AVG(ta.progress), 2) as avg_progress
		FROM
			`tabEmployee` emp
		LEFT JOIN
			`tabTraining Assignment` ta ON emp.name = ta.employee
		WHERE
			emp.status = 'Active'
			{conditions}
		GROUP BY
			emp.name, emp.employee_name, emp.department, emp.designation
		ORDER BY
			has_training DESC, emp.employee_name
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Format progress and apply has_training filter
	result_data = []
	for row in data:
		if row.avg_progress is None:
			row.avg_progress = 0
		if row.total_assignments is None or row.total_assignments == 0:
			row.total_assignments = 0
			row.has_training = "Chưa có"
		else:
			row.has_training = "Có"
		if row.completed is None:
			row.completed = 0
		if row.in_progress is None:
			row.in_progress = 0
		if row.pending is None:
			row.pending = 0
		if row.overdue is None:
			row.overdue = 0
		
		# Apply has_training filter if specified
		if filters.get("has_training"):
			if filters.get("has_training") == "Có" and row.has_training != "Có":
				continue
			elif filters.get("has_training") == "Chưa có" and row.has_training != "Chưa có":
				continue
		
		result_data.append(row)
	
	return result_data


def get_conditions(filters):
	conditions = ""
	
	if filters.get("employee"):
		conditions += " AND emp.name = %(employee)s"
	
	if filters.get("department"):
		conditions += " AND emp.department = %(department)s"
	
	if filters.get("designation"):
		conditions += " AND emp.designation = %(designation)s"
	
	if filters.get("training_plan"):
		conditions += " AND ta.training_plan = %(training_plan)s"
	
	if filters.get("status"):
		conditions += " AND ta.status = %(status)s"
	
	# Note: has_training filter will be handled in post-processing
	# because it's a computed field based on COUNT
	
	return conditions

