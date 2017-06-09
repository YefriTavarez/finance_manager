import frappe
from datetime import date

@frappe.whitelist()
def get_next_repayment_schedule(chasis_no):
	loan_id = frappe.get_value("Loan", { "asset": chasis_no }, "name")

	if not loan_id:
		next_month = frappe.utils.add_months(date.today(), 1)

		return next_month.strftime("%Y-%m-%d")

	loan = frappe.get_doc("Loan", loan_id)

	pagos_vencidos = [row for row in loan.repayment_schedule if row.estado == "PENDIENTE"]

	pagare = pagos_vencidos[0]

	fecha_pagare = pagare.fecha

	return fecha_pagare.strftime('%Y-%m-%d')

	