// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('FM Configuration', {
	refresh: function(frm) {
		root_types = {
			"interest_income_account" : "Income",
			"expenses_account" : "Income",
			"payment_account" : "Asset",
			"customer_loan_account" : "Asset"
		}

		fields = [
			"interest_income_account", "expenses_account", 
			"payment_account", "customer_loan_account"
		]

		$.each(fields, function(idx, field) {
			frm.set_query(field, function() {
				return {
					"filters": {
						"company": frm.doc.company,
						"root_type": root_types[field],
						"is_group": 0
					}
				}
			})
		})

		frm.set_query("default_insurance_supplier", function() {
			return {
				"filters": {
					"supplier_type": "Insurance Provider"
				}
			}
		})
		frm.set_query("goods_received_but_not_billed", function() {
			return {
				"filters": {
					"account_type": "Stock Received But Not Billed"
				}
			}
		})
	},
	validate: function(frm) {
		// ok, now let's request the email entered to see if it exists in the system
		frappe.model.get_value('User', { 'email': frm.doc.allocated_to_email }, 'email', function(data) {
			// if by any chance this brings no data, that means the user entered
			// does not exist in the system
			if (!data) {
				// prompts the user with an error message
				frappe.msgprint(
					repl("User %(user)s not found!", { "user": frm.doc.allocated_to_email })
				)

				// let's clear the field
				frm.set_value("allocated_to_email", undefined)

				// this validation failed 
				// let's prevent the user from saving the document
				validated = false
			}
		})
	}
})
