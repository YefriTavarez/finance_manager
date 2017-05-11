import frappe
from datetime import date
from math import ceil

def calculate_fines():
	print "================================================================="
	print "**** Executing job"
	print "================================================================="
	# global defaults
	fine = frappe.db.get_single_value("FM Configuration", "vehicle_fine")
	grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
	fine_rate = float(fine) / 100
	today = date.today()

	# let's begin
	for loan in frappe.get_list("Loan",{"docstatus":1,"status":["=","Fully Disbursed"]}):
		doc = frappe.get_doc("Loan",loan.name)
		print "Loan -> {}".format(doc.name)
		for row in doc.get("repayment_schedule"):
			# date diff in days
			date_diff = frappe.utils.date_diff(today, row.fecha)
			if row.estado == "PENDIENTE" and frappe.utils.add_days(row.fecha, int(grace_days)) < today:
				print "estado -> {}".format(row.estado)
				print "row fecha -> {}".format(frappe.utils.add_days(row.fecha, int(grace_days)))
				print "today -> {}".format(today)
				print row.estado
				if not (fine_rate * doc.monthly_repayment_amount * ceil(date_diff / 30.0) == row.fine:
					row.fine = fine_rate * doc.monthly_repayment_amount * ceil(date_diff / 30.0) 
					doc.save()
					
					print "amount -> {}".format(doc.monthly_repayment_amount)
					print "fine rate -> {}".format(fine_rate)
					print "fine -> {}".format(row.fine)
	print "================================================================="
