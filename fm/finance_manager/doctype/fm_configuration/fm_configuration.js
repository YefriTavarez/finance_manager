// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('FM Configuration', {
	validate: function(frm) {
		// ok, now let's request the email entered to see if it exists in the system
		frappe.model.get_value('User', { 'email': frm.doc.allocated_to_email }, 'email', function(data) {
			// if by any chance this brings no data, that means the user entered
			// does not exist in the system
			if (!data) {
				// prompts the user with an error message
				frappe.msgprint(
					repl("User %(user)s not found!", { "user": frm.doc.allocated_to_email })
				)

				// let's clear the field
				frm.set_value("allocated_to_email", undefined)

				// this validation failed 
				// let's prevent the user from saving the document
				validated = false
			}
		})
	}
})
