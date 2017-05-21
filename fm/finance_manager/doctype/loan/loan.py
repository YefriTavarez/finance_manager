# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import add_months, nowdate
from erpnext.controllers.accounts_controller import AccountsController

from math import ceil

PENDING = "PENDIENTE"
FULLY_PAID = "SALDADA"

class Loan(AccountsController):
	def before_insert(self):
		existing_loan = frappe.get_value("Loan", {
			"loan_application": self.loan_application
		})

		if existing_loan:
			frappe.throw(
				_("There is already a Loan against the Loan Application: {}"
					.format(
						self.loan_application
					)
				)
			)

	def validate(self):

		# let's validate that the user has filled up the required fields
		check_repayment_method(
			self.repayment_method, 
			self.loan_amount, 
			self.monthly_repayment_amount, 
			self.repayment_periods
		)

		# set missing values for hidden fields
		self.set_missing_values()

		# now let's fetch from the DB the maximum loan amount limit depending on the Loan Type
		maximum_loan_limit = frappe.db.get_single_value("FM Configuration", 'max_loan_amount_vehic' 
			if self.loan_type == "Vehicle" else 'max_loan_amount_vivienda')

		# throw an error if the loan amount is greater than what it should be
		if self.loan_amount > float(maximum_loan_limit):
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

		if not self.company:
			self.company = erpnext.get_default_company()

		if not self.posting_date:
			self.posting_date = nowdate()

		self.validate_loan_amount()

	def validate_loan_amount(self):

		if self.interest_type == "Simple":
			if not self.rate_of_interest: 	
				self.rate_of_interest = frappe.db.get_single_value("FM Configuration", "simple_rate_of_interest")

			self.make_simple_repayment_schedule()

		elif self.interest_type == "Composite":
			if not self.rate_of_interest:
				self.rate_of_interest = frappe.db.get_single_value("FM Configuration", "composite_rate_of_interest")

			self.set_repayment_period()
			self.make_repayment_schedule()

	def make_jv_entry(self):
		self.check_permission('write')
		journal_entry = frappe.new_doc('Journal Entry')
		
		journal_entry.voucher_type = 'Bank Entry'
		journal_entry.user_remark = _('Desembolso de Prestamo: {0}').format(self.name)
		journal_entry.company = self.company
		journal_entry.loan = self.name
		journal_entry.posting_date = nowdate()
		journal_entry.cheque_date = nowdate()

		account_amt_list = []

		account_amt_list.append({
			"account": self.customer_loan_account,
			"party_type": "Customer",
			"party": self.customer,
			"debit_in_account_currency": self.total_payment,
			"reference_type": "Loan",
			"reference_name": self.name,
			})
		account_amt_list.append({
			"account": self.payment_account,
			"credit_in_account_currency": self.total_payment,
			"reference_type": "Loan",
			"reference_name": self.name,
			})
		journal_entry.set("accounts", account_amt_list)
		return journal_entry.as_dict()

	def make_payment_entry(self):
		self.check_permission('write')
		return make_payment_entry(self.doctype, self.name, self.monthly_repayment_amount)

	def make_simple_repayment_schedule(self):
		from fm.accounts import get_repayment_details
		
		# let's get the loan details
		get_repayment_details(self)
		
		# let's clear the table
		self.repayment_schedule = []

		# set defaults for this variables
		capital_balance = self.loan_amount
		interest_balance = self.total_payable_interest
		## self.repayment_periods = ceil(self.repayment_periods)
		pagos_acumulados = interes_acumulado = 0
		capital_acumulado = 0

		# map the values from the old variables
		self.total_payment = self.total_payable_amount
		self.total_interest_payable = self.total_payable_interest

		# fetch from the db the maximun pending amount for a loan
		maximum_pending_amount = frappe.db.get_single_value("FM Configuration", "maximum_pending_amount")

		# ok, now let's add the records to the table
		while(capital_balance > float(maximum_pending_amount)):

			monthly_repayment_amount = self.monthly_repayment_amount

			# if(capital_balance + interest_balance < monthly_repayment_amount ):
			cuota =  capital_balance + interest_balance
				
			capital_balance -= self.monthly_capital
			interest_balance -= self.monthly_interest
			pagos_acumulados += monthly_repayment_amount
			interes_acumulado += self.monthly_interest
			capital_acumulado += self.monthly_capital

			# start running the dates
			payment_date = add_months(self.disbursement_date, 1)

			if capital_balance < 0 or interest_balance < 0:
			 	capital_balance = interest_balance = 0

			 	if len(self.repayment_schedule) >= int(self.repayment_periods):
			 		self.repayment_periods += 1
			
			self.append("repayment_schedule", {
				"fecha": payment_date,
				"cuota": cuota,
				"capital": self.monthly_capital,
				"interes": self.monthly_interest,
				"balance_capital": capital_balance,
				"balance_interes": round(interest_balance),
				"capital_acumulado": round(capital_acumulado),
				"interes_acumulado": round(interes_acumulado),
				"pagos_acumulados": pagos_acumulados,
				"estado": PENDING
			})
		
		
	def make_repayment_schedule(self):
		self.repayment_schedule = []
		payment_date = self.disbursement_date
		balance_amount = self.loan_amount

		while(balance_amount > 0):
			interest_amount = balance_amount * float(self.rate_of_interest) / (12*100)
			principal_amount = self.monthly_repayment_amount - interest_amount
			balance_amount = balance_amount + interest_amount - self.monthly_repayment_amount

			if balance_amount < 0:
				principal_amount += balance_amount
				balance_amount = 0.0

			total_payment = principal_amount + interest_amount

			self.append("repayment_schedule", {
				"payment_date": payment_date,
				"principal_amount": principal_amount,
				"interest_amount": round(interest_amount),
				"total_payment": total_payment,
				"balance_loan_amount": round(balance_amount)
			})

			next_payment_date = add_months(payment_date, 1)
			payment_date = next_payment_date

	def set_missing_values(self):
		from fm.api import from_en_to_es

		if not self.customer_cedula:
			self.customer_cedula = frappe.db.get_value("Customer", self.customer, "cedula")

		if not self.posting_date_str:
			self.posting_date_str = '{0}, {4} ({1:%d}) del mes de {2} del año {3} ({1:%Y})'.format(
				from_en_to_es("{0:%A}".format(self.posting_date)),
				self.posting_date,
				from_en_to_es("{0:%B}".format(self.posting_date)),
				frappe.utils.num2words(self.posting_date.year, lang='es').upper(),
				frappe.utils.num2words(self.posting_date.day, lang='es').upper()
			)

			# print "{}".format(self.posting_date_str)
			self.end_date = frappe.utils.add_months(self.posting_date, self.repayment_periods)

			self.end_date_str = '{0}, {4} ({1:%d}) del mes de {2} del año {3} ({1:%Y})'.format(
				from_en_to_es("{0:%A}".format(self.end_date)),
				self.end_date,
				from_en_to_es("{0:%B}".format(self.end_date)),
				frappe.utils.num2words(self.end_date.year, lang='es').upper(),
				frappe.utils.num2words(self.end_date.day, lang='es').upper()
			)

			# print "{}".format(self.end_date_str)

	def set_repayment_period(self):
		if self.repayment_method == "Repay Fixed Amount per Period":
			repayment_periods = len(self.repayment_schedule)

			self.repayment_periods = repayment_periods

	def next_repayment(self):
		for repayment in self.repayment_schedule:
			if not repayment.estado == FULLY_PAID:
				return repayment # the first found in the table


def update_disbursement_status(doc):
	disbursement = frappe.db.sql("""SELECT posting_date, IFNULL(SUM(debit_in_account_currency), 0) AS disbursed_amount
		FROM `tabGL Entry` WHERE against_voucher_type = 'Loan' AND against_voucher = %s""",
		(doc.name), as_dict=1)[0]
	if disbursement.disbursed_amount == doc.total_payment:
		frappe.db.set_value("Loan", doc.name , "status", "Fully Disbursed")
	if disbursement.disbursed_amount < doc.total_payment and disbursement.disbursed_amount != 0:
		frappe.db.set_value("Loan", doc.name , "status", "Partially Disbursed")
	if disbursement.disbursed_amount == 0:
		frappe.db.set_value("Loan", doc.name , "status", "Sanctioned")
	if disbursement.disbursed_amount > doc.total_payment:
		frappe.throw(_("Disbursed Amount cannot be greater than Loan Amount {0}").format(doc.total_payment))
	if disbursement.disbursed_amount > 0:
		frappe.db.set_value("Loan", doc.name , "disbursement_date", disbursement.posting_date)

def update_loan_status(loan):
	# fecth from the DB and sum all the credits against this customer
	result_set = frappe.db.sql("""SELECT IFNULL(SUM(gl.credit_in_account_currency),0) AS paid
		FROM `tabGL Entry` AS gl
		JOIN `tabPayment Entry` AS pmt
		ON gl.voucher_no = pmt.name
		WHERE gl.party_type = "Customer"
		AND gl.party = "%(customer)s"
		AND pmt.loan = "%(loan)s" """
		% { "customer": loan.customer, "loan": loan.name }, as_dict=True)

	first_row = result_set.pop()

	loan.paid_by_now = first_row.paid

	if loan.paid_by_now >= loan.total_payment:
		loan.status = "Repaid/Closed"

	loan.db_update()

def check_repayment_method(repayment_method, loan_amount, monthly_repayment_amount, repayment_periods):
	if repayment_method == "Repay Over Number of Periods" and not repayment_periods:
		frappe.throw(_("Please enter Repayment Periods"))
		
	if repayment_method == "Repay Fixed Amount per Period":
		if not monthly_repayment_amount:
			frappe.throw(_("Please enter repayment Amount"))

		if monthly_repayment_amount > loan_amount:
			frappe.throw(_("Monthly Repayment Amount cannot be greater than Loan Amount"))

def get_monthly_repayment_amount(interest_type, repayment_method, loan_amount, rate_of_interest, repayment_periods):
	if interest_type == "Composite": 	
		if rate_of_interest:
			monthly_interest_rate = float(rate_of_interest) / 100.0
			return round((loan_amount * monthly_interest_rate *
				(1 + monthly_interest_rate)**repayment_periods) \
				/ ((1 + monthly_interest_rate)**repayment_periods - 1))
	elif rate_of_interest == "Simple":
		return round(float(loan_amount) / repayment_periods)

@frappe.whitelist()
def get_loan_application(loan_application):
	loan = frappe.get_doc("Loan Application", loan_application)
	if loan:
		return loan

@frappe.whitelist()
def make_jv_entry(customer_loan, company, customer_loan_account, customer, loan_amount, payment_account):
	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = 'Bank Entry'
	journal_entry.user_remark = _('Desembolso de Prestamo: {0}').format(customer_loan)
	journal_entry.company = company
	journal_entry.posting_date = nowdate()

	account_amt_list = []

	account_amt_list.append({
		"account": customer_loan_account,
		"debit_in_account_currency": loan_amount,
		"reference_type": "Loan",
		"reference_name": customer_loan,
		})
	account_amt_list.append({
		"account": payment_account,
		"credit_in_account_currency": loan_amount,
		"reference_type": "Loan",
		"reference_name": customer_loan,
		})
	journal_entry.set("accounts", account_amt_list)
	return journal_entry.as_dict()

@frappe.whitelist()
def make_payment_entry(doctype, docname, paid_amount):
	from erpnext.accounts.utils import get_account_currency
	frappe.has_permission('Payment Entry', throw=True)

	loan = frappe.get_doc(doctype, docname)

	party_type = "Customer"

	
	party_account_currency = get_account_currency(loan.customer_loan_account)
	
	# amounts
	grand_total = loan.monthly_repayment_amount

	outstanding_amount = grand_total - paid_amount
	row = loan.next_repayment()

	payment = frappe.new_doc("Payment Entry")
	payment.payment_type = "Receive"
	payment.company = loan.company
	payment.loan = loan.name
	payment.posting_date = nowdate()
	payment.mode_of_payment = loan.mode_of_payment
	payment.party_type = "Customer"
	payment.party = loan.customer
	payment.paid_from = loan.customer_loan_account
	payment.paid_to = loan.payment_account
	payment.paid_from_account_currency = party_account_currency
	payment.paid_to_account_currency = party_account_currency
	payment.paid_amount = paid_amount + row.fine
	payment.mora = row.fine
	payment.pagare = row.idx
	payment.received_amount = paid_amount
	payment.allocate_payment_amount = 1
	
	payment.append("references", {
		"reference_doctype": doctype,
		"reference_name": docname,
		"due_date": row.fecha,
		"total_amount": grand_total,
		"outstanding_amount": outstanding_amount,
		"allocated_amount": outstanding_amount
	})

	payment.setup_party_account_field()
	payment.set_missing_values()

	return payment
