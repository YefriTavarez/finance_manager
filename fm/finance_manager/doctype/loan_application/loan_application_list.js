frappe.listview_settings['Loan Application'] = {
	add_fields: [
		"status",
		"docstatus"
	],
	onload: function(listview) {
		frappe.route_options = {
			"owner": frappe.user.name,
			"docstatus": ["!=", "2"],
			"status": ["!=", "Rejected"]
		}
	},
	get_indicator: function(doc) {
		if (doc.status == "Open") {
			return [__("Open"), "orange", "status,=,Open"]
		} else if (doc.status == "Rejected") {
			return [__("Rejected"), "red", "status,=,Rejected"]
		} else if(doc.status == "Linked") {
			return [__("Linked"), "blue", "status,=,Linked"]
		} else if(doc.status == "Approved") {
			return [__("Approved"), "green", "status,=,Approved"]
		}
	}
}