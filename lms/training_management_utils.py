# Copyright (c) 2025, Frappe and contributors
# Utility functions for Training Management System

import frappe
from frappe import _


def check_training_setup():
	"""Check if all required DocTypes and settings are properly configured"""
	results = {
		"doctypes": {},
		"naming_series": False,
		"issues": []
	}
	
	# Check if DocTypes exist
	doctypes = ["Training Period", "Training Plan", "Training Plan Item", "Training Assignment"]
	for dt in doctypes:
		exists = frappe.db.exists("DocType", dt)
		results["doctypes"][dt] = exists
		if not exists:
			results["issues"].append(f"DocType '{dt}' not found. Run 'bench migrate' first.")
	
	# Check naming series
	if results["doctypes"].get("Training Plan"):
		meta = frappe.get_meta("Training Plan")
		naming_field = meta.get_field("naming_series")
		if naming_field and naming_field.options:
			results["naming_series"] = "TRN-PLN" in naming_field.options
			if not results["naming_series"]:
				results["issues"].append(
					"Naming Series not configured. Go to Document Naming Settings > Training Plan"
				)
	
	return results


def get_training_statistics(training_plan=None):
	"""Get statistics for training assignments"""
	filters = {}
	if training_plan:
		filters["training_plan"] = training_plan
	
	assignments = frappe.get_all(
		"Training Assignment",
		filters=filters,
		fields=["status", "progress"]
	)
	
	stats = {
		"total": len(assignments),
		"pending": 0,
		"in_progress": 0,
		"completed": 0,
		"overdue": 0,
		"average_progress": 0
	}
	
	total_progress = 0
	for a in assignments:
		status = a.status.lower().replace(" ", "_")
		if status in stats:
			stats[status] += 1
		total_progress += a.progress or 0
	
	if stats["total"] > 0:
		stats["average_progress"] = round(total_progress / stats["total"], 2)
	
	return stats


def sync_all_progress():
	"""Manually sync progress for all training assignments"""
	assignments = frappe.get_all(
		"Training Assignment",
		fields=["name", "employee", "lms_course"]
	)
	
	updated = 0
	for assignment in assignments:
		doc = frappe.get_doc("Training Assignment", assignment.name)
		doc.sync_lms_progress()
		if doc.has_value_changed("progress"):
			doc.save(ignore_permissions=True)
			updated += 1
	
	return updated


@frappe.whitelist()
def get_employee_training_status(employee):
	"""Get training status for a specific employee"""
	if not frappe.db.exists("Employee", employee):
		return {"error": "Employee not found"}
	
	assignments = frappe.get_all(
		"Training Assignment",
		filters={"employee": employee},
		fields=["name", "lms_course", "training_plan", "status", "progress", "completion_date"]
	)
	
	employee_name = frappe.db.get_value("Employee", employee, "employee_name")
	
	return {
		"employee": employee,
		"employee_name": employee_name,
		"assignments": assignments,
		"total": len(assignments),
		"completed": len([a for a in assignments if a.status == "Completed"]),
		"in_progress": len([a for a in assignments if a.status == "In Progress"]),
		"pending": len([a for a in assignments if a.status == "Pending"]),
		"overdue": len([a for a in assignments if a.status == "Overdue"])
	}


@frappe.whitelist()
def get_plan_summary(training_plan):
	"""Get summary for a training plan"""
	if not frappe.db.exists("Training Plan", training_plan):
		return {"error": "Training Plan not found"}
	
	plan = frappe.get_doc("Training Plan", training_plan)
	
	assignments = frappe.get_all(
		"Training Assignment",
		filters={"training_plan": training_plan},
		fields=["employee", "lms_course", "status", "progress"]
	)
	
	# Group by course
	course_stats = {}
	for a in assignments:
		course = a.lms_course
		if course not in course_stats:
			course_stats[course] = {
				"total": 0,
				"completed": 0,
				"in_progress": 0,
				"pending": 0,
				"overdue": 0
			}
		
		course_stats[course]["total"] += 1
		status = a.status.lower().replace(" ", "_")
		if status in course_stats[course]:
			course_stats[course][status] += 1
	
	return {
		"plan_name": plan.plan_name,
		"status": plan.status,
		"period": plan.period,
		"total_assignments": len(assignments),
		"total_cost": plan.total_estimated_cost,
		"course_statistics": course_stats,
		"overall_statistics": get_training_statistics(training_plan)
	}

