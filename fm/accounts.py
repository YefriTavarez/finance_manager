# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import fm.api

from frappe import _
from datetime import datetime
from fm.api import *
from frappe.utils import flt

from fm.finance_manager.doctype.loan.loan import get_monthly_repayment_amount

def submit_journal(doc, event):
	if doc.loan and not doc.es_un_pagare:

		# load the loan from the database
		loan = frappe.get_doc("Loan", doc.loan)

		curex = frappe.get_doc("Currency Exchange", 
			{"from_currency": "USD", "to_currency": "DOP"})

		exchange_rate = curex.exchange_rate

		if loan.customer_currency == "DOP":
			exchange_rate = 1.000

		if not loan.total_payment == round(doc.total_debit / exchange_rate):
			frappe.throw("El monto desembolsado difiere del monto del prestamo!")

		# call the update status function
		loan.update_disbursement_status()

		# update the database
		loan.db_update()

def cancel_journal(doc, event):
	if not doc.loan:
		return 0.000 # exit code is zero

	filters = { 
		"loan": doc.loan,
		"es_un_pagare": "1" 
	}

	if not doc.es_un_pagare:

		if frappe.get_list("Journal Entry", filters):
			frappe.throw("No puede cancelar este desembolso con pagares hechos!")
	
		# load the loan from the database
		loan = frappe.get_doc("Loan", doc.loan)

		# call the update status function
		loan.update_disbursement_status()

		# update the database
		loan.db_update()

		return 0.000 # to exit the function
	 		
	else: update_repayment_amount(doc)
	
def update_repayment_amount(doc):

	loan = frappe.get_doc("Loan", doc.loan)

	# load the repayment to work it
	row = fm.api.get_repayment(loan, doc.pagare)

	if not row:
		frappe.throw("No se encontro ningun pagare asociado con esta Entrada de Pago.<br>\
			Es posible que se haya marcado como un pagare sin tener alguno asociado!")

	paid_amount = 0.000
	filters = { "pagare": row.name, "name": ["!=", doc.name] }

	# let's see how much the customer has paid so far for this repayment
	for journal in frappe.get_list("Journal Entry", filters, "total_amount"):
		paid_amount += journal.total_amount
	
	# let see if we're canceling the jv
	if doc.docstatus == 2.000:

		creditors = frappe.db.get_single_value("FM Configuration", "account_of_suppliers")
		interest_on_loans = frappe.db.get_single_value("FM Configuration", "interest_on_loans")

		row.capital = fm.api.get_paid_amount(loan.customer_loan_account, doc.name) + row.capital
		row.interes = fm.api.get_paid_amount(loan.interest_income_account, doc.name) + row.interes
		
		row.fine = fm.api.get_paid_amount(interest_on_loans, doc.name) + row.fine
		row.insurance = fm.api.get_paid_amount(loan.customer_loan_account, doc.name, False) + row.insurance

		# let's make sure we update the status to the corresponding
		# row in the insurance doc
		fm.api.update_insurance_status("PENDIENTE", row.insurance_doc)

	curex = frappe.get_doc("Currency Exchange", 
		{"from_currency": "USD", "to_currency": "DOP"})

	exchange_rate = curex.exchange_rate

	if loan.customer_currency == "DOP":
		exchange_rate = 1.000

	# duty will be what the customer has to pay for this repayment
	duty = flt(row.capital) + flt(row.interes) + flt(row.fine) + round(row.insurance / exchange_rate)

	# then, the outstanding amount will be the 
	# duty less what he's paid so far
	row.monto_pendiente = duty - paid_amount

	# pass the latest paid amount so that it can update the loan status
	# with the realtime data that is out of date when this is run 

	# update the status of the repayment
	row.update_status()

	# save to the database
	row.db_update()

	loan.update_disbursement_status()
	loan.db_update()

def get_repayment_details(loantype):

	# validate that the interest type is simple
	if loantype.interest_type == "Simple":
		return get_simple_repayment_details(loantype)

	elif loantype.interest_type == "Composite":
		return get_compound_repayment_details(loantype)		

def get_simple_repayment_details(loantype):
	# if there's not rate set
	if not loantype.rate_of_interest: 	
		# now let's fetch from the DB the default rate for interest simple
		loantype.rate_of_interest = frappe.db.get_single_value("FM Configuration", "simple_rate_of_interest")

	# convert the rate of interest to decimal
	loantype.rate = flt(loantype.rate_of_interest) / 100.000

	# calculate the monthly interest
	loantype.monthly_interest = round(loantype.loan_amount * loantype.rate)

	# ok, now let's check the repayment method
	if loantype.repayment_method == "Repay Over Number of Periods":

		# total interest
		loantype.total_payable_interest = loantype.monthly_interest * loantype.repayment_periods

		# calculate the monthly capital
		loantype.monthly_capital = flt(loantype.loan_amount) / flt(loantype.repayment_periods)

	elif loantype.repayment_method == "Repay Fixed Amount per Period":
		
		# calculate the monthly capital
		loantype.monthly_capital = flt(loantype.monthly_repayment_amount) - loantype.monthly_interest

		if loantype.monthly_capital < 0.000:
			frappe.throw(_("Monthly repayment amount cannot be less than the monthly interest!"))

		# calculate the repayment periods based on the given monthly repayment amount
		loantype.repayment_periods = flt(loantype.loan_amount) / flt(loantype.monthly_capital)

		# total interest
		loantype.total_payable_interest = loantype.monthly_interest * loantype.repayment_periods

	# get the monthly repayment amount
	loantype.monthly_repayment_amount = round(loantype.monthly_interest + loantype.monthly_capital)

	# calculate the total payment
	loantype.total_payable_amount = loantype.monthly_repayment_amount * loantype.repayment_periods

def get_compound_repayment_details(loantype):
	# if there's not rate set
	if not loantype.rate_of_interest: 
		# now let's fetch from the DB the default rate for interest compound
		loantype.rate_of_interest = frappe.db.get_single_value("FM Configuration", "composite_rate_of_interest")
	
	if loantype.repayment_method == "Repay Over Number of Periods":
		loantype.repayment_amount = \
			get_monthly_repayment_amount(
				loantype.interest_type,
				loantype.repayment_method, 
				loantype.loan_amount, 
				loantype.rate_of_interest, 
				loantype.repayment_periods
			)

	if loantype.repayment_method == "Repay Fixed Amount per Period":

		# convert the rate to decimal
		monthly_interest_rate = flt(loantype.rate_of_interest) / 100.000

		if monthly_interest_rate:
			loantype.repayment_periods = round(
				flt(
					log(loantype.repayment_amount) 
					- log(loantype.repayment_amount 
						- flt(loantype.loan_amount 
							* monthly_interest_rate ))) 
				/ flt(log(monthly_interest_rate	+1 ))
			)
		else:
			loantype.repayment_periods = loantype.loan_amount / loantype.repayment_amount

	loantype.calculate_payable_amount()

def make_simple_repayment_schedule(loantype):
	from fm.api import from_en_to_es
	
	# let's get the loan details
	get_repayment_details(loantype)
	
	# let's clear the table
	loantype.repayment_schedule = []

	# set defaults for this variables
	capital_balance = loantype.loan_amount
	interest_balance = loantype.total_payable_interest
	## loantype.repayment_periods = ceil(loantype.repayment_periods)
	pagos_acumulados = interes_acumulado = 0.000
	capital_acumulado = 0.000

	
	payment_date = loantype.get("disbursement_date") if loantype.get("disbursement_date") \
		else loantype.get("posting_date")

	# map the values from the old variables
	loantype.total_payment = loantype.total_payable_amount
	loantype.total_interest_payable = loantype.total_payable_interest

	# fetch from the db the maximun pending amount for a loan
	maximum_pending_amount = frappe.db.get_single_value("FM Configuration", "maximum_pending_amount")

	# ok, now let's add the records to the table
	while(capital_balance > flt(maximum_pending_amount)):

		monthly_repayment_amount = loantype.monthly_repayment_amount

		# if(capital_balance + interest_balance < monthly_repayment_amount ):
		cuota =  round(loantype.monthly_capital) + loantype.monthly_interest
			
		capital_balance -= loantype.monthly_capital
		interest_balance -= loantype.monthly_interest
		pagos_acumulados += monthly_repayment_amount
		interes_acumulado += loantype.monthly_interest
		capital_acumulado += loantype.monthly_capital

		# start running the dates
		payment_date = frappe.utils.add_months(payment_date, 1)
		payment_date_obj = payment_date

		if isinstance(payment_date, basestring):
			payment_date_obj = datetime.strptime(payment_date, frappe.utils.DATE_FORMAT)

		payment_date_str = payment_date_obj.strftime(frappe.utils.DATE_FORMAT)

		if capital_balance < 0.000 or interest_balance < 0.000:
		 	capital_balance = interest_balance = 0.000

		 	if len(loantype.repayment_schedule) >= int(loantype.repayment_periods):
		 		loantype.repayment_periods += 1
		
		loantype.append("repayment_schedule", {
			"fecha": payment_date_str,
			"cuota": cuota,
			"monto_pendiente": cuota,
			"capital": round(loantype.monthly_capital),
			"interes": loantype.monthly_interest,
			"balance_capital": round(capital_balance),
			"balance_interes": round(interest_balance),
			"capital_acumulado": round(capital_acumulado),
			"interes_acumulado": round(interes_acumulado),
			"pagos_acumulados": pagos_acumulados,
			"fecha_mes": from_en_to_es("{0:%B}".format(payment_date_obj)),
			"estado": PENDING
		})

@frappe.whitelist()
def loan_disbursed_amount(loan):
	return frappe.db.sql("""SELECT IFNULL(SUM(debit_in_account_currency), 0) AS disbursed_amount 
		FROM `tabGL Entry` 
		WHERE against_voucher_type = 'Loan' 
		AND against_voucher = %s""", 
		(loan), as_dict=1)[0]

@frappe.whitelist()
def make_payment_entry(doctype, docname, paid_amount, capital_amount, interest_amount, fine=0.000, fine_discount=0.000, insurance=0.000):
	from erpnext.accounts.utils import get_account_currency
	from fm.api import get_voucher_type

	# load the loan from the database to make the requests more
	# efficients as the browser won't have to send everything back
	loan = frappe.get_doc(doctype, docname)

	curex = frappe.get_value("Currency Exchange", 
		{"from_currency": "USD", "to_currency": "DOP"}, "exchange_rate")

	exchange_rate = curex if loan.customer_currency == "USD" else 0.000

	# validate if the user has permissions to do this
	frappe.has_permission('Journal Entry', throw=True)

	def make(journal_entry, _paid_amount, _capital_amount=0.000, _interest_amount=0.000,  _insurance=0.000, _fine=0.000, _fine_discount=0.000):
		party_type = "Customer"

		voucher_type = get_voucher_type(loan.mode_of_payment)
		party_account_currency = get_account_currency(loan.customer_loan_account)
		today = frappe.utils.nowdate()

		interest_for_late_payment = frappe.db.get_single_value("FM Configuration", "interest_for_late_payment")
		account_of_suppliers = frappe.db.get_single_value("FM Configuration", "account_of_suppliers")
		interest_on_loans = frappe.db.get_single_value("FM Configuration", "interest_on_loans")

		filters = { 
			"loan": loan.name,
			"docstatus": "1",
			"start_date": ["<=", today],
			"end_date": [">=", today] 
		}
		
		insurance_supplier = frappe.get_value("Poliza de Seguro", filters, "insurance_company")

		if not insurance_supplier:
			# insurance supplier was not found in the Poliza de Seguro document. setting default
			insurance_supplier = frappe.db.get_single_value("FM Configuration", "default_insurance_supplier")

		# journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = voucher_type
		journal_entry.user_remark = _('Pagare de Prestamo: %(name)s' % { 'name': loan.name })
		journal_entry.company = loan.company
		journal_entry.posting_date = today

		journal_entry.es_un_pagare = 1
		journal_entry.loan = loan.name

		journal_entry.append("accounts", {
			"account": loan.payment_account,
			"debit_in_account_currency": _paid_amount,
			"reference_type": loan.doctype,
			"reference_name": loan.name,
			"exchange_rate": exchange_rate,
			"debit": flt(exchange_rate) * flt(_paid_amount)
		})

		if flt(_fine_discount):
			journal_entry.append("accounts", {
				"account": interest_for_late_payment,
				"debit_in_account_currency": _fine_discount,
				"exchange_rate": exchange_rate,
				"debit": flt(exchange_rate) * flt(_fine_discount)
			})

		if flt(_capital_amount):
			journal_entry.append("accounts", {
				"account": loan.customer_loan_account,
				"party_type": "Customer",
				"party": loan.customer,
				"credit_in_account_currency": _capital_amount,
				"exchange_rate": exchange_rate,
				"credit": flt(exchange_rate) * flt(_capital_amount)
			})	


		if flt(_interest_amount):
			journal_entry.append("accounts", {
				"account": loan.interest_income_account,
				"credit_in_account_currency": _interest_amount,
				"exchange_rate": exchange_rate,
				"credit": flt(exchange_rate) * flt(_interest_amount)
			})

		if flt(_insurance):
			journal_entry.append("accounts", {
				"account": loan.customer_loan_account,
				"party_type": "Customer",
				"party": loan.customer,
				"credit_in_account_currency": _insurance,
			})	

		if flt(_fine):
			journal_entry.append("accounts", {
				"account": fm.api.get_currency(loan, interest_on_loans),
				"credit_in_account_currency": _fine,
				"exchange_rate": exchange_rate,
				"credit": flt(exchange_rate) * flt(_fine)
			})

		journal_entry.multi_currency = 1.000 if loan.customer_currency == "USD" else 0.000

		journal_entry.submit()

		return journal_entry


	_paid_amount = flt(paid_amount)
 	rate = exchange_rate if loan.customer_currency == "USD" else 1.000
	while _paid_amount > 0.000:
		# to create the journal entry we will need some temp files
		# these tmp values will store the actual values for each row before they are changed
		tmp_fine = tmp_capital = tmp_interest = tmp_insurance = 0.000

		# to know how much exactly was paid for this repayment
		temp_paid_amount = _paid_amount


		# get the repayment from the loan
		row = loan.next_repayment()

		if not row:
			frappe.throw("""<h4>Parece que este prestamo no tiene mas pagares.</h4>
				<b>Si esta pagando multiples cuotas, es probable que el monto que este digitando
				sea mayor al monto total pendiente del prestamo!</b>""")

		# duty without the fine discount applied which is the original duty
		duty = flt(row.capital) + flt(row.interes) + flt(row.fine) + flt(row.insurance)

		# let's validate that the user is not applying discounts for multiple payments
		if flt(fine_discount) and paid_amount > duty:
			frappe.throw("No esta permitido hacer descuento de mora para pagos de multiples cuotas!")
		
		# duty with the fine discount applied
		# at this point we are sure that if there is any discount it is only applicable for one repayment
		duty = flt(row.capital) + flt(row.interes) + flt(row.fine) + flt(row.insurance) - flt(fine_discount)
		
		if _paid_amount >= row.fine: 
			tmp_fine = row.fine
			_paid_amount -= row.fine
			row.fine = 0.000
		else:
			tmp_fine = _paid_amount
			row.fine -= _paid_amount
	 		_paid_amount = 0.000

		if _paid_amount >= row.interes: 
			tmp_interest = row.interes
	 		_paid_amount -= row.interes
			row.interes = 0.000
		else:
			tmp_interest = _paid_amount
			row.interes -= _paid_amount
	 		_paid_amount = 0.000

		if _paid_amount >= row.capital: 
			tmp_capital = row.capital
	 		_paid_amount -= row.capital
			row.capital = 0.000
		else:
			tmp_capital = _paid_amount
			row.capital -= _paid_amount
	 		_paid_amount = 0.000

		if _paid_amount >= row.insurance:
			tmp_insurance = row.insurance
	 		_paid_amount -= row.insurance
			row.insurance = 0.000

			# Cambiar el estado de la cuota de la poliza de seguro a SALDADA 
	 		fm.api.update_insurance_status("SALDADO", row.insurance_doc)
		else:
			tmp_insurance = _paid_amount
			row.insurance -= _paid_amount
	 		_paid_amount = 0.000

			# Cambiar el estado de la cuota de la poliza de seguro a ABONO 
	 		fm.api.update_insurance_status("ABONO", row.insurance_doc)
		
		repayment_amount = tmp_fine + tmp_interest + tmp_capital + tmp_insurance - flt(fine_discount)
		
		if repayment_amount >= duty:

			row.monto_pendiente = 0.000
		else:
			row.monto_pendiente = flt(row.capital) + flt(row.interes) + flt(row.fine) + flt(row.insurance)

		row.update_status()

		payment_entry = frappe.new_doc("Journal Entry")

		payment_entry.pagare = row.name
		payment_entry.loan = loan.name

		payment_entry = make(journal_entry=payment_entry,
			_paid_amount=repayment_amount if temp_paid_amount > duty else temp_paid_amount,
			_capital_amount=tmp_capital, 
			_interest_amount=tmp_interest, 
			_insurance=tmp_insurance, 
			_fine=tmp_fine, 
			_fine_discount=fine_discount
		)

		row.db_update()
		loan.update_disbursement_status()

		loan.db_update()
