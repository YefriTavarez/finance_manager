// Copyright (c) 2016, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cashier Closing', {
	refresh: function(frm) {
		frm.page.show_menu()
		frm.trigger("refresh_btn")

	},
	close: function(frm) {
		frm.trigger("load_prompt")
	},
	open: function(frm) {
		frm.trigger("load_prompt")
	},
	refresh_btn: function(frm) {

		if (frm.doc.entries && !! frm.doc.entries.length && frm.doc.entries[0].type == "CLOSE") {
			frm.set_df_property("close", "hidden", true)
			frm.set_df_property("open", "hidden", false)
		} else if (frm.doc.entries && !! frm.doc.entries.length && frm.doc.entries[0].type =="OPEN") {
			frm.set_df_property("close", "hidden", false)
			frm.set_df_property("open", "hidden", true)
		} else  {
			frm.set_df_property("close", "hidden", true)
			frm.set_df_property("open", "hidden", false)
		}
	},
	load_prompt: function(frm) {

		last_entry ="CLOSE"
		
		if(frm.doc.entries && frm.doc.entries.length > 1)
			last_entry = frm.doc.entries[0].type 
		
		action = last_entry == "CLOSE"	? "OPEN" : "CLOSE" 

		var fields = [{
			"label": "DOP",
			"fieldtype": "Heading",
			"fieldname": "heading_dop"
		},
		{
			"label":__("Cashier (DOP)"),
			"fieldtype": "Currency",
			"fieldname": "amount_dop"
		},
		{
			"fieldtype": "Column Break",
			"fieldname": "colunm_break"
		},
		{
			"label": "USD",
			"fieldtype": "Heading",
			"fieldname": "heading_usd"
		},
		{
			"label":__("Cashier (USD)"),
			"fieldtype": "Currency",
			"fieldname": "amount_usd"
		},
		{
			"fieldtype": "Section Break",
			"fieldname": "section_break"
		},
		{
			"label":__("Action"),
			"fieldtype": "Data",
			"fieldname": "type",
			"read_only": 1,
			"default": action
		},
		{
			"label": "Company",
			"fieldtype": "Data",
			"fieldname": "company",
			"hidden": 1,
			"default": frm.doc.company
		}]

		// the callback to execute when user
		// finishes introducing the values
		var onsubmit = function(data) {

			// message to be shown
			var msg = __("Are you sure you want to {0} Cashier?", [data.type])

			// code to execute when user says yes
			var ifyes = function() {

				// method to be executed in the server
				var _method = "fm.accounts.cashier_control"
				// arguments passed to the method
				var _args = {
					"frm": frm.doc,
					"data": data
				}


				// callback to be executed after the server responds
				var _callback = function(response) {
					var doc = frappe.model.sync(response.message)[0]

					frappe.utils.play_sound("submit")

					frm.reload_doc()
					frm.prompt = undefined
				}

				frappe.call({ "method": _method, "args": _args, "callback": _callback })
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
			frm.prompt = frappe.prompt(fields, onsubmit, __("Cashier Closing"), "Submit")
		}

	}

});
