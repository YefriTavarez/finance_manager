// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan', {
	onload: function(frm) {
		// to filter some link fields
		frm.trigger("set_queries")

		// let's set the default account from the FM Configuration
		frm.trigger("set_account_defaults")
	},
	onload_post_render: function(frm) {
		// this function will just fetch the asset onload time
		// to avoid reduce the complexity of future steps
		var method = "frappe.client.get"

		// set the doctype dinamically as it might change
		var doctype = frm.doc.loan_type == "Vehicle" ? "Vehicle" : "Vivienda"

		// the arguments for the method in the server side
		var args = { "doctype": doctype, "name": frm.doc.asset }

		// code segment to execute after the server responds
		var callback = function(response) {

			// let's place the asset in the doc object
			frm.doc._asset = response.message
		}

		if ( frm.doc.asset ){
			frappe.call({ "method": method, "args": args, "callback": callback }) 
		}
		console.log("run")
	},
	refresh: function(frm) {
		frm.trigger("needs_to_refresh")		
		frm.trigger("toggle_fields")
		frm.trigger("add_buttons")
		frm.trigger("beautify_repayment_table")
	},
	validate: function(frm) {
		frm.trigger("setup")
	},
	needs_to_refresh: function(frm) {
		// check if it's a new doc
		if ( frm.doc.__islocal ) 
			return 0 // let's just ignore it

		var field_list = [
			"modified",
			"paid_by_now"
		]

		var callback = function(data) {
			if (frm.doc.modified != data.modified || frm.doc.paid_by_now != data.paid_by_now){
				// reload the doc because it's out of date
				frm.reload_doc()
			}
		}

		// check the last time it was modified in the DB
		frappe.db.get_value(frm.doctype, frm.docname, field_list, callback)
	},
	gross_loan_amount: function(frm) {
		var expense_rate_dec = frm.doc.legal_expense_rate / 100
		var loan_amount = frm.doc.gross_loan_amount * (expense_rate_dec +1)
		
		frm.set_value("loan_amount", loan_amount)
	},
	make_jv: function(frm) {
		$c('runserverobj', { "docs": frm.doc, "method": "make_jv_entry" }, function(response) {
			// let's see if everything was ok
			if ( !response.message )
				return 1 // exit code is 1

			var doc = frappe.model.sync(response.message)[0]
			frappe.set_route("Form", doc.doctype, doc.name)
		})
	},
	make_payment_entry_old: function(frm) {
		$c('runserverobj', { "docs": frm.doc, "method": "make_payment_entry" }, function(response) {
			// let's see if everything was ok
			if ( !response.message )
				return 1 // exit code is 1

			var doc = frappe.model.sync(response.message)[0]
			frappe.set_route("Form", doc.doctype, doc.name)
		})
	},
	mode_of_payment: function(frm) {

		// check to see if the mode of payment is set
		if ( !frm.doc.mode_of_payment ) 
			return 0 // let's just ignore it

		var method = "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account"

		var args = {
			"mode_of_payment": frm.doc.mode_of_payment,
			"company": frm.doc.company
		}

		var callback = function(response) {

			// set the response body to a local variable
			var data = response.message

			// check to see if the server sent something back
			if ( !data )
				return 0 // let's just ignore it

			// let's set the value
			frm.set_value("payment_account", data.account)
		}
		
		// ok, now we're ready to send the request
		frappe.call({ method: method, args: args, callback: callback })
	},
	set_account_defaults: function(frm) {
		// this method fetch the default accounts from
		// the FM Configuration panel if it exists


		// the method that we're going to execute in the server
		var method = "frappe.client.get"

		// and the arguments that it requires
		var args = { "doctype": "FM Configuration", "name": "FM Configuration" }

		// finally this is the callback to execute when the server finishes
		var callback = function(response) {

			// in case something is wrong with the request
			if (response.exec){
				frappe.throw(__("There was an error while loading the default accounts!"))
			}

			// set the response body to a local variable
			var conf = response.message

			// set the response doc object to a local variable
			var doc = frm.doc

			var fields = [
				"payment_account",
				"mode_of_payment",
				"expenses_account",
				"customer_loan_account",
				"interest_income_account",
				"disbursement_account"
			]

			// set the values
			$.each(fields, function(idx, field) {
				// check to see if the field has value
				if ( !doc[field] ){

					// it has no value, then set it
					frm.set_value(field, conf[field])
				}
			})
		}

		// ok, now we're ready to send the request
		frappe.call({ "method": method, "args": args, "callback": callback })
	},
	loan_application: function(frm) {
		// exit the function and do nothing
		// if loan application is triggered but has not data
		if ( !frm.doc.loan_application )
			return 0 // let's just ignore it

		frm.call({
			"method": "fm.finance_manager.doctype.loan.loan.get_loan_application",
			"args": {
				"loan_application": frm.doc.loan_application
			},
			"callback": function(response) {
				var loan_application = response.message

				// exit the callback if no data came from the SV
				if ( !loan_application )
					return 0 // let's just ignore it

				var field_list = [
					"loan_type", "loan_amount",
					"repayment_method", "monthly_repayment_amount",
					"repayment_periods", "rate_of_interest"
				]

				// assign the common values from the application to the loan
				$.each(field_list, function(idx, field) {
					frm.set_value(field, loan_application[field])
				})
			}
		})
	},
	repayment_method: function(frm) {
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method == "Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method == "Repay Over Number of Periods")
		frm.trigger("fix_table_header")
	},
	add_buttons: function(frm) {
		// validate that the document is submitted
		if (frm.doc.docstatus == 1) {
			if (frm.doc.status == "Sanctioned" || frm.doc.status == "Partially Disbursed") {
				frm.add_custom_button(__('Make Disbursement Entry'), function() {
					frm.trigger("make_jv")
				})
			} else if (frm.doc.status == "Fully Disbursed") {
				frm.add_custom_button(__('Payment Entry'), function() {
					frm.trigger("make_payment_entry")
				})

				frm.add_custom_button(__('Disbursement Entry'), function() {
					frappe.db.get_value("Journal Entry", { "loan": frm.docname, "docstatus": ["!=", 2] }, "name", function(data) {
						frappe.set_route("Form", "Journal Entry", data.name)
					})
				}, "Ver")

				frm.add_custom_button(__('Payment Entry'), function() {
					frappe.set_route("List", "Payment Entry", { "loan": frm.docname })
				}, "Ver")
			}
		}
	},
	set_queries: function(frm) {
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

		frm.set_query("loan_application", function() {
			return {
				"filters": {
					"docstatus": 1,
					"status": "Approved",
					"status": ["!=","Linked"]
				}
			}
		})
	},
	fix_table_header: function(frm) {
		setTimeout(function() {
			$("[data-fieldname=repayment_schedule] [data-fieldname=fecha]").css("width", "12%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=cuota]").css("width", "10%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=balance_capital]").css("width", "10%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=balance_interes]").css("width", "10%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=capital_acumulado]").css("width", "10%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=interes_acumulado]").css("width", "10%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=pagos_acumulados]").css("width", "10%")
			$("[data-fieldname=repayment_schedule] [data-fieldname=estado]").css("width", "14%")
			$("[data-fieldname=repayment_schedule] .close.btn-open-row").parent().css("width", "5%")
			$("[data-fieldname=repayment_schedule] .grid-heading-row .col.col-xs-1").css("height", 60)
			$("[data-fieldname=repayment_schedule] .grid-heading-row .col.col-xs-2").css("height", 60)

			fecha = $("[data-fieldname=repayment_schedule] [data-fieldname=fecha] .static-area.ellipsis:first")
			fecha.html("<br>Fecha")

			cuota = $("[data-fieldname=repayment_schedule] [data-fieldname=cuota] .static-area.ellipsis:first")
			cuota.html("<br>Cuota")

			balance_capital = $("[data-fieldname=repayment_schedule] [data-fieldname=balance_capital] .static-area.ellipsis:first")
			balance_capital.html("Bal.<br>Capital")

			balance_interes = $("[data-fieldname=repayment_schedule] [data-fieldname=balance_interes] .static-area.ellipsis:first")
			balance_interes.html("Bal.<br>Interes")

			capital_acumulado = $("[data-fieldname=repayment_schedule] [data-fieldname=capital_acumulado] .static-area.ellipsis:first")
			capital_acumulado.html("Capital<br>Acum.")

			interes_acumulado = $("[data-fieldname=repayment_schedule] [data-fieldname=interes_acumulado] .static-area.ellipsis:first")
			interes_acumulado.html("Interes<br>Acum.")

			pagos_acumulados = $("[data-fieldname=repayment_schedule] [data-fieldname=pagos_acumulados] .static-area.ellipsis:first")
			pagos_acumulados.html("Pagos<br>Acum.")

			estado = $("[data-fieldname=repayment_schedule] [data-fieldname=estado] .static-area.ellipsis:first")
			estado.html("<br>Estado")
		}, 500)
	},
	beautify_repayment_table: function(frm) {
		setTimeout(function() {

			// let's prepare the repayment table's apereance for the customer
			fields = $("[data-fieldname=repayment_schedule] [data-fieldname=estado]")

			// ok, now let's iterate over each row
			$.each(fields, function(idx, value){
				var field = $(value)
				var text = field.text()

				if(text == "SALDADA"){
					field.addClass("indicator green")
					field.text("PAID")
				} else if(text == "ABONO"){
					field.addClass("indicator blue")
					field.text("PENDING")
				} else if(text == "PENDIENTE"){
					field.addClass("indicator orange")
					field.text("UNPAID")
				} else {
					// nothing to do
				}
			})
		}, 500)
	},
	make_payment_entry: function(frm) {

		var next_cuota = undefined
		var next_pagare = undefined
		
		if ( frm.doc._asset ){
			var found = false
			var asset = frm.doc._asset

			asset.cuotas.forEach(function(value){

				// if there's no one found yet
				if ( !found && value.status == "PENDING" ){
					// means that this is the first one PENDING

					found = true // set the flag to true
					next_cuota = value // and set the value
				}
			})
		}

		// set the insurance rate if there is one
		var cuota_amount = !next_cuota || !next_cuota.amount ? 0 : next_cuota.amount

		var found = false
		var schedule = frm.doc.repayment_schedule

		schedule.forEach(function(value){

			// if there's no one found yet
			if ( !found && value.estado == "PENDIENTE" ){
				// means that this is the first one PENDING

				found = true // set the flag to true
				next_pagare = value // and set the value
			}
		})

		// set the fine amount if there is one
		var fine_amount = !next_pagare.fine ? 0 : next_pagare.fine

		// add all the posible values that applies to the amount that has to be paid
		var paid_amount = flt(frm.doc.monthly_repayment_amount) + flt(cuota_amount) + flt(fine_amount)

		var read_only_discount = frappe.user.has_role("Gerente de Operaciones") ? 0 : 1 


		// these are the fields to be shown
		fields = [
			{ 
				"fieldname": "paid_amount", "fieldtype": "Float", "label": __("Paid Amount"), "reqd": 1, "default": paid_amount
			},
			{ 
				"fieldtype": "Section Break", "fieldname": "fine_section"
			},
			{ 
				"fieldname": "fine", "fieldtype": "Float", "label": __("Fine"), "read_only": 1, "default": fine_amount
			},
			{ 
				"fieldname": "discount_column", "fieldtype": "Column Break"
			},
			{   
				"fieldname": "fine_discount", "fieldtype": "Float", "label": __("Fine Discount"), "default": "0.0", "precision": 2, "read_only": read_only_discount
			},
			{ 
				"fieldtype": "Section Break", "fieldname": "insurance_section"
			},
			{ 
				"fieldname": "insurance", "fieldtype": "Float", "label": __("Insurance Amount"), "read_only": 1, "default": cuota_amount
			}
		]

		// the callback to execute when user
		// finishes introducing the values
		var onsubmit = function(data){

			// message to be shown
			var msg = __("Are you sure you want to submit this new Payment Entry")

			// code to execute when user says yes
			var ifyes = function(){
				var method = "fm.accounts.make_payment_entry"
				var args = {
					"doctype": frm.doctype,
					"docname": frm.docname,
					"paid_amount": data.paid_amount,
					"fine": data.fine,
					"fine_discount": data.fine_discount,
					"insurance": data.insurance,
					"interest_amount": next_pagare.interes,
					"capital_amount": next_pagare.capital
				}

				var _callback = function(response){
					var name = response.message

					// let the user know that it was succesfully created
					frappe.show_alert(__("Payment Entry created!"), 9)

					// let's play a sound for the user
					frappe.utils.play_sound("submit")

					// clear the prompt
					frm.prompt = undefined

					// let's show the user the new payment entry
					setTimeout(function() { frappe.set_route(["Form", "Journal Entry", name]) }, 1500)
				}

				frappe.call({ "method": method, "args": args, "callback": _callback })
		    }

			// code to execute when user says no
			var ifno = function(){
				frm.prompt.show()
		    }

		    // ok, now we're ready to ask the user
			frappe.confirm( msg, ifyes, ifno )
		}

		// let's check if object is already set
		if ( frm.prompt ){

			// it is set at this point
			// let's just make it visible
			frm.prompt.show()
		} else {
			fields[0].default = 
			// there was not object, so we need to create it
			frm.prompt = frappe.prompt( fields, onsubmit, "Payment Entry", "Submit" )
		}
	}
})
