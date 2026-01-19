// List View script for Training Plan

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
		// Lưu reference đến listview để sử dụng sau
		window.training_plan_listview = listview;
		
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

		// Thêm nút Import vào List View cho Training HR và System Manager
		const can_import = frappe.user_roles.includes('Training HR') || frappe.user_roles.includes('System Manager');
		console.log('[Training Plan List] onload can_import:', can_import, 'roles:', frappe.user_roles);
		if (can_import) {
			listview.page.add_inner_button(__('Import'), function() {
				show_import_dialog_listview(listview);
			}, __('Actions'));
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

		// Thêm lại nút Import sau khi refresh
		const can_import = frappe.user_roles.includes('Training HR') || frappe.user_roles.includes('System Manager');
		console.log('[Training Plan List] refresh can_import:', can_import, 'roles:', frappe.user_roles);
		if (can_import) {
			listview.page.add_inner_button(__('Import'), function() {
				show_import_dialog_listview(listview);
			}, __('Actions'));
		}
	}
};

// Show import dialog (for list view)
function show_import_dialog_listview(listview) {
	let dialog = new frappe.ui.Dialog({
		title: __('Import Kế hoạch Đào tạo'),
		fields: [
			{
				fieldtype: 'Attach',
				fieldname: 'import_file',
				label: __('Chọn file Excel/CSV'),
				reqd: 1,
				description: __('File phải có định dạng Excel (.xlsx) hoặc CSV với các cột: plan_name, period, department, training_manager, status và các dòng plan_details')
			},
			{
				fieldtype: 'Check',
				fieldname: 'update_existing',
				label: __('Cập nhật nếu đã tồn tại'),
				default: 0
			}
		],
		primary_action_label: __('Import'),
		primary_action: function(values) {
			dialog.hide();
			import_training_plan(values, listview);
		}
	});

	dialog.show();
}

// Import Training Plan function (List view)
function import_training_plan(values, listview) {
	frappe.call({
		method: 'lms.training.api.import_training_plan',
		args: {
			file_url: values.import_file,
			update_existing: values.update_existing || 0
		},
		freeze: true,
		freeze_message: __('Đang import kế hoạch đào tạo...'),
		callback: function(r) {
			if (r.message) {
				frappe.msgprint({
					title: __('Thành công'),
					message: __('Đã import {0} kế hoạch đào tạo thành công', [r.message.imported]),
					indicator: 'green'
				});
				
				if (r.message.updated > 0) {
					frappe.msgprint({
						title: __('Thông báo'),
						message: __('Đã cập nhật {0} kế hoạch đào tạo', [r.message.updated]),
						indicator: 'blue'
					});
				}

				// Refresh list view
				if (listview) {
					listview.refresh();
				} else if (cur_list) {
					cur_list.refresh();
				}
			}
		},
		error: function(r) {
			// Xử lý lỗi
			frappe.msgprint({
				title: __('Lỗi'),
				message: r.message || __('Có lỗi xảy ra khi import kế hoạch đào tạo'),
				indicator: 'red'
			});

			// Refresh listview sau lỗi
			if (listview) {
				setTimeout(() => {
					listview.refresh();
				}, 500);
			} else if (cur_list) {
				setTimeout(() => {
					cur_list.refresh();
				}, 500);
			}
		}
	});
}


