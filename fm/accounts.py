# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

from frappe import _

from datetime import datetime
from fm.api import *

from fm.finance_manager.doctype.loan.loan import update_loan_status
from fm.finance_manager.doctype.loan.loan import update_disbursement_status
from fm.finance_manager.doctype.loan.loan import get_monthly_repayment_amount

def update_loan(doc, event):
	if doc.loan:
		loan = frappe.get_doc("Loan", doc.loan)
		update_disbursement_status(loan)

def remove_loan(doc, event):
	if doc.loan:
		# fetch the from the DB first
		loan = frappe.get_doc("Loan", doc.loan)

		doc.loan = None # to remove the link

		# update the DB
		doc.db_update()
		
		# and finally update the Loan's status
		update_disbursement_status(loan)

def update_loan_table(doc, event):
	loan = frappe.get_doc("Loan", doc.loan)

	# brings the repayment that we are going to be working with
	row = loan.next_repayment()

	# ok, let's see if the repayment has been fully paid
	if doc.paid_amount < loan.monthly_repayment_amount:

		# update the status in the repayment table
		row.estado = "ABONO"

	elif doc.paid_amount > loan.monthly_repayment_amount:
		pass
		# if doc.paid_amount > total_amount:
		# 	row.estado = "SALDADA"
		# if row.fine:
		# 	total_amount = row.fine + monthly_repayment_amount
	elif doc.docstatus == 2:
		row.estado = "PENDIENTE"
	else:
		row.estado = "SALDADA"

	# see if the status can be updated
	update_loan_status(loan)

	row.db_update()

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
	loantype.rate = float(loantype.rate_of_interest) / 100.0

	# calculate the monthly interest
	loantype.monthly_interest = round(loantype.loan_amount * loantype.rate)

	# ok, now let's check the repayment method
	if loantype.repayment_method == "Repay Over Number of Periods":

		# total interest
		loantype.total_payable_interest = loantype.monthly_interest * loantype.repayment_periods

		# calculate the monthly capital
		loantype.monthly_capital = round(loantype.loan_amount / loantype.repayment_periods)

	elif loantype.repayment_method == "Repay Fixed Amount per Period":
		
		# calculate the monthly capital
		loantype.monthly_capital = float(loantype.monthly_repayment_amount) - loantype.monthly_interest

		if loantype.monthly_capital < 0:
			frappe.throw(_("Monthly repayment amount cannot be less than the monthly interest!"))

		# calculate the repayment periods based on the given monthly repayment amount
		loantype.repayment_periods = loantype.loan_amount / loantype.monthly_capital

		# total interest
		loantype.total_payable_interest = loantype.monthly_interest * loantype.repayment_periods

	# get the monthly repayment amount
	loantype.monthly_repayment_amount = loantype.monthly_interest + loantype.monthly_capital

	# calculate the total payment
	loantype.total_payable_amount = loantype.monthly_repayment_amount * loantype.repayment_periods

def get_compound_repayment_details(loantype):
	# if there's not rate set
	if not loantype.rate_of_interest: 
		# now let's fetch from the DB the default rate for interest compound
		loantype.rate_of_interest = frappe.db.get_single_value("FM Configuration", "composite_rate_of_interest")
	
	if loantype.repayment_method == "Repay Over Number of Periods":
		loantype.repayment_amount = get_monthly_repayment_amount(
			loantype.interest_type,
			loantype.repayment_method, 
			loantype.loan_amount, 
			loantype.rate_of_interest, 
			loantype.repayment_periods
		)

	if loantype.repayment_method == "Repay Fixed Amount per Period":

		# convert the rate to decimal
		monthly_interest_rate = float(loantype.rate_of_interest) / 100

		if monthly_interest_rate:
			loantype.repayment_periods = round(
				float(
					log(loantype.repayment_amount) 
					- log(loantype.repayment_amount 
						- float(
							loantype.loan_amount 
							* monthly_interest_rate
						)
					)
				) 
				/ float(
					log(
						monthly_interest_rate
						+ 1 
					)
				)
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
	pagos_acumulados = interes_acumulado = 0
	capital_acumulado = 0

	
	payment_date = loantype.get("disbursement_date") if loantype.get("disbursement_date") else loantype.get("posting_date")

	# map the values from the old variables
	loantype.total_payment = loantype.total_payable_amount
	loantype.total_interest_payable = loantype.total_payable_interest

	# fetch from the db the maximun pending amount for a loan
	maximum_pending_amount = frappe.db.get_single_value("FM Configuration", "maximum_pending_amount")

	# ok, now let's add the records to the table
	while(capital_balance > float(maximum_pending_amount)):

		monthly_repayment_amount = loantype.monthly_repayment_amount

		# if(capital_balance + interest_balance < monthly_repayment_amount ):
		cuota =  loantype.monthly_capital + loantype.monthly_interest
			
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

		if capital_balance < 0 or interest_balance < 0:
		 	capital_balance = interest_balance = 0

		 	if len(loantype.repayment_schedule) >= int(loantype.repayment_periods):
		 		loantype.repayment_periods += 1
		
		loantype.append("repayment_schedule", {
			"fecha": payment_date_str,
			"cuota": cuota,
			"capital": loantype.monthly_capital,
			"interes": loantype.monthly_interest,
			"balance_capital": capital_balance,
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
