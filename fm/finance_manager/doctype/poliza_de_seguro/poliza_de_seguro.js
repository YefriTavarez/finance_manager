// Copyright (c) 2016, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Poliza de Seguro', {
	onload: function(frm) {
		if (frm.doc.__islocal){

			var today = frappe.datetime.get_today()
			frm.set_value("start_date", today)

			// var next_year = frappe.datetime.add_months(today, 12)
			// frm.set_value("end_date", next_year)
		}

		frm.trigger("set_queries")
	},
	on_submit: function(frm){
		// function after the server responds 
		callback =  function(response) {
			var doc = response.message

			console.log(doc)
			
			if ( !doc || !doc.name ){
				return 1 // exit code is one
			} 

			setTimeout(function() { 
				frappe.set_route(["Form", "Purchase Invoice", doc.name])
			}, 1500)	
		}

		frm.call("make_purchase_invoice", "args", callback)
	},
	start_date: function(frm) {
		var next_year = frappe.datetime.add_months(frm.doc.start_date, 12)
		frm.set_value("end_date", next_year)
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
			amount = Math.ceil(frm.doc.amount / 3)
			var date = frappe.datetime.get_today()
			// date = frappe.datetime.add_months(today, 1)

			frm.clear_table("cuotas")

			for (i = 0; i < 3; i++) {
				frm.add_child("cuotas", { "date": date, "amount": amount, "status": "PENDIENTE" })

				date = frappe.datetime.add_months(date, 1)
			}

			refresh_field("cuotas")
		}
	},
	validate: function(frm) {
		if (frm.doc.financiamiento && frm.doc.amount <= 0){
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
	}
})
