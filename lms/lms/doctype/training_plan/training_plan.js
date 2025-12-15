// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Plan', {
	refresh: function(frm) {
		// Ẩn nút Create cho Training Manager và Training Approver
		if (frm.is_new()) {
			if (frappe.user_roles.includes('Training Manager') || 
				frappe.user_roles.includes('Training Approver')) {
				frm.disable_save();
				frappe.msgprint(__('Bạn không có quyền tạo Training Plan. Vui lòng liên hệ Training HR.'));
			}
		}

		// Training HR: Chỉ cho phép Draft hoặc Submitted
		if (!frm.is_new() && frappe.user_roles.includes('Training HR') && 
			!frappe.user_roles.includes('Training Manager') && 
			!frappe.user_roles.includes('Training Approver')) {
			
			// Ẩn/disable status field nếu đang ở Approved/Rejected
			if (frm.doc.status === 'Approved' || frm.doc.status === 'Rejected') {
				frm.set_df_property('status', 'read_only', 1);
				frm.set_df_property('status', 'description', __('Training HR không thể thay đổi status từ Approved/Rejected.'));
			} else {
				// Chỉ cho phép chọn Draft hoặc Submitted
				frm.set_df_property('status', 'options', 'Draft\nSubmitted');
				frm.set_df_property('status', 'read_only', 0);
				frm.set_df_property('status', 'description', __('Training HR chỉ có thể set status là Draft hoặc Submitted.'));
			}
		}

		// Hiển thị buttons Approve/Reject cho Training Manager và Training Approver
		if (!frm.is_new() && 
			(frappe.user_roles.includes('Training Manager') || 
			 frappe.user_roles.includes('Training Approver')) &&
			!frappe.user_roles.includes('Training HR')) {
			
			if (frm.doc.status === 'Submitted') {
				// Button Approve
				frm.add_custom_button(__('Approve'), function() {
					frappe.confirm(
						__('Bạn có chắc chắn muốn duyệt kế hoạch đào tạo này?'),
						function() {
							frm.set_value('status', 'Approved');
							frm.save();
						}
					);
				}, __('Actions'));

				// Button Reject
				frm.add_custom_button(__('Reject'), function() {
					frappe.prompt({
						fieldname: 'rejection_reason',
						fieldtype: 'Small Text',
						label: __('Lý do từ chối'),
						reqd: 1
					}, function(values) {
						frm.set_value('status', 'Rejected');
						frm.save().then(() => {
							// Tạo comment với lý do từ chối
							frappe.call({
								method: 'frappe.desk.doctype.comment.comment.create_comment',
								args: {
									comment_type: 'Comment',
									reference_doctype: 'Training Plan',
									reference_name: frm.doc.name,
									content: __('Lý do từ chối: {0}', [values.rejection_reason])
								}
							});
						});
					});
				}, __('Actions'));
			}
		}

		// Ẩn nút Save cho Training Manager/Approver nếu status không phải Submitted
		if (!frm.is_new() && 
			(frappe.user_roles.includes('Training Manager') || 
			 frappe.user_roles.includes('Training Approver')) &&
			!frappe.user_roles.includes('Training HR')) {
			if (frm.doc.status !== 'Submitted' && frm.doc.status !== 'Draft') {
				frm.set_read_only();
			}
		}
	},

	onload: function(frm) {
		// Set default status cho Training HR
		if (frm.is_new() && frappe.user_roles.includes('Training HR')) {
			frm.set_value('status', 'Draft');
		}
	}
});

// Filter list view cho Training Manager - chỉ thấy Submitted plans
frappe.listview_settings['Training Plan'] = {
	get_filters: function() {
		if (frappe.user_roles.includes('Training Manager') || 
			frappe.user_roles.includes('Training Approver')) {
			// Training Manager chỉ thấy các plan đã submit
			return [['Training Plan', 'status', '=', 'Submitted']];
		}
		// Training HR thấy tất cả
		return [];
	},
	
	onload: function(listview) {
		// Ẩn nút "New" cho Training Manager và Training Approver
		if (frappe.user_roles.includes('Training Manager') || 
			frappe.user_roles.includes('Training Approver')) {
			// Ẩn nút New mặc định
			setTimeout(() => {
				// Tìm và ẩn nút New
				listview.page.$('.btn-primary').each(function() {
					if ($(this).text().trim() === 'New' || $(this).text().trim() === 'Mới') {
						$(this).hide();
					}
				});
				// Ẩn nút trong menu
				listview.page.$('[data-label="New"]').hide();
				listview.page.$('[data-label="Mới"]').hide();
			}, 500);
		}
	},
	
	hide_name_column: false,
	refresh: function(listview) {
		// Ẩn nút New khi refresh
		if (frappe.user_roles.includes('Training Manager') || 
			frappe.user_roles.includes('Training Approver')) {
			setTimeout(() => {
				listview.page.$('.btn-primary').each(function() {
					if ($(this).text().trim() === 'New' || $(this).text().trim() === 'Mới') {
						$(this).hide();
					}
				});
			}, 100);
		}
	}
};

