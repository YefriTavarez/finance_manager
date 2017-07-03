import frappe
import requests
from frappe.utils import add_to_date


PENDING = "PENDIENTE"
FULLY_PAID = "SALDADA"
PARTIALLY_PAID = "ABONO"
OVERDUE = "VENCIDA"

def get_currency(loan, account):
	return account if loan.customer_currency == "DOP" \
		else account.replace("DOP", "USD")

def get_repayment(loan, repayment):
	for row in loan.repayment_schedule:
		if row.name == repayment:
			return row

def get_paid_amount(account, journal_entry):
	for current in get_accounts_and_amounts(journal_entry):
		if account == current.account:
			return current.amount
	else:
		return 0.000

def get_accounts_and_amounts(journal_entry):
	return frappe.db.sql("""SELECT child.account, child.debit_in_account_currency,
		child.credit_in_account_currency AS amount
	FROM `tabJournal Entry` AS parent 
	JOIN `tabJournal Entry Account` AS child 
	ON parent.name = child.parent 
	WHERE parent.name = '%s'""" % journal_entry, as_dict=True)

def update_insurance_status(new_status, row_name, is_new=True):
	def get_correponding_insurance_row(row_name):
		result = frappe.db.sql("""SELECT insurance.name
			FROM `tabInsurance Repayment Schedule` AS insurance 
			join `tabPoliza de Seguro` AS poliza ON poliza.name = insurance.parent 
			JOIN `tabTabla Amortizacion` AS repayment ON repayment.parent = poliza.loan  
			WHERE repayment.name = '%s' 
			AND insurance.date <= repayment.fecha
			AND insurance.status =%s LIMIT 1""" % 
		(row_name, "'PENDIENTE'" if is_new else "'SALDADO' OR 'ABONO'"))

		return result[0][0] if result else 0.000

	insurance_name = get_correponding_insurance_row(row_name)

	if insurance_name:
		insurance_row = frappe.get_doc("Insurance Repayment Schedule", insurance_name)

		insurance_row.status = new_status
		insurance_row.db_update()

def from_en_to_es(string):
	return {
		# days of the week
		"Sunday": "Domingo",
		"Monday": "Lunes",
		"Tuesday": "Martes",
		"Wednesday": "Miercoles",
		"Thursday": "Jueves",
		"Friday": "Viernes",
		"Saturday": "Sabado",

		# months of the year
		"January": "Enero",
		"February": "Febrero",
		"March": "Marzo",
		"April": "Abril",
		"May": "Mayo",
		"June": "Junio",
		"July": "Julio",
		"August": "Agosto",
		"September": "Septiembre",
		"October": "Octubre",
		"November": "Noviembre",
		"December": "Diciembre" 
	}[string]

def add_months(date, months):
	return add_to_date(date, months=months, as_datetime=True)

def get_voucher_type(mode_of_payment):
	# fetch the mode of payment type
	_type = frappe.db.get_value("Mode of Payment", mode_of_payment, "type")

	return {
		"General": "Journal Entry",
		"Bank": "Bank Entry",
		"Cash": "Cash Entry"
	}[_type]

@frappe.whitelist()
def next_repayment(loan):
	doc = frappe.get_doc("Loan", loan)

	for repayment in doc.repayment_schedule:
		if not repayment.estado == FULLY_PAID:
			return repayment # the first found in the table

def get_exchange_rates(base):
	from frappe.email.queue import send

	URL = "http://openexchangerates.org/api/latest.json"

	ARGS = {
		# my app id for the service
		"app_id": frappe.db.get_single_value("FM Configuration", "app_id"), 
		# base currency that we are going to be working with
		"base": base
	}

	# sending the request
	response = requests.get(url=URL, params=ARGS)

	# convert to json the response
	obj = response.json()

	rates = obj["rates"]

	if not rates:
		send(
			recipients=["yefri@soldeva.com"],
			sender="yefritavarez@gmail.com",
			subject="No rates when requesting to openexchangerates.org",
			message="There was an error while fetching today's rates",
			now=True
		)

	return rates


@frappe.whitelist()
def exchange_rate_USD(currency):
	from frappe.email.queue import send
	
	rates = get_exchange_rates('USD')

	exchange_rate = rates[currency]

	if not exchange_rate:
		send(
			recipients=['yefri@soldeva.com'],
			sender='yefritavarez@gmail.com',
			subject='Failed to find {currency} Currency'.format(currency=currency),
			message='We were unable to find the {currency} Currency in the rates list'.format(currency=currency),
			now=True
		)

		return 0.000

	return exchange_rate

@frappe.whitelist()
def get(doctype, name=None, filters=None):
	import frappe.client
	
	try:
		frappe.client.get(doctype, name, filters)
	except:
		pass
	