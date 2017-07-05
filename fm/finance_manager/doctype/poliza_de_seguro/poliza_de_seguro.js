// Copyright (c) 2016, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Poliza de Seguro', {
	onload: function(frm) {
		frm.trigger("set_queries")

		if ( !frm.doc.__islocal ){
			return 0 // exit code is zero
		}

		var today = frappe.datetime.get_today()
		frm.set_value("start_date", today)

		var doctype = docname = "FM Configuration"
		var callback = function(data) {
			if (data){
				frm.set_value("insurance_company", data.default_insurance_supplier)
			}
		}

		frappe.model.get_value(doctype, docname, "default_insurance_supplier", callback)	

	},
	refresh: function(frm) {
		if ( !frm.doc.docstatus == 0.00 ){

			var callback = function(data){
				if ( !data ){
					return 1 // exit code is one
				}	

				frm.doc.currency = data.customer_currency
				frm.set_df_property("amount", "label", __("Importe ({0})", [frm.doc.currency]))
			}

			frappe.model.get_value("Loan", frm.doc.loan, "customer_currency", callback)
		}

		frm.trigger("beautify_table")
	},
	on_submit: function(frm){
        // create a new Array from the history
        var new_history = Array.from(frappe.route_history)

        // then reversed the new history array
        var reversed_history = new_history.reverse()

        // not found flag to stop the bucle
        var not_found = true

        // iterate the array to find the last Loan visited
        $.each(reversed_history, function(idx, value) {

            // see if there is a Loan that was visited in this
            // section. if found it then redirect the browser to
            // asumming that the user came from that Loan
            if (not_found && "Form" == value[0] && "Loan" == value[1]) {

                // give a timeout before switching the location
                setTimeout(function() {
                    // set the route to the latest opened Loan
                    frappe.set_route(value)
                })

                // set the flag to false to finish
                not_found = false
            }
        })
	},
	start_date: function(frm) {
		var next_year = frappe.datetime.add_months(frm.doc.start_date, 12)
		frm.set_value("end_date", next_year)

		// to sync the table
		frm.trigger("amount")
	},
	financiamiento: function(frm) {
		if (!frm.doc.financiamiento){
			frm.set_value("amount", 0.000)
		} else {
			frm.trigger("amount")
		}
	},
	amount: function(frm) {

		if (frm.doc.amount <= 0.000 || !frm.doc.financiamiento) {
			frm.set_value("cuotas", [
				// empty array
			])

			return 0 // exit code is one
		} 

		if (frm.doc.amount) {
			var amount = Math.ceil(frm.doc.amount / 3.000)
			var date = frm.doc.start_date

			frm.clear_table("cuotas")

			for (index = 0; index < 3; index ++) {
				frm.add_child("cuotas", { 
					"date": date, 
					"amount": amount, 
					"status": index == 0? "SALDADO": "PENDIENTE" 
				})

				date = frappe.datetime.add_months(date, 1.000)
			}

			// to make it match with real amount being charged to the customer
			frm.doc.amount = flt(amount * 3)

			// refresh all fields
			frm.refresh_fields()
		}
	},
	validate: function(frm) {
		if (frm.doc.financiamiento && frm.doc.amount <= 0.000){
			frappe.msgprint("Ingrese un monto valido para el seguro!")
			validated = false
		}
	},
	set_queries: function(frm) {
		frm.set_query("insurance_company", function(){
			return {
				"filters": {
					"supplier_type": "Insurance Provider"
				}
			}
		})
	},
	beautify_table: function(frm) {
		setTimeout(function() {

			// let's prepare the repayment table's apereance for the customer
			var fields = $("[data-fieldname=cuotas] \
				[data-fieldname=status] > .static-area.ellipsis")

			// ok, now let's iterate over each row
			$.each(fields, function(idx, value) {

				// set the jQuery object to a local variable
				// to make it more readable
				var field = $(value)

				// let's remove the previous css class
				clear_class(field)

				if ("SALDADO" == field.text()) {

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
	}
})
