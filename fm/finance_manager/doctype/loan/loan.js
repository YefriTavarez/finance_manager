// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan', {
	setup: function(frm) {
		frm.add_fetch("customer", "default_currency", "customer_currency")
	},
	onload: function(frm) {
		// to filter some link fields
		frm.trigger("set_queries")

		var _status = frm.doc.status

		if (_status == "Approved" || _status == "Linked") {
			frm.set_value("status", "Sanctioned")
		}

		// let's clear the prompt
		frm.prompt = undefined
	},
	onload_post_render: function(frm) {
		var doctype = "Currency Exchange"
		var fieldname = "exchange_rate"
		var filters = {
			"from_currency": "USD",
			"to_currency": "DOP"
		}

		var callback = function(data) {
			if (data) {
				frm.doc.exchange_rate = data.exchange_rate
			} else {
				frappe.msgprint("Hubo un problema mientras se cargaba la tasa de conversion de\
					Dolar a Peso.<br>Favor de contactar su administrador de sistema!")
			}
		}

		frappe.db.get_value(doctype, filters, fieldname, callback)
	},
	refresh: function(frm) {
		frm.trigger("needs_to_refresh")
		frm.trigger("toggle_fields")
		frm.trigger("add_buttons")
		frm.trigger("beautify_repayment_table")

		setTimeout(function() {

			// let's hide this field
			frm.set_df_property("repayment_periods", "read_only", true)
		})
	},
	validate: function(frm) {
		frm.trigger("setup")
	},
	needs_to_refresh: function(frm) {
		// check if it's a new doc
		if (frm.doc.__islocal)
			return 0 // let's just ignore it

		var field_list = [
			"modified",
			"paid_by_now"
		]

		var callback = function(data) {
			if (frm.doc.modified != data.modified || frm.doc.paid_by_now != data.paid_by_now) {
				// reload the doc because it's out of date
				frm.reload_doc()
			}
		}

		// check the last time it was modified in the DB
		frappe.db.get_value(frm.doctype, frm.docname, field_list, callback)
	},
	gross_loan_amount: function(frm) {
		var expense_rate_dec = flt(frm.doc.legal_expense_rate / 100.000)
		var loan_amount = frm.doc.gross_loan_amount * (expense_rate_dec +1.000)

		frm.set_value("loan_amount", loan_amount)
	},
	make_jv: function(frm) {
		frm.call("make_jv_entry", "args", function(response) {
			var doc = response.message

			// let's see if everything was ok
			if (!doc) {
				frappe.msgprint("Uups... algo salió mal!")
				return 1 // exit code is 1
			}

			frappe.model.sync(doc)

			frappe.set_route("Form", doc.doctype, doc.name)
		})
	},
	mode_of_payment: function(frm) {

		// check to see if the mode of payment is set
		if (!frm.doc.mode_of_payment)
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
			if (!data)
				return 0 // let's just ignore it

			// let's set the value
			frm.set_value("payment_account", frm.doc.customer_currency == "DOP" ?
				data.account : data.account.replace("DOP", "USD"))
		}

		// ok, now we're ready to send the request
		frappe.call({
			method: method,
			args: args,
			callback: callback
		})
	},
	set_account_defaults: function(frm) {
		// this method fetch the default accounts from
		// the FM Configuration panel if it exists


		// the method that we're going to execute in the server
		var method = "frappe.client.get"

		// and the arguments that it requires
		var args = {
			"doctype": "FM Configuration",
			"name": "FM Configuration"
		}

		// finally this is the callback to execute when the server finishes
		var callback = function(response) {

			// in case something is wrong with the request
			if (response.exec) {
				frappe.throw(__("There was an error while loading the default accounts!"))
			}

			// set the response body to a local variable
			var conf = response.message

			// set the response doc object to a local variable
			var doc = frm.doc

			var fields = [
				"mode_of_payment",
				"payment_account",
				"expenses_account",
				"customer_loan_account",
				"interest_income_account",
				"disbursement_account"
			]

			// set the values
			$.each(fields, function(idx, field) {
				// check to see if the field has value

				var account = frm.doc.customer_currency != "DOP" ?
					conf[field].replace("DOP", "USD") : conf[field]

				// it has no value, then set it
				frm.set_value(field, account)
			})
		}

		// ok, now we're ready to send the request
		frappe.call({
			"method": method,
			"args": args,
			"callback": callback
		})
	},
	loan_application: function(frm) {
		// exit the function and do nothing
		// if loan application is triggered but has not data
		if (!frm.doc.loan_application)
			return 0 // let's just ignore it

		frm.call({
			"method": "fm.finance_manager.doctype.loan.loan.get_loan_application",
			"args": {
				"loan_application": frm.doc.loan_application
			},
			"callback": function(response) {
				var loan_application = response.message

				// exit the callback if no data came from the SV
				if (!loan_application)
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
	customer: function(frm) {

		// let's set the default account from the FM Configuration
		frm.trigger("set_account_defaults")
	},
	repayment_method: function(frm) {
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("monthly_repayment_amount", 
			frm.doc.repayment_method == "Repay Fixed Amount per Period")

		frm.toggle_enable("repayment_periods", 
			frm.doc.repayment_method == "Repay Over Number of Periods")
		frm.trigger("fix_table_header")
	},
	add_buttons: function(frm) {
		if ( !frm.doc.__islocal) {
			frm.add_custom_button("Refrescar", function() {
				frm.reload_doc()
			})
		}

		// validate that the document is submitted
		if (!frm.doc.docstatus == 1) {
			return 0 // exit code is zero
		}

		if (frm.doc.status == "Sanctioned" || frm.doc.status == "Partially Disbursed") {
			frm.add_custom_button(__('Disbursement Entry'), function() {
				frm.trigger("make_jv")
			}, "Make")
		}

		if (frm.doc.status == "Fully Disbursed" || frm.doc.status == "Partially Disbursed") {

			if (frm.doc.status == "Fully Disbursed") {
				frm.add_custom_button(__('Payment Entry'), function() {
					frm.trigger("make_payment_entry")
				}, frappe.user.has_role("Cajera") ? "" : "Make")
			}

		}
		
		frm.add_custom_button(__('Insurance'), function() {
			frm.trigger("insurance")
		}, "Make")

		frm.add_custom_button(__('Disbursement Entry'), function() {
			var _filters = {
				"loan": frm.docname,
				"docstatus": ["!=", 2]
			}
			var _callback = function(data) {
				if (!data) {
					frappe.throw("No se encontro ningun desembolso para este prestamo!")
				}

				frappe.set_route("List", "Journal Entry", {
					"loan": frm.docname,
					"es_un_pagare": "0"
				})
			}

			frappe.db.get_value("Journal Entry", _filters, "name", _callback)
		}, "Ver")

		frm.add_custom_button(__('Payment Entry'), function() {
			frappe.set_route("List", "Journal Entry", {
				"loan": frm.docname,
				"es_un_pagare": "1"
			})
		}, "Ver")
	},
	set_queries: function(frm) {
		root_types = {
			"interest_income_account": "Income",
			"expenses_account": "Income",
			"payment_account": "Asset",
			"customer_loan_account": "Asset"
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
					"status": ["!=", "Linked"]
				}
			}
		})
	},
	fix_table_header: function(frm) {
		setTimeout(function() {
			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=fecha]")
			.css("width", "14%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=cuota]")
			.css("width", "9%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=balance_capital]")
			.css("width", "9%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=balance_interes]")
			.css("width", "9%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=capital_acumulado]")
			.css("width", "9%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=interes_acumulado]")
			.css("width", "9%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=pagos_acumulados]")
			.css("width", "9%")

			$("[data-fieldname=repayment_schedule] \
				[data-fieldname=estado]")
			.css("width", "14%")

			$("[data-fieldname=repayment_schedule] \
				.close.btn-open-row").parent()
			.css("width", "5%")

			$("[data-fieldname=repayment_schedule] \
				.grid-heading-row .col.col-xs-1")
			.css("height", 60)

			$("[data-fieldname=repayment_schedule] \
				.grid-heading-row .col.col-xs-2")
			.css("height", 60)


			$("[data-fieldname=repayment_schedule] [data-fieldname=fecha] \
				.static-area.ellipsis:first")
			.html("<br>Fecha")

			$("[data-fieldname=repayment_schedule] [data-fieldname=cuota] \
				.static-area.ellipsis:first")
			.html("<br>Cuota")

			$("[data-fieldname=repayment_schedule] [data-fieldname=balance_capital] \
				.static-area.ellipsis:first")
			.html("Bal.<br>Capital")

			$("[data-fieldname=repayment_schedule] [data-fieldname=balance_interes] \
				.static-area.ellipsis:first")
			.html("Bal.<br>Interes")

			$("[data-fieldname=repayment_schedule] [data-fieldname=capital_acumulado] \
				.static-area.ellipsis:first")
			.html("Capital<br>Acum.")

			$("[data-fieldname=repayment_schedule] [data-fieldname=interes_acumulado] \
				.static-area.ellipsis:first")
			.html("Interes<br>Acum.")

			$("[data-fieldname=repayment_schedule] [data-fieldname=pagos_acumulados] \
				.static-area.ellipsis:first")
			.html("Pagos<br>Acum.")

			$("[data-fieldname=repayment_schedule] [data-fieldname=estado] \
				.static-area.ellipsis:first")
			.html("<br>Estado")
		})
	},
	beautify_repayment_table: function(frm) {
		setTimeout(function() {

			// let's prepare the repayment table's apereance for the customer
			var fields = $("[data-fieldname=repayment_schedule] \
				[data-fieldname=estado] > .static-area.ellipsis")

			// ok, now let's iterate over each row
			$.each(fields, function(idx, value) {

				// set the jQuery object to a local variable
				// to make it more readable
				var field = $(value)

				// let's remove the previous css class
				clear_class(field)

				if ("SALDADA" == field.text()) {

					field.addClass("indicator green")
				} else if ("ABONO" == field.text()) {

					field.addClass("indicator blue")
				} else if ("PENDIENTE" == field.text()) {

					field.addClass("indicator orange")
				} else if ("VENCIDA" == field.text()) {

					field.addClass("indicator red")
				}
			})
		})

		var clear_class = function(field) {
			field.removeClass("indicator green")
			field.removeClass("indicator blue")
			field.removeClass("indicator orange")
			field.removeClass("indicator red")
		}
	},
	insurance: function(frm) {
		var today = frappe.datetime.get_today()

		var filters = {
			"loan": frm.doc.name,
			"docstatus": ["!=", "2"],
			"start_date": ["<=", today],
			"end_date": [">=", today]
		}

		var callback = function(data) {
			if (data) {
				frappe.set_route(["Form", "Poliza de Seguro", data.name])
			} else {
				frappe.route_options = {
					"vehicle": frm.doc.asset,
					"loan": frm.docname
				}

				frappe.new_doc("Poliza de Seguro")
			}
		}

		frappe.model.get_value("Poliza de Seguro", filters, "name", callback)
	},
	make_payment_entry: function(frm) {
		var read_only_discount = !!!frappe.user.has_role("Gerente de Operaciones")

		// var next_cuota = undefined
		var next_pagare = undefined

		var found = false
		var schedule = frm.doc.repayment_schedule
		var currency = frm.doc.customer_currency

		schedule.forEach(function(value) {

			// if there's no one found yet
			if (!found && value.estado != "SALDADA") {
				// means that this is the first one PENDING

				found = true // set the flag to true
				next_pagare = value // and set the value
			}
		})

		// set the fine amount if there is one
		var fine_amount = !next_pagare.fine ? 0 : next_pagare.fine
		var repayment_amount = !next_pagare.cuota ? frm.doc.monthly_repayment_amount : next_pagare.cuota

		// these are the fields to be shown
		fields = [{
			"fieldname": "paid_amount",
			"fieldtype": "Float",
			"label": __("Monto Recibido ({0})", [currency]),
			"reqd": 1,
			"default": next_pagare.monto_pendiente
		}, {
			"fieldname": "payment_section",
			"fieldtype": "Column Break"
		}, {
			"fieldname": "repayment_idx",
			"fieldtype": "Int",
			"label": __("Pagare No."),
			"read_only": 1,
			"default": next_pagare.idx
		}, {
			"fieldname": "fine_section",
			"fieldtype": "Section Break"
		}, {
			"fieldname": "fine",
			"fieldtype": "Float",
			"label": __("Mora ({0})", [currency]),
			"read_only": 1,
			"default": fine_amount? fine_amount: "0.00"
		}, {
			"fieldname": "discount_column",
			"fieldtype": "Column Break"
		}, {
			"fieldname": "fine_discount",
			"fieldtype": "Float",
			"label": __("Descuento a Mora ({0})", [currency]),
			"default": "0.0",
			"precision": 2,
			"read_only": read_only_discount
		}, {
			"fieldname": "insurance_section",
			"fieldtype": "Section Break"
		}, {
			"fieldname": "insurance",
			"fieldtype": "Float",
			"label": __("Seguro (DOP)"),
			"read_only": 1,
			"default": next_pagare.insurance
		}, {
			"fieldname": "repayment_section",
			"fieldtype": "Column Break"
		}, {
			"fieldname": "pending_amount",
			"fieldtype": "Float",
			"label": __("Monto del Pendiente ({0})", [currency]),
			"read_only": 1,
			"default": next_pagare.monto_pendiente
		}, {
			"fieldname": "repayment_amount",
			"fieldtype": "Float",
			"label": __("Monto del Pagare ({0})", [currency]),
			"read_only": 1,
			"default": repayment_amount
		}]

		// the callback to execute when user
		// finishes introducing the values
		var onsubmit = function(data) {

			// message to be shown
			var msg = __("Are you sure you want to submit this new Payment Entry")

			// code to execute when user says yes
			var ifyes = function() {

				// method to be executed in the server
				var method = "fm.accounts.make_payment_entry"

				// arguments passed to the method
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

				// callback to be executed after the server responds
				var _callback = function(response) {
					var name = response.message

					// let the user know that it was succesfully created
					frappe.show_alert(__("Payment Entry created!"), 9)

					// let's play a sound for the user
					frappe.utils.play_sound("submit")

					// clear the prompt
					frm.reload_doc()

					var filters = {
						"loan": frm.docname,
						"es_un_pagare": "1"
					}

					setTimeout(function() {
						frappe.hide_msgprint(instant=true)
					})
					
					// let's show the user the new payment entry
					frappe.set_route("List", "Journal Entry", filters)
				}

				frappe.call({
					"method": method,
					"args": args,
					"callback": _callback
				})
			}

			// code to execute when user says no
			var ifno = function() {
				frm.prompt.show()
			}

			// ok, now we're ready to ask the user
			frappe.confirm(msg, ifyes, ifno)
		}

		// let's check if object is already set
		if (frm.prompt) {

			// it is set at this point
			// let's just make it visible
			frm.prompt.show()
		} else {

			// there was not object, so we need to create it
			frm.prompt = frappe.prompt(fields, onsubmit, "Payment Entry", "Submit")
		}
	}
})

frappe.ui.form.on('Tabla Amortizacion', {
	voucher: function(frm, cdt, cdn) {
		frappe.route_options = {
			"pagare": cdn
		}

		frappe.set_route(["List", "Journal Entry"])
	}
})