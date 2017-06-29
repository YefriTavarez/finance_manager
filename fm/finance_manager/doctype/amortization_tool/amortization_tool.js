// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Amortization Tool', {
	setup: function(frm) {
		// field list for global purposes
		frm._field_list = [
			"interest_type",
			"gross_loan_amount",
			"repayment_method",
			"repayment_periods",
			"rate_of_interest",
			"legal_expenses_rate",
			"loan_amount",
			"monthly_repayment_amount",
			"total_payment",
			"total_interest_payable",
			"repayment_schedule"
		]
	},
	refresh: function(frm) {
		frm.add_custom_button(__("Clear"), function(event) {
			frm.trigger("clear_and_set_defautls")
		})
		frm.add_custom_button(__("Calculate"), function(event) {
			frm.trigger("calculate_everything")
		})

		// to toggle the fields from at load time
		frm.trigger("toggle_fields")

		// load defaults from the server
		frm.trigger("clear_and_set_defautls")

		// user should not be able to save this form
		frm.disable_save()
	},
	repayment_method: function(frm) {
		frm.trigger("toggle_fields")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("monthly_repayment_amount", frm.doc.repayment_method == "Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method == "Repay Over Number of Periods")
		frm.trigger("fix_table_header")
	},
	gross_loan_amount: function(frm) {
		var expense_rate_dec = frm.doc.legal_expenses_rate / 100
		var loan_amount = frm.doc.gross_loan_amount * (expense_rate_dec + 1)
		frm.set_value("loan_amount", loan_amount)
	},
	validate_mandatory: function(frm) {
		var mandatory_fields = [
			"gross_loan_amount",
			"rate_of_interest",
			"legal_expenses_rate",
			"loan_amount",
			"repayment_periods"
		]

		var del_underscores = function(fieldname) {
			var without_scores = fieldname.replace(/_/g, " ")

			var label = without_scores.replace(/(\b\w)/gi, 
				function(first_letter){
					return first_letter.toUpperCase()
				}
			)

			return label
		}

		$.each(mandatory_fields, function(idx, field) {
			if ( !frm.doc[field] ) {
				frappe.throw(
					__("Missing {0}", 
						[ __(frm.fields_dict[field]._label) ]
					)
				)
				// frappe.throw(__("Missing {0}", [del_underscores(field)]))
			}
		})
	},
	clear_and_set_defautls: function(frm){
		// method to run in the server in order
		// to fetch the FM Configuration document
		var method = "frappe.client.get"

		// arguments passed to the method
		var args = {
			"doctype": "FM Configuration",
			"name": "FM Configuration"
		}

		// method to run after the server finishes
		var callback = function(response){

			// grab the whole document in a local variable
			var conf = response.message

			// to map the current requeriments
			conf.rate_of_interest = conf.simple_rate_of_interest

			// map defaults
			conf.interest_type = "Simple"
			conf.repayment_periods = 24
			conf.repayment_method = "Repay Over Number of Periods"

			// iterate over the field list
			$.each(frm._field_list, function(idx, field){
				// set the default value from the FM Configuration
				// and if the value is not in there then set it to undefined
				frm.set_value(field, conf[field])
			})
		}

		frappe.call({ method: method, args: args, callback: callback })
	},
	calculate_everything: function(frm) {
		
		// check if all the fields we need are set
		frm.trigger("validate_mandatory")

		// freeze the screen and don't let the user to send 
		// actions while the request is being processed
		frappe.dom.freeze("Espere...")

		// empty the table to reduce page load
		frm.doc.repayment_schedule = []

		// update the table so the user can see it is empty
		frm.refresh_field("repayment_schedule")

		// this is the success callback func
		var callback = function(response) {
			var field_dict = response.message

			// let's see if the server sent something back
			if ( !field_dict ) {
				return 1 // exit code 1
			}

			// for each field that we got in the response
			// let us set it to this form so the user
			// can see the results
			$.each(frm._field_list, function(key, field) {
				frm.set_value(field, field_dict[field])
			})

			// update the form
			frm.refresh_fields()
			frm.trigger("fix_table_header")
			
			frappe.dom.unfreeze()
		}

		// unfreeze it after 5 secs, just in case!
		setTimeout(function() { frappe.dom.unfreeze() }, 5000)

		// ok, we're ready now to send the request to the server
		$c('runserverobj', { "docs": frm.doc, "method": "calculate_everything" }, callback)
	},
	fix_table_header: function(frm) { setTimeout(
		function() {
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
	}
})