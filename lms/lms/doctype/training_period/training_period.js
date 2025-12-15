// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Training Period', {
	refresh: function(frm) {
	},

	validate: function(frm) {
		if (frm.is_new()) {
			// Validate Period Name
			if (!frm.doc.period_name || !String(frm.doc.period_name).trim()) {
				frappe.msgprint({
					title: __('Missing Field'),
					message: __('Please fill in Period Name before saving.'),
					indicator: 'red'
				});
				frappe.validated = false;
				return false;
			}

			// Validate Start Date
			if (!frm.doc.start_date) {
				frappe.msgprint({
					title: __('Missing Field'),
					message: __('Please fill in Start Date before saving.'),
					indicator: 'red'
				});
				frappe.validated = false;
				return false;
			}

			// Validate End Date
			if (!frm.doc.end_date) {
				frappe.msgprint({
					title: __('Missing Field'),
					message: __('Please fill in End Date before saving.'),
					indicator: 'red'
				});
				frappe.validated = false;
				return false;
			}

			// Validate date logic
			if (frm.doc.start_date && frm.doc.end_date) {
				if (new Date(frm.doc.end_date) < new Date(frm.doc.start_date)) {
					frappe.msgprint({
						title: __('Invalid Date'),
						message: __('End Date cannot be earlier than Start Date.'),
						indicator: 'red'
					});
					frappe.validated = false;
					return false;
				}
			}
		}
	},

	period_name: function(frm) {
		// Check for duplicate Period Name (async check, don't block save)
		if (frm.doc.period_name && frm.is_new() && String(frm.doc.period_name).trim()) {
			frappe.db.get_value('Training Period', {period_name: String(frm.doc.period_name).trim()}, 'name', (r) => {
				if (r && r.name) {
					frappe.msgprint({
						title: __('Duplicate Period Name'),
						message: __('Training Period "{0}" already exists. Please use a different name.', [frm.doc.period_name]),
						indicator: 'orange'
					});
				}
			});
		}
	},

	onload: function(frm) {
		// Ensure Period Name field is visible and editable
		if (frm.is_new()) {
			frm.set_df_property('period_name', 'read_only', 0);
		}
	},

	after_save: function(frm) {
		// After save, reload the form to update the status and document name
		// This ensures "Not Saved" indicator is cleared and form shows correct saved state
		if (frm.doc.name && !frm.doc.name.startsWith('new-')) {
			// Document has been saved with a real name, reload to update form state
			frappe.set_route('Form', 'Training Period', frm.doc.name);
		}
	}
});


