// Copyright (c) 2016, Soldeva, SRL and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vivienda', {
	refresh: function(frm) {

	},
	owner_first_name:function (frm){
		var name=frm.doc.owner_first_name.trim();	
		frm.set_value("owner_first_name",(name).toUpperCase());
		if(frm.doc.owner_last_name)
			frm.set_value("owner_full_name",frm.doc.owner_first_name+" "+frm.doc.owner_last_name);
		else
			frm.set_value("nombre_completo",frm.doc.owner_first_name);	

	},
	owner_last_name:function(frm){
		var name=frm.doc.owner_last_name.trim();	
		frm.set_value("owner_last_name",(name).toUpperCase());
		if(frm.doc.owner_first_name)
			frm.set_value("owner_full_name",frm.doc.owner_first_name+" "+frm.doc.owner_last_name);
		else
			frm.set_value("nombre_completo",frm.doc.owner_last_name);	

	}
});
