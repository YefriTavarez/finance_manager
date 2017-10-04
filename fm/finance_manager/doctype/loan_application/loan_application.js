// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Application', {
	setup: function(frm) {
		frm.add_fetch("customer", "default_currency", "customer_currency")
	},
	onload: function(frm) {
		if (frm.doc.__islocal) {
			frm.trigger("interest_type")
		}

		frm.set_df_property("vehiculo", "reqd", frm.doc.loan_type == "Vehicle")
		frm.set_df_property("vivienda", "reqd", frm.doc.loan_type == "Vivienda")
	},
	refresh: function(frm) {
		frm.trigger("toggle_fields")
		frm.trigger("add_toolbar_buttons")
		setTimeout(function() {
			$("[data-fieldname=description]").css("height", 94)
		}, 100)
	},
	validate: function(frm) {
		// if the customer does not have a default currency set
		if ( !frm.doc.customer_currency ){
			// then set the default company's currency
			frm.set_value("customer_currency", frappe.defaults.get_default("currency"))
		}
	},
	loan_type: function(frm) {
		
		// validate the loan type and set the corresponding interest type
		frm.set_value("interest_type", frm.doc.loan_type == "Vehicle" ? "Simple" : "Composite")

		frm.set_value("asset", "")
		frm.set_df_property("vehiculo", "reqd", frm.doc.loan_type == "Vehicle")
		frm.set_df_property("vivienda", "reqd", frm.doc.loan_type == "Vivienda")
	},
	vehiculo: function(frm) {
		if (frm.doc.vehiculo){
			frm.set_value("asset", frm.doc.vehiculo)
			frm.set_value("vivienda", undefined)
		}
	},
	vivienda: function(frm) {
		if (frm.doc.vivienda){
			frm.set_value("asset", frm.doc.vivienda)
			frm.set_value("vehiculo", undefined)
		}
	},
	gross_loan_amount: function(frm) {
		var expense_rate_dec = flt(frm.doc.legal_expense_rate / 100.000)
		var loan_amount = frm.doc.gross_loan_amount * flt(expense_rate_dec +1.000)
		frm.set_value("loan_amount", loan_amount)
	},
	legal_expense_rate: function(frm) {
		frm.trigger("gross_loan_amount")
	},
	rate_of_interest: function(frm) {
		frm.trigger("gross_loan_amount")
	},
	interest_type: function(frm) {
		// let's validate the interest_type to see what's rate type we are requesting from the server
		var field = frm.doc.interest_type == "Simple" ? "simple_rate_of_interest" : "composite_rate_of_interest"

		frappe.db.get_value("FM Configuration", "", field, function(data) {
			if (!frm.doc.rate_of_interest){
				frm.set_value("rate_of_interest", data[field])
			}
		})
	},
	repayment_method: function(frm) {
		frm.doc.monthly_repayment_amount = frm.doc.repayment_periods = ""
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method == "Repay Fixed Amount per Period")
		frm.set_df_property("monthly_repayment_amount", "reqd", frm.doc.repayment_method == "Repay Fixed Amount per Period")

		frm.toggle_enable("repayment_periods", frm.doc.repayment_method == "Repay Over Number of Periods")
		frm.set_df_property("repayment_periods", "reqd", frm.doc.repayment_method == "Repay Over Number of Periods")
	},
	make_loan: function(frm) {

		// point to the method that we're executing now
		var method = "fm.finance_manager.doctype.loan_application.loan_application.make_loan"
		
		// the args that it requires
		var args = {
			"source_name": frm.docname
		}

		// callback to be executed after the server responds
		var callback = function(response) {

			// check to see if there is something back
			if (!response.message) 
				return 1 // exit code is 1

			var doc = frappe.model.sync(response.message)
			frappe.set_route("Form", response.message.doctype, response.message.name)
		}

		frappe.call({ "method": method, "args": args, "callback": callback })
	},
	add_toolbar_buttons: function(frm) {
		// check to see if the loan is rejected or still opened
		if (frm.doc.status == "Rejected" || frm.doc.status == "Open") 
			return 0 // let's just ignore it

		var callback = function(data) {
			if (data) {
				frappe.set_route("Form", "Loan", data.name)
			} else {
				frm.trigger("make_loan")
			}			
		}

		var customer_loan =  function() {
			frappe.model.get_value("Loan", { "loan_application": frm.docname, "docstatus": ["!=", "2"] }, "name", callback)
		}

		frm.add_custom_button(__('Loan'), customer_loan, "Hacer")
	}
})