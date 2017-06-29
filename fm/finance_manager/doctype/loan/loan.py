# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import nowdate, flt
from erpnext.controllers.accounts_controller import AccountsController
from datetime import datetime
from fm.api import FULLY_PAID, add_months

class Loan(AccountsController):
	def before_insert(self):
		existing_loan = frappe.get_value("Loan", {
			"loan_application": self.loan_application,
			"docstatus": ["!=", "2"]
		})

		if existing_loan:
			frappe.throw(
				_("There is already a Loan against the Loan Application: %s" % self.loan_application)
			)

	def after_insert(self):
		self.update_application_status()

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
		if self.loan_amount > flt(maximum_loan_limit):
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

		# let's calculate some values
		legal_expenses_amount = self.loan_amount - self.gross_loan_amount
		total_payable_interest = self.total_payment - self.loan_amount

		account_amt_list.append({
			"account": self.customer_loan_account,
			"party_type": "Customer",
			"party": self.customer,
			"debit_in_account_currency": self.total_payment,
			"reference_type": "Loan",
			"reference_name": self.name,
		})

		account_amt_list.append({
			"account": self.disbursement_account,
			"credit_in_account_currency": self.gross_loan_amount,
			# "reference_type": "Loan",
			# "reference_name": self.name,
		})

		account_amt_list.append({
			"account": self.expenses_account,
			"credit_in_account_currency": legal_expenses_amount,
			# "reference_type": "Loan",
			# "reference_name": self.name,
		})

		account_amt_list.append({
			"account": self.interest_income_account,
			"credit_in_account_currency": total_payable_interest,
			# "reference_type": "Loan",
			# "reference_name": self.name,
		})

		# let's put the totals too
		journal_entry.total_debit = self.total_payment
		journal_entry.total_credit = legal_expenses_amount \
			+ total_payable_interest \
			+ self.gross_loan_amount

		journal_entry.set("accounts", account_amt_list)
		return journal_entry.as_dict()

	def make_payment_entry(self):
		self.check_permission('write')
		return make_payment_entry(self.doctype, self.name, self.monthly_repayment_amount)

	def make_simple_repayment_schedule(self):
		from fm.accounts import make_simple_repayment_schedule
		make_simple_repayment_schedule(self)
		
	def make_repayment_schedule(self):
		self.repayment_schedule = []
		payment_date = self.disbursement_date
		balance_amount = self.loan_amount

		while(balance_amount > 0):
			interest_amount = balance_amount * flt(self.rate_of_interest) / (12*100)
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
			# ok, let's validate if the posting date is a string
			if isinstance(self.posting_date, unicode):
				# it is a string, so let's convert to a datetime object
				self.posting_date = datetime.strptime(self.posting_date, "%Y-%m-%d")

			self.posting_date_str = '{0}, {4} ({1:%d}) del mes de {2} del año {3} ({1:%Y})'.format(
				from_en_to_es("{0:%A}".format(self.posting_date)),
				self.posting_date,
				from_en_to_es("{0:%B}".format(self.posting_date)),
				frappe.utils.num2words(self.posting_date.year, lang='es').upper(),
				frappe.utils.num2words(self.posting_date.day, lang='es').upper()
			)

			self.end_date = add_months(self.posting_date, self.repayment_periods)

			self.end_date_str = '{0}, {4} ({1:%d}) del mes de {2} del año {3} ({1:%Y})'.format(
				from_en_to_es("{0:%A}".format(self.end_date)),
				self.end_date,
				from_en_to_es("{0:%B}".format(self.end_date)),
				frappe.utils.num2words(self.end_date.year, lang='es').upper(),
				frappe.utils.num2words(self.end_date.day, lang='es').upper()
			)

			self.posting_date = self.posting_date.strftime("%Y-%m-%d")

	def set_repayment_period(self):
		if self.repayment_method == "Repay Fixed Amount per Period":
			repayment_periods = len(self.repayment_schedule)

			self.repayment_periods = repayment_periods

	def next_repayment(self, by_insurance=False, with_date=None):
		if by_insurance and not with_date:
			frappe.throw("<i>With Date</i> argument is mandatory if <i>By Insurance</i> is provided")

		for repayment in self.repayment_schedule:
			if (by_insurance and not repayment.insurance and str(repayment.fecha) >= with_date) \
				or (not by_insurance and repayment.monto_pendiente):

				# the first found in the table
				return repayment


	# to update the loan application status
	def update_application_status(self):
		appl = frappe.get_doc("Loan Application", self.loan_application)

		if not self.docstatus == 2:
			# if loan is in draft or submitted, change the status of the appl
			appl.status = "Linked"
			appl.parent = "Linked"

		else:
			# if loan is cancelled then change the status application
			appl.status = "Approved"
			appl.parent = None

			# also, unlink the loan application
			self.loan_application = None

		# finally update the database
		appl.db_update()

	def on_cancel(self):
		self.update_application_status()
		
	def on_trash(self):
		if self.loan_application:
			appl = frappe.get_doc("Loan Application", self.loan_application)
			appl.status = "Approved"
			
			# finally update the database
			appl.db_update()

	def update_disbursement_status(self, exc=None):
		disbursement = get_disbursed_amount(self.name)

		if disbursement.disbursed_amount == self.total_payment:
			self.status = "Fully Disbursed"
			
		if disbursement.disbursed_amount == 0:
			self.status = "Sanctioned"

		if disbursement.disbursed_amount < self.total_payment and disbursement.disbursed_amount != 0:
			self.status = "Partially Disbursed"

		disbursement = get_disbursed_amount(self.name, 1, exc)

		if disbursement.disbursed_amount == self.total_payment:
			self.status = "Repaid/Closed"
			


	def update_loan_status(self):
		pass
		# index = 0
		# for repayment in self.repayment_schedule:
		# 	index += 1

		# 	if repayment.monto_pendiente:
		# 		self.update_disbursement_status()
		# 		break
				
		# if index == len(self.repayment_schedule):
		# 	self.status = "Repaid/Closed"

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
			monthly_interest_rate = flt(rate_of_interest) / 100.0
			return round((loan_amount * monthly_interest_rate *
				(1 + monthly_interest_rate)**repayment_periods) \
				/ ((1 + monthly_interest_rate)**repayment_periods - 1))
	elif rate_of_interest == "Simple":
		return round(flt(loan_amount) / repayment_periods)

def get_disbursed_amount(loan, pagare=0, exc=None):
	return frappe.db.sql("""SELECT journal.posting_date, IFNULL(SUM(general.credit_in_account_currency), 0) AS  disbursed_amount
		FROM `tabGL Entry` AS general 
		JOIN `tabJournal Entry` AS journal 
		ON journal.name = general.voucher_no 
		WHERE journal.loan = '{0}'
		AND journal.es_un_pagare = '{1}' {2}""".format(loan, pagare, 
			(" AND journal.name <> '%s'" % exc) if exc else " "),
		as_dict=True)[0] 

@frappe.whitelist()
def get_loan_application(loan_application):
	return frappe.get_doc("Loan Application", loan_application)

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
	customer_currency = frappe.db.get_value("Customer", loan.customer, "default_currency")
	
	# amounts
	grand_total = loan.monthly_repayment_amount

	outstanding_amount = grand_total - paid_amount
	row = loan.next_repayment()

	payment = frappe.new_doc("Payment Entry")
	payment.payment_type = "Receive"
	payment.company = loan.company
	payment.loan = loan.name
	payment.insurance = loan.vehicle_insurance
	payment.posting_date = nowdate()
	payment.mode_of_payment = loan.mode_of_payment
	payment.party_type = party_type
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

	# payment.es_un_pagare = 1

	if not customer_currency == frappe.defaults.get_global_default("currency"):
		payment.multi_currency = 1

	# cuotas
	payment.append("references", {
		"reference_doctype": doctype,
		"reference_name": docname,
		"due_date": row.fecha,
		"total_amount": grand_total,
		"outstanding_amount": outstanding_amount,
		"allocated_amount": outstanding_amount
	})
	
	return payment
