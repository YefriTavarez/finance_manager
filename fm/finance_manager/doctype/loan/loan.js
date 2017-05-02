// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan', {
	onload: function(frm) {
		frm.set_query("loan_application", function() {
			return {
				"filters": {
					"customer": frm.doc.customer,
					"docstatus": 1,
					"status": "Approved"
				}
			}
		})
		
		frm.set_query("interest_income_account", function() {
			return {
				"filters": {
						"company": frm.doc.company,
						"root_type": "Income",
						"is_group": 0
				}
			}
		})

		$.each(["payment_account", "customer_loan_account"], function(i, field) {
			frm.set_query(field, function() {
				return {
					"filters": {
						"company": frm.doc.company,
						"root_type": "Asset",
						"is_group": 0
					}
				}
			})
		})
	},

	refresh: function(frm) {
		if (frm.doc.docstatus == 1 && (frm.doc.status == "Sanctioned" || frm.doc.status == "Partially Disbursed")) {
			frm.add_custom_button(__('Make Disbursement Entry'), function() {
				frm.trigger("make_jv")
			})
		}
		frm.trigger("toggle_fields")
	},
	gross_loan_amount: function(frm){
		var expense_rate_dec = frm.doc.legal_expense_rate / 100
		var loan_amount = frm.doc.gross_loan_amount * (expense_rate_dec +1)
		frm.set_value("loan_amount", loan_amount)
	},
	// make_jv: function(frm) {
	// 	frappe.call({
	// 		args: {
	// 			"customer_loan": frm.doc.name,
	// 			"company": frm.doc.company,
	// 			"customer_loan_account": frm.doc.customer_loan_account,
	// 			"customer": frm.doc.customer,
	// 			"loan_amount": frm.doc.loan_amount,
	// 			"payment_account": frm.doc.payment_account
	// 		},
	// 		method: "erpnext.hr.doctype.loan.loan.make_jv_entry", //pendiente por arreglar LV
	// 		callback: function(r) {
	// 			if (r.message)
	// 				var doc = frappe.model.sync(r.message)[0]
	// 				frappe.set_route("Form", doc.doctype, doc.name)
	// 		}
	// 	})
	// },
	mode_of_payment: function(frm) {
		frappe.call({
			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
			args: {
				"mode_of_payment": frm.doc.mode_of_payment,
				"company": frm.doc.company
			},
			callback: function(r, rt) {
				if(r.message) {
					frm.set_value("payment_account", r.message.account)
				}
			}
		})
	},

	loan_application: function(frm) {
		return frm.call({
			method: "fm.finance_manager.doctype.loan.loan.get_loan_application",
			args: {
				"loan_application": frm.doc.loan_application
			},
			callback: function(response){
				var loan_application = response.message
				if (!loan_application) return
				var array = ["loan_type", "loan_amount", "repayment_method", "monthly_repayment_amount", "repayment_periods", "rate_of_interest"]

				$.each(array, function(idx, field){
					frm.set_value(field, loan_application[field])
				})
			}
		})

	},

	repayment_method: function(frm) {
		frm.trigger("toggle_fields")
	},

	toggle_fields: function(frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
	},
	add_toolbar_buttons: function(frm) {
		if (frm.doc.docstatus == 0 ){
			frm.add_custom_button(('Repayment Schedule'), function() {
				frappe.call({
					type: "GET",
					method: "validate",
					args: {  "docs": frm },
					callback: function(data) {
						console.log(data)
					}
				})
			})
		}
	}
})
