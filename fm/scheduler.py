import frappe
from math import ceil

from fm.api import FULLY_PAID
from frappe.utils import flt, nowdate

def calculate_fines():

	# global defaults
	fine = frappe.db.get_single_value("FM Configuration", "vehicle_fine")
	grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
	fine_rate = flt(fine) / 100.000

	# today as string to operate with other dates
	today = str(nowdate())

	# let's begin
	for loan in frappe.get_list("Loan", { "docstatus": "1", "status": "Fully Disbursed" }):

		due_repayment_list = []

		doc = frappe.get_doc("Loan", loan.name) # load from db
		for row in doc.get("repayment_schedule"):

			# date diff in days
			date_diff = frappe.utils.date_diff(today, row.fecha)
			due_payments = ceil(date_diff / 30.000)
			due_date = frappe.utils.add_days(row.fecha, 0.000 if due_payments > 1.000 else int(grace_days))
			new_fine = fine_rate * doc.monthly_repayment_amount * due_payments

			if not row.estado == FULLY_PAID and today > str(due_date):

				if not ceil(new_fine) == flt(row.fine):
					row.fine = ceil(new_fine) # setting the new fine
					row.due_date = due_date # setting the new due date
					doc.due_payments = due_payments # setting the new due payments

					row.monto_pendiente = flt(row.cuota) + flt(row.fine) + flt(row.insurance)
					row.update_status()

					# updating
					row.db_update()
					doc.db_update()

					due_repayment_list.append(row)
					
		if due_repayment_list:
			create_todo(doc, due_repayment_list)

def create_todo(doc, due_rows):
	# payments that are already due
	due_payments = len(due_rows)

	# load from db the default email for ToDos
	allocated_to = frappe.db.get_single_value("FM Configuration" , "allocated_to_email")

	customer_currency = frappe.db.get_value("Customer", doc.customer, "default_currency")

	# load defaults
	description_tmp = ""
	description = get_description()

	total_debt = 0

	for idx, row in enumerate(due_rows):
		# calculated values
		total_overdue_amount = flt(row.fine) + flt(doc.monthly_repayment_amount)
		description_tmp += """<br/><li> Para el pagare vencido de fecha <i>{1}</i> el cargo por mora asciende 
			a <i>{5} ${2} {6}</i> ademas de <i>{5} ${3} {6} </i> por la cuota de dicho pagare para una deuda total 
			de <i>{5} ${4}</i> {6} solo por ese pagare.</li>"""
		
		description_tmp = description_tmp.format(
			idx +1, # add 1 to make it natural
			row.due_date,
			row.fine,
			doc.monthly_repayment_amount,
			total_overdue_amount,
			"RD" if customer_currency == "DOP" else "US",
			"Pesos" if customer_currency == "DOP" else "Dolares"
		)

		total_debt += total_overdue_amount

	# ok, let's begin
	t = frappe.new_doc("ToDo")

	t.assigned_by = allocated_to
	t.owner = allocated_to
	t.reference_type = doc.doctype
	t.reference_name = doc.name

	t.description = description.format(
		doc.customer, 
		due_payments, 
		nowdate(),
		description_tmp,
		doc.name,
		total_debt,
		"RD" if customer_currency == "DOP" else "US",
		"Pesos" if customer_currency == "DOP" else "Dolares"
	)

	t.insert()

def get_description():
	# the ToDo description
	description = """El cliente <b>{0}</b> tiene <b style="color:#ff5858">{1}</b> pagares vencidos a la fecha de hoy 
		<i>{2}</i>: <ol>{3}</ol><br/> <span style="margin-left: 3.5em"> Para una deuda total <b>{6}$ {5}</b> {7}, 
		mas informacion en el enlace debajo.</span"""

	return description

def get_expired_insurance():
	days_to_expire = frappe.db.get_single_value("FM Configuration", "renew_insurance")

	insurance_list = frappe.db.sql("""SELECT loan.customer, loan.asset
		FROM `tabPoliza de Seguro` AS poliza 
		JOIN tabLoan AS loan 
		ON loan.name = poliza.loan 
		WHERE DATEDIFF(poliza.end_date, NOW()) <= %s""" % days_to_expire, 
	as_dict=True)

	for vehicle in insurance_list:

		create_expired_insurance_todo(
			frappe.get_doc("Vehicle", vehicle.name), 
			vehicle.days
		)

def create_expired_insurance_todo(doc, days):

	# load from db the default email for ToDos
	allocated_to = frappe.db.get_single_value("FM Configuration", "allocated_to_email")
	description = get_expired_insurance_description()
	# ok, let's begin
	t = frappe.new_doc("ToDo")

	t.assigned_by = "Administrator"
	t.owner = allocated_to
	t.reference_type = doc.doctype
	t.reference_name = doc.name

	t.description = description.format(
		doc.make, 
		doc.model, 
		doc.license_plate, 
		days
	)

	t.insert()

def get_expired_insurance_description():

	# the ToDo description
	description = """El vehiculo <b>{0} {1}</b> placa <b>{2}</b>  le faltan <b style="color:#ff5858">{3}</b> dias para 
		vencer por favor renovar, mas informacion en el enlace debajo."""

	return description

def update_insurance_status():
	current_date = frappe.utils.nowdate()

	insurance_list = frappe.get_list("Poliza de Seguro", {
		"end_date": ["<=", current_date],
		"status": "Activo",
		"docstatus": "1"
	})

	for insurance in insurance_list:
		doc = frappe.get_doc("Poliza de Seguro", insurance.name)

		doc.status = "Inactivo"
		doc.db_update()

def update_exchange_rates():
	from fm.api import exchange_rate_USD

	today = nowdate()

	# load the Currency Exchange docs that were created when installing
	# the app and update them in a daily basis
	usddop = frappe.get_doc("Currency Exchange", "USD-DOP")
	dopusd = frappe.get_doc("Currency Exchange", "DOP-USD")

	# update the date field to let the user
	# know that it's up to date
	usddop.date = today
	dopusd.date = today

	# fetch the exchange rate from USD to DOP
	dop = exchange_rate_USD('DOP')

	if dop:
		usddop.exchange_rate = round(dop)
		usddop.save()

		dopusd.exchange_rate = round(dop)
		dopusd.save()
		 