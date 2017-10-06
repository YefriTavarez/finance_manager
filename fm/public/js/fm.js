
function developer_mode(){
	var doctype = docname = "FM Configuration"
	var dev_mode = 0
		frappe.db.get_value(doctype, docname, "developer_mode", function(data) {
		dev_mode = data.developer_mode
	})
	console.log(dev_mode)
}