// Copyright (c) 2016, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Poliza de Seguro', {
	onload: function(frm) {
		if (frm.doc.__islocal){
			var today = frappe.datetime.get_today()
			var next_year = frappe.datetime.add_months(today, 12)

			frm.set_value("start_date", today)
			frm.set_value("end_date", next_year)
		}

        frm.trigger("set_queries")
	},
    on_submit: function(frm){
       // method to be called 
        method = "make_purchase_invoice"
        
        // function after the server responds 
        callback =  function(response) {
            
            if ( !response.message )
                return 1 

            var doc = frappe.model.sync(response.message)[0]
            frappe.set_route("Form", doc.doctype, doc.name)
        }

        $c('runserverobj', { "docs": frm.doc, "method": method }, callback)
    },
	renew: function(frm) {
		if ( !frm.doc.insurance_company )
            frappe.throw("Debe ingresar el nombre de la aseguradora")

        if ( !frm.doc.policy_no )
            frappe.throw("Debe ingresar el numero de poliza del cliente")

        if (frm.doc.financiamiento) {
            if (frm.doc.amount > 0) {
                amount = Math.ceil(frm.doc.amount / 3)
                var today = frappe.datetime.get_today()
                date = frappe.datetime.add_months(today, 1)

                frm.clear_table("cuotas")

                for (i = 0; i < 3; i++) {
                    frm.add_child("cuotas", { "date": date, "amount": amount, "status": "PENDING" })

                    date = frappe.datetime.add_months(date, 1)
                }

                refresh_field("cuotas")
                frm.save()
            } else {
                frappe.msgprint("Si opta por el financiamiento el monto de la poliza debe ser mayor que cero")
            }
        } else {
            frm.set_value("amount", 0)
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
