// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Plan', {
	refresh: function(frm) {
		// Format hiển thị period để hiển thị tên thay vì ID
		if (frm.doc.period && frm.fields_dict.period) {
			frappe.db.get_value('Training Period', frm.doc.period, 'period_name', (r) => {
				if (r && r.period_name) {
					// Đợi DOM render xong rồi mới cập nhật
					setTimeout(() => {
						const periodField = frm.fields_dict.period;
						if (periodField && periodField.$input) {
							// Tìm element hiển thị text của link field
							const linkWrapper = periodField.$input.closest('.form-group');
							if (linkWrapper.length > 0) {
								// Tìm link-content hoặc link-select
								let linkContent = linkWrapper.find('.link-content');
								if (linkContent.length === 0) {
									linkContent = linkWrapper.find('.link-select .link-content');
								}
								if (linkContent.length > 0) {
									// Nếu đang hiển thị ID, thay bằng tên
									const currentText = linkContent.text().trim();
									if (currentText === frm.doc.period || currentText === '') {
										linkContent.text(r.period_name);
									}
								}
								// Set title attribute
								periodField.$input.attr('title', r.period_name);
							}
						}
					}, 300);
				}
			});
		}

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

		// Thêm nút Export cho Training HR và System Manager ở header (bên trái nút Save)
		// Export chỉ có ý nghĩa khi đã có kế hoạch (export kế hoạch hiện tại)
		if ((frappe.user_roles.includes('Training HR') || frappe.user_roles.includes('System Manager')) && !frm.is_new()) {
			// Thêm nút Export bên trái nút Save
			frm.page.add_inner_button(__('Export'), function() {
				export_training_plan(frm);
			}, __('Actions'));
		}
	},

	onload: function(frm) {
		// Set default status cho Training HR
		if (frm.is_new() && frappe.user_roles.includes('Training HR')) {
			frm.set_value('status', 'Draft');
		}
	},

	period: function(frm) {
		// Khi period thay đổi, cập nhật hiển thị tên
		if (frm.doc.period && frm.fields_dict.period) {
			frappe.db.get_value('Training Period', frm.doc.period, 'period_name', (r) => {
				if (r && r.period_name) {
					// Đợi DOM render xong rồi mới cập nhật
					setTimeout(() => {
						const periodField = frm.fields_dict.period;
						if (periodField && periodField.$input) {
							const linkWrapper = periodField.$input.closest('.form-group');
							if (linkWrapper.length > 0) {
								let linkContent = linkWrapper.find('.link-content');
								if (linkContent.length === 0) {
									linkContent = linkWrapper.find('.link-select .link-content');
								}
								if (linkContent.length > 0) {
									const currentText = linkContent.text().trim();
									if (currentText === frm.doc.period || currentText === '') {
										linkContent.text(r.period_name);
									}
								}
								periodField.$input.attr('title', r.period_name);
							}
						}
					}, 300);
				}
			});
		}
	}
});

// Export Training Plan function (Form view)
function export_training_plan(frm) {
	frappe.call({
		method: 'lms.training.api.export_training_plan',
		args: {
			plan_name: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Đang xuất kế hoạch đào tạo...'),
		callback: function(r) {
			if (r.message) {
				// Download file
				const link = document.createElement('a');
				link.href = r.message.file_url;
				link.download = r.message.filename;
				link.click();
				
				frappe.msgprint({
					title: __('Thành công'),
					message: __('Đã xuất kế hoạch đào tạo thành công'),
					indicator: 'green'
				});
			}
		}
	});
}