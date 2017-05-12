import frappe
from datetime import date
from math import ceil


def calculate_fines():
	# global defaults
	fine = frappe.db.get_single_value("FM Configuration", "vehicle_fine")
	grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
	fine_rate = float(fine) / 100
	today = date.today()

	# log to the console
	print "================================================================="
	print "********** Executing job -> calculate_fines **********"
	print "================================================================="

	# let's begin
	for loan in frappe.get_list("Loan", {"docstatus":1, "status": "Fully Disbursed" }):
		print "************** Evaluating Loan -> {} **************".format(loan.name)
		print "-----------------------------------------------------------------"

		# clear repayment list array
		due_repayment_list = []

		doc = frappe.get_doc("Loan", loan.name) # load from db
		for row in doc.get("repayment_schedule"):
			print "Evaluating Loan row -> {0}".format(row.idx)

			# date diff in days
			date_diff = frappe.utils.date_diff(today, row.fecha)
			due_payments = ceil(date_diff / 30.0)
			due_date = frappe.utils.add_days(row.fecha, 0 if due_payments > 1 else int(grace_days))
			new_fine = fine_rate * doc.monthly_repayment_amount * due_payments

			if row.estado == "PENDIENTE" and today > due_date:
				print "Row {0} is already due with {1} months".format(row.idx, due_payments)

				if not ceil(new_fine) == float(row.fine):
					print "Row {0} is out of date. Updating!".format(row.idx)

					row.fine = ceil(new_fine) # setting the new fine
					row.due_date = due_date # setting the new due date
					doc.due_payments = due_payments # setting the new due payments
					doc.db_update() # updating the document

					due_repayment_list.append(row)
					
					print "amount -> {0}".format(doc.monthly_repayment_amount)
					print "due_payments -> {0}".format(due_payments)
					print "fine rate -> {0}".format(fine_rate)
					print "fine -> {0}".format(row.fine)
				else:
					print "Row {0} is up to date. Nothing to do!".format(row.idx)

			else:
				print "Row {0} is fine. Skipping!".format(row.idx)

			if due_repayment_list:
				create_todo(doc, due_repayment_list)
			print "-----------------------------------------------------------------"

		print "*****************************************************************"
	print "================================================================="


def create_todo(doc, due_rows):
	# payments that are already due
	due_payments = len(due_rows)

	# load from db the default email for ToDos
	allocated_to = frappe.db.get_single_value("FM Configuration" , "allocated_to_email")

	# load defaults
	description_tmp = ""
	description = get_description()

	for r in due_rows:
		# calculated values
		total_overdue_amount = float(r.fine) + float(doc.monthly_repayment_amount)

		description_tmp += "Para el pagare vencido No. {0} de fecha {1} el cargo por mora asciende a RD ${2} Pesos "
		description_tmp += "ademas de RD ${3} Pesos por la cuota de dicho pagare para una deuda total de RD ${4} "
		description_tmp += "Pesos solo por ese pagare. "
		
		description_tmp = description_tmp.format(
			r.idx,
			r.due_date,
			r.fine,
			doc.monthly_repayment_amount,
			total_overdue_amount
		)
		
	# ok, let's begin
	t = frappe.new_doc("ToDo")

	t.allocated_by = "Administrator"
	t.allocated_to = allocated_to
	t.reference_type = doc.doctype
	t.reference_name = doc.name
	t.description = description.format(
		doc.customer, 
		due_payments, 
		date.today(),
		description_tmp
	)

	t.insert()

def get_description():
	# the ToDo description
	description = "El cliente {0} tiene {1} pagares vencidos a la fecha de hoy {2}. {3}"
	description += "Para ver mas detalles de este prestamo. Busque el campo de Referencia "
	description += "mas abajo y abra el prestamo."

	return description

