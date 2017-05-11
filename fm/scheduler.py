import frappe
from datetime import date
from math import ceil

def calculate_fines():
	print "================================================================="
	print "********** Executing job -> calculate_fines **********"
	print "================================================================="
	# global defaults
	fine = frappe.db.get_single_value("FM Configuration", "vehicle_fine")
	grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
	fine_rate = float(fine) / 100
	today = date.today()

	# let's begin
	for loan in frappe.get_list("Loan", {"docstatus":1, "status": "Fully Disbursed" }):
		print "************** Evaluating Loan -> {} **************".format(loan.name)
		print "-----------------------------------------------------------------"

		doc = frappe.get_doc("Loan", loan.name) # load from db

		for row in doc.get("repayment_schedule"):
			print "Evaluating Loan row -> {}".format(row.idx)

			# date diff in days
			date_diff = frappe.utils.date_diff(today, row.fecha)
			due_payments = ceil(date_diff / 30.0)
			due_date = frappe.utils.add_days(row.fecha, 0 if due_payments > 1 else int(grace_days))
			new_fine = fine_rate * doc.monthly_repayment_amount * due_payments

			if row.estado == "PENDIENTE" and today > due_date:
				print "Row {} is already due with {} months".format(row.idx, due_payments)

				if not ceil(new_fine) == float(row.fine):
					print "Row {} is out of date. Updating!".format(row.idx)

					row.fine = ceil(new_fine) # setting the new fine
					doc.db_update() # updating the document
					
					print "amount -> {}".format(doc.monthly_repayment_amount)
					print "due_payments -> {}".format(due_payments)
					print "fine rate -> {}".format(fine_rate)
					print "fine -> {}".format(row.fine)
				else:
					print "Row {} is up to date. Nothing to do!".format(row.idx)
			else:
				print "Row {} is fine. Skipping!".format(row.idx)

			print "-----------------------------------------------------------------"

		print "*****************************************************************"

	print "================================================================="
