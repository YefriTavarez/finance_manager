// Copyright (c) 2016, Soldeva, SRL and contributors
// For license information, please see license.txt
frappe.ui.form.on('Amortization Tool', {
	onload: function(frm) {
		{
			frm.trigger("toggle_fields")
			frm.trigger("set_defaults")
		}

	},
	refresh: function(frm) {
		frm.add_custom_button("Limpiar", function(event) {
			frm.reload_doc()
		})

		frm.add_custom_button("Calcular", function(event) {
			frm.trigger("calculate_everything")
		})
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
	fix_table_header: function(frm) {
		setTimeout(function() {
			$("[data-fieldname=repayment_schedule] .grid-heading-row .col.col-xs-1").css("height", 50)
			$("[data-fieldname=repayment_schedule] .grid-heading-row .col.col-xs-2").css("height", 50)
		}, 500)
	},
	set_defaults: function(frm) {
		frappe.db.get_value("FM Configuration", "", "simple_rate_of_interest", function(data) {
			cur_frm.set_value("rate_of_interest", data.simple_rate_of_interest)
		})
		frappe.db.get_value("FM Configuration", "", "legal_expenses_rate", function(data) {
			cur_frm.set_value("legal_expenses_rate", data.legal_expenses_rate)
		})
	},
	gross_loan_amount: function(frm) {
		var expense_rate_dec = frm.doc.legal_expenses_rate / 100
		var loan_amount = frm.doc.gross_loan_amount * (expense_rate_dec + 1)
		frm.set_value("loan_amount", loan_amount)
	},
	calculate_everything: function(frm) {
		frappe.dom.freeze("Espere...")
		frm.doc.repayment_schedule = []
		frm.refresh_field("repayment_schedule")

		$c('runserverobj', { "docs": frm.doc, "method": "calculate_everything" }, function(response) {
			if (response.message) {
				var field_dict = response.message

				$.each(field_dict, function(key, value) {
					frm.doc[key] = value
				})

				frm.refresh_fields()
			} 

			frappe.dom.unfreeze()
		})
	}
})