import frappe
from datetime import date
from math import ceil

from fm.api import PENDING


def calculate_fines():

	# setting and fetching global defaults
	fine = frappe.db.get_single_value("FM Configuration", "vehicle_fine")
	grace_days = frappe.db.get_single_value("FM Configuration", "grace_days")
	fine_rate = float(fine) / 100.0

	today = date.today()

	# let's begin
	for loan in frappe.get_list("Loan", { "docstatus": 1, "status": "Fully Disbursed" }):

		due_repayment_list = []

		doc = frappe.get_doc("Loan", loan.name) # load from db
		for row in doc.get("repayment_schedule"):

			# date diff in days
			date_diff = frappe.utils.date_diff(today, row.fecha)
			due_payments = ceil(date_diff / 30.0)
			due_date = frappe.utils.add_days(row.fecha, 0 if due_payments > 1 else int(grace_days))
			new_fine = fine_rate * doc.monthly_repayment_amount * due_payments

			if row.estado == PENDING and today > due_date:

				if not ceil(new_fine) == float(row.fine):
					row.fine = ceil(new_fine) # setting the new fine
					row.due_date = due_date # setting the new due date
					doc.due_payments = due_payments # setting the new due payments

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

	# load defaults
	description_tmp = ""
	description = get_description()

	total_debt = 0

	for idx, row in enumerate(due_rows):
		# calculated values
		total_overdue_amount = float(row.fine) + float(doc.monthly_repayment_amount)
		description_tmp += """<br/><br/> &emsp;{0} - Para el pagare vencido de fecha <i>{1}</i> el cargo por mora asciende 
			a <i>RD ${2} Pesos</i> ademas de <i>RD ${3} Pesos </i> por la cuota de dicho pagare para una deuda total 
			de <i>RD ${4}</i> Pesos solo por ese pagare."""
		
		description_tmp = description_tmp.format(
			idx +1, # add 1 to make it natural
			row.due_date,
			row.fine,
			doc.monthly_repayment_amount,
			total_overdue_amount
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
		date.today(),
		description_tmp,
		doc.name,
		total_debt
	)

	t.insert()

def get_description():
	# the ToDo description
	description = """El cliente <b>{0}</b> tiene <b style="color:#ff5858">{1}</b> pagares vencidos a la fecha de hoy 
		<i>{2}</i>: {3}<br/><br/> Para una deuda total <b>RD$ {5}</b>, mas informacion en el enlace debajo."""

	return description

def get_expired_insurance():
	days_to_expire = frappe.db.get_single_value("FM Configuration", "renew_insurance")

	vehicle_list = frappe.db.sql("""SELECT loan.asset AS name, DATEDIFF(vehicle.end_date, NOW()) AS days 
		FROM tabLoan AS loan 
		JOIN tabVehicle AS vehicle 
		ON loan.asset = vehicle.name 
		WHERE loan.docstatus = 1 
		AND loan.status = 'Fully Disbursed' 
		AND DATEDIFF(vehicle.end_date, NOW()) >= %s""" % days_to_expire, 
	as_dict=True)

	for vehicle in vehicle_list:

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

def update_exchange_rates():
	from fm.api import exchange_rate_USD
	from datetime import date

	today = date.today()

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
		usddop.exchange_rate = dop
		usddop.save()

		dopusd.exchange_rate = dop
		dopusd.save()
		 