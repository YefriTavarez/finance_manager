import frappe
from datetime import date

@frappe.whitelist()
def get_next_repayment_schedule(chasis_no):
    loan_id = frappe.get_value("Loan",{"asset":chasis_no},"name")
    if not loan_id:
         return (frappe.utils.add_months(date.today(),1)).strftime("%Y-%m-%d")
    loan = frappe.get_doc("Loan",loan_id)
    pagos_vencidos = filter( lambda row:row.estado == "PENDIENTE",loan.repayment_schedule)

    return (pagos_vencidos[0].fecha).strftime('%Y-%m-%d')

    