// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Assignment', {
	refresh: function(frm) {
		// Thêm button để HR có thể thêm nhiều nhân viên vào khóa học
		if (frappe.user_roles.includes('Training HR') || frappe.user_roles.includes('System Manager')) {
			frm.add_custom_button(__('Thêm nhân viên vào khóa học'), function() {
				show_add_employees_dialog(frm);
			}, __('Actions'));
		}

		// Button để enroll vào LMS nếu chưa enroll
		if (!frm.is_new() && frm.doc.employee && frm.doc.lms_course) {
			frappe.db.get_value('Employee', frm.doc.employee, 'user_id', (r) => {
				if (r && r.user_id) {
					// Use get_list instead of exists to avoid filter issues
					frappe.db.get_list('LMS Enrollment', {
						filters: {
							member: r.user_id,
							course: frm.doc.lms_course
						},
						limit: 1
					}).then((enrollments) => {
						if (!enrollments || enrollments.length === 0) {
							frm.add_custom_button(__('Enroll vào LMS'), function() {
								enroll_employee_in_course(frm);
							}, __('Actions'));
						}
					});
				}
			});
		}
	},

	lms_course: function(frm) {
		// Khi chọn khóa học, tự động lấy completion_date từ Training Plan nếu có
		if (frm.doc.lms_course && frm.doc.training_plan) {
			frappe.db.get_doc('Training Plan', frm.doc.training_plan).then((plan) => {
				if (plan.plan_details) {
					const plan_item = plan.plan_details.find(item => item.lms_course === frm.doc.lms_course);
					if (plan_item && plan_item.completion_date) {
						frm.set_value('completion_date', plan_item.completion_date);
					}
				}
			});
		}
	},

	training_plan: function(frm) {
		// Khi chọn training plan, tự động lấy completion_date từ plan item
		if (frm.doc.training_plan && frm.doc.lms_course) {
			frappe.db.get_doc('Training Plan', frm.doc.training_plan).then((plan) => {
				if (plan.plan_details) {
					const plan_item = plan.plan_details.find(item => item.lms_course === frm.doc.lms_course);
					if (plan_item && plan_item.completion_date) {
						frm.set_value('completion_date', plan_item.completion_date);
					}
				}
			});
		}
	}
});

function show_add_employees_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: __('Thêm nhân viên vào khóa học'),
		fields: [
			{
				fieldtype: 'Link',
				fieldname: 'lms_course',
				label: __('Khóa học'),
				options: 'LMS Course',
				reqd: 1,
				get_query: function() {
					return {
						filters: {
							published: 1
						}
					};
				}
			},
			{
				fieldtype: 'Link',
				fieldname: 'training_plan',
				label: __('Kế hoạch đào tạo (tùy chọn)'),
				options: 'Training Plan',
				get_query: function() {
					return {
						filters: {
							status: ['in', ['Draft', 'Submitted', 'Approved']]
						}
					};
				}
			},
			{
				fieldtype: 'MultiSelectPills',
				fieldname: 'employees',
				label: __('Chọn nhân viên'),
				reqd: 1,
				get_data: function(txt) {
					return frappe.db.get_link_options('Employee', txt, {
						status: 'Active'
					});
				}
			},
			{
				fieldtype: 'Date',
				fieldname: 'completion_date',
				label: __('Deadline'),
				reqd: 1
			}
		],
		primary_action_label: __('Thêm'),
		primary_action: function(values) {
			if (!values.employees || values.employees.length === 0) {
				frappe.msgprint(__('Vui lòng chọn ít nhất một nhân viên'));
				return;
			}

			dialog.hide();
			add_employees_to_course(values);
		}
	});

	dialog.show();
}

function add_employees_to_course(values) {
	let employees = values.employees;
	if (typeof employees === 'string') {
		employees = employees.split(',').map(e => e.trim());
	}

	frappe.call({
		method: 'lms.training.api.add_employees_to_course',
		args: {
			employees: employees,
			lms_course: values.lms_course,
			training_plan: values.training_plan || null,
			completion_date: values.completion_date
		},
		freeze: true,
		freeze_message: __('Đang thêm nhân viên vào khóa học...'),
		callback: function(r) {
			if (r.message) {
				frappe.msgprint({
					title: __('Thành công'),
					message: __('Đã thêm {0} nhân viên vào khóa học', [r.message.added]),
					indicator: 'green'
				});
				
				if (r.message.skipped > 0) {
					frappe.msgprint({
						title: __('Thông báo'),
						message: __('{0} nhân viên đã được gán khóa học này trước đó', [r.message.skipped]),
						indicator: 'orange'
					});
				}

				// Refresh list view
				if (cur_list) {
					cur_list.refresh();
				}
			}
		}
	});
}

function enroll_employee_in_course(frm) {
	frappe.call({
		method: 'lms.training.api.enroll_employee_in_lms',
		args: {
			assignment_name: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Đang enroll nhân viên vào LMS...'),
		callback: function(r) {
			if (r.message) {
				frappe.msgprint({
					title: __('Thành công'),
					message: __('Đã enroll nhân viên vào khóa học LMS'),
					indicator: 'green'
				});
				frm.reload_doc();
			}
		}
	});
}

// List view settings
frappe.listview_settings['Training Assignment'] = {
	add_fields: ['status', 'progress', 'completion_date'],
	get_indicator: function(doc) {
		if (doc.status === 'Completed') {
			return [__('Completed'), 'green', 'status,=,Completed'];
		} else if (doc.status === 'In Progress') {
			return [__('In Progress'), 'blue', 'status,=,In Progress'];
		} else if (doc.status === 'Overdue') {
			return [__('Overdue'), 'red', 'status,=,Overdue'];
		} else {
			return [__('Pending'), 'orange', 'status,=,Pending'];
		}
	},
	formatters: {
		progress: function(value) {
			if (value === null || value === undefined) {
				return '0%';
			}
			return value + '%';
		}
	}
};

