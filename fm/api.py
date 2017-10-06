# -*- encoding: utf-8 -*-

import frappe
import requests
from frappe.utils import add_to_date

PENDING = "PENDIENTE"
FULLY_PAID = "SALDADA"
PARTIALLY_PAID = "ABONO"
OVERDUE = "VENCIDA"


def get_repayment(loan, repayment):
	for row in loan.repayment_schedule:
		if row.name == repayment:
			return row

def get_paid_amount(account, journal_entry, fieldname):

	result = 0.000
	for current in get_accounts_and_amounts(journal_entry):

		if account == current.account and fieldname == current.fieldname:
			return current.amount

	return result

def get_paid_amount2(account, journal_entry):

	result = 0.000
	for current in get_accounts_and_amounts2(journal_entry):

		if account == current.account:
			return current.amount

	return result

def get_accounts_and_amounts(journal_entry):
	return frappe.db.sql("""SELECT child.account, 
		child.credit_in_account_currency AS amount, child.repayment_field AS fieldname
	FROM 
		`tabJournal Entry` AS parent 
	JOIN 
		`tabJournal Entry Account` AS child 
	ON 
		parent.name = child.parent 
	WHERE 
		parent.name = '%s' 
	ORDER BY 
		child.idx""" 
	% journal_entry, as_dict=True)

def get_accounts_and_amounts2(journal_entry):
	return frappe.db.sql("""SELECT child.account, 
		child.credit_in_account_currency + child.debit_in_account_currency AS amount, child.repayment_field AS fieldname
	FROM 
		`tabJournal Entry` AS parent 
	JOIN 
		`tabJournal Entry Account` AS child 
	ON 
		parent.name = child.parent 
	WHERE 
		parent.name = '%s' 
	ORDER BY 
		child.idx""" 
	% journal_entry, as_dict=True)

def update_insurance_status(new_status, row_name):
	if frappe.get_value("Insurance Repayment Schedule", { "name": row_name }, "name"):
		insurance_row = frappe.get_doc("Insurance Repayment Schedule", row_name)

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

	if not ARGS.get("app_id"):
		return 0 # exit code is zero
		
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
	
@frappe.whitelist()
def authorize(usr, pwd, reqd_level):
	from frappe.auth import check_password

	validated = False

	try:
		validated = not not check_password(usr, pwd)
	except:
		pass

	if validated:
		doc = frappe.get_doc("User", usr)

		role_list = [ row.role for row in doc.user_roles ]

		return reqd_level in role_list
	else: return False

@frappe.whitelist()
def get_currency(loan, account):
	return account if loan.customer_currency == "DOP" \
		else account.replace("DOP", "USD")

def get_paid_amount_for_loan(customer, posting_date):
	result = frappe.db.sql("""SELECT IFNULL(SUM(child.credit_in_account_currency), 0.000) AS amount
		FROM `tabJournal Entry` AS parent 
		JOIN `tabJournal Entry Account` AS child 
		ON parent.name = child.parent 
		WHERE child.party = '%(customer)s'
		AND parent.posting_date >= '%(posting_date)s'""" % {
			"customer": customer, "posting_date": posting_date })

	return result[0][0]

def get_pending_amount_for_loan(customer, posting_date):
	result = frappe.db.sql("""SELECT (IFNULL(SUM(child.debit_in_account_currency), 0.000) # what he was given
			- IFNULL(SUM(child.credit_in_account_currency), 0.000)) AS amount  # vs. what's he's already paid
		FROM `tabJournal Entry` AS parent 
		JOIN `tabJournal Entry Account` AS child 
		ON parent.name = child.parent 
		WHERE child.party = '%(customer)s'
		AND parent.posting_date >= '%(posting_date)s'""" % { 
			"customer": customer, "posting_date": posting_date })

	return result[0][0]

def create_purchase_invoice( amount, item_type, docname, is_paid=1.00 ):
	import erpnext 
	company = frappe.get_doc("Company", erpnext.get_default_company())
	#Let's get the default supplier for the PINV
	supplier = frappe.db.get_single_value("FM Configuration", "default_{0}_supplier".format(item_type.lower()))

	if not supplier:
		frappe.throw("No se Encontro Ningun Suplidor para {0}".format(item_type))

	item = frappe.new_doc("Item")
	item_name = frappe.get_value("Item", { "item_group": item_type })

	# let's see if it exists
	if item_name:
		item = frappe.get_doc("Item", item_name)
	else:
		# ok, let's create it 
		item.item_group = item_type
		item.item_code = item.item_name = "%s Services" % item_type
		item.insert()

	if not supplier:
		frappe.throw("No se ha seleccionado un suplidor de {0}".format(item_type))

	pinv = frappe.new_doc("Purchase Invoice")

	pinv.supplier = supplier
	pinv.is_paid = 1.000
	pinv.company = company.name
	pinv.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
	pinv.cash_bank_account = company.default_bank_account
	pinv.paid_amount = amount
	pinv.base_paid_amount = amount

	# ensure this doc is linked to the new purchase
	pinv.linked_doc = docname

	pinv.append("items", {
		"item_code": item.item_code,
		"is_fixed_item": 1,
		"item_name": item.item_name,
		"qty": 1,
		"rate": amount
	})

	pinv.flags.ignore_permissions = True
	pinv.submit()

	return pinv.name

def customer_autoname(doc, event):
	from fm.utilities import s_sanitize
	doc.name = s_sanitize(doc.customer_name)

def on_session_creation():
	msg = "User {} has now logged in at {}".format(frappe.session.user, frappe.utils.now_datetime())
	frappe.publish_realtime(event="msgprint", message=msg, user="yefri@soldeva.com")