
frappe.ui.form.on("Tabla Amortizacion", "repayment_schedule_add", function(frm) {
	msgprint("You can not select past date in From Date");
});