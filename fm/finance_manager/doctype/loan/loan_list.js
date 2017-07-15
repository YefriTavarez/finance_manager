frappe.listview_settings['Loan'] = {
	add_fields: ["status", "docstatus"],
	onload: function(listview) {
		var filters = {
			"status": ["=","Sanctioned"]
		}

		if (frappe.user.has_role("Gerente de Operaciones")) {
			filters = {
				"status": ["!=","Repaid/Closed"]
			}
		} else if (frappe.user.has_role("Cobros")){
			filters = {
				"status": ["!=","Repaid/Closed"],
				"docstatus": ["=", "1"]
			}
		} else if (frappe.user.has_role("Financiamiento")){
			$.extend(filters, {
				"owner": frappe.user.name
			})
		} else if (frappe.user.has_role("Cajera")){
			filters = {
				"status": "Fully Disbursed"
			}
		} else if (frappe.user.has_role("Contador")){
			$.extend(filters, {
				"docstatus": ["=", "1"]
			})
		}

		frappe.route_options = filters
	},

	// not working
	// filters: [
	// 	["status", "!=", "Repaid/Closed"],
	// 	["docstatus", "!=", 2]
	// ],

	get_indicator: function(doc) {
		if(doc.status === "Sanctioned") {
			return [__("Sanctioned"), "orange", "status,=,Sanctioned"]
		} else if (doc.status === "Partially Disbursed") {
			return [__("Partially Disbursed"), "darkgrey", "status,=,Partially Disbursed"]
		} else if(doc.status === "Fully Disbursed") {
			return [__("Fully Disbursed"), "blue", "status,=,Fully Disbursed"]
		} else if(doc.status === "Repaid/Closed") {
			return [__("Repaid/Closed"), "green", "status,=,Repaid/Closed"]
		}
	}
}