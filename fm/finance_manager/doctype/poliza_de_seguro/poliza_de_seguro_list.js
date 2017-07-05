frappe.listview_settings["Poliza de Seguro"] = {
	add_fields: ["status"],
	onload: function(page) {
		frappe.route_options = {
			"status": "Activo"
		}
	},
	get_indicator: function(doc) {
		if (doc.status == "Activo") {
			return ["Activo", "blue", "status,=,Activo"]
		} else if (doc.status == "Inactivo") {
			return ["Inactivo", "orange", "status,=,Inactivo"]
		}
	}
}