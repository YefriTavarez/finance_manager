frappe.listview_settings['Loan'] = {
	add_fields: ["status", "docstatus"],

	// not working
	// filters: [
	// 	["status", "!=", "Repaid/Closed"],
	// 	["docstatus", "!=", 2]
	// ],

	get_indicator: function(doc) {
		if(doc.status === "Sanctioned"){
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