// Copyright (c) 2017, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('FM Configuration', {
	refresh: function(frm) {

	},
	allocated_to_email: function (frm) {
		if(frm.doc.allocated_to_email=="") return;
		
		frappe.model.get_value('User', {'email': frm.doc.allocated_to_email}, 'email',
		  	function(d) {
		   	if(d)
		   	{
		   		frm.set_value("allocated_to_email",d.email);
		   	}	
		   	else
		   	{
		   		frm.set_value("allocated_to_email","");
		   		frappe.msgprint("No existe ningun usuario con el correo ingresado. Debe ingresar un usuario valido");
		   	}	
		});
	}
});
