// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Application', {
	onload: function(frm) {
		if(!frm.doc.docstatus > 0){
			frm.trigger("interest_type")
		}
	},
	refresh: function(frm) {
		frm.trigger("toggle_fields")
		frm.trigger("add_toolbar_buttons")
		setTimeout(function() {
			$("[data-fieldname=description]").css("height",94)
		},100)
	},
	loan_type: function(frm){
		frm.set_value("interest_type", frm.doc.loan_type == "Vehiculo" ? "Simple": "Composite")
	},
	gross_loan_amount: function(frm){
		var expense_rate_dec = frm.doc.legal_expense_rate / 100
		var loan_amount = frm.doc.gross_loan_amount * (expense_rate_dec +1)
		frm.set_value("loan_amount", loan_amount)
	},
	interest_type: function(frm){
		var field = frm.doc.interest_type =="Simple"?"simple_rate_of_interest":"composite_rate_of_interest"
		frappe.db.get_value("FM Configuration", "", field, function(data){ 
			frm.set_value("rate_of_interest", data[field]) 
		})
	},
	repayment_method: function(frm) {
		frm.doc.monthly_repayment_amount = frm.doc.repayment_periods = ""
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.set_df_property("monthly_repayment_amount", "reqd", frm.doc.repayment_method=="Repay Fixed Amount per Period")

		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
		frm.set_df_property("repayment_periods", "reqd", frm.doc.repayment_method=="Repay Over Number of Periods")
	},
	add_toolbar_buttons: function(frm) {	
		if (frm.doc.status == "Approved") {
			frm.add_custom_button(__('Customer Loan'), function() {
				frappe.call({
					method: "fm.finance_manager.doctype.loan_application.loan_application.make_loan",
					args: {
						"source_name": frm.doc.name
					},
					callback: function(r) {
						if(!r.exc) {
							var doc = frappe.model.sync(r.message)
							frappe.set_route("Form", r.message.doctype, r.message.name)
						}
					}
				})
			})
		}
	}
})
