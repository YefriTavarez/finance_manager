# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from  fm.finance_manager.doctype.loan.loan import get_monthly_repayment_amount, check_repayment_method
   
class LoanApplication(Document):
	def validate(self):
		# let's validate that the user has filled up the required fields
		check_repayment_method(
			self.repayment_method, 
			self.loan_amount, 
			self.monthly_repayment_amount, 
			self.repayment_periods
		)

		self.validate_customer_references()
		self.validate_loan_amount()
		self.get_repayment_details()

	def validate_loan_amount(self):
		# now let's fetch from the DB the maximum loan amount limit depending on the Loan Type
		maximum_loan_limit = frappe.db.get_single_value("FM Configuration", "max_loan_amount_vehic" 
			if self.loan_type == "Vehicle" else "max_loan_amount_vivienda")

		# throw an error if the loan amount is greater than what it should be
		if self.loan_amount > float(maximum_loan_limit):
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

		# just for safety, let us put the status in the parent field to know what was the previous status
		self.parent = self.status


	def on_update_after_submit(self):
		# 
		previous_status = get_previous_status(self.name)

		# validate that the user has not linked the appl manually
		if (self.status == "Linked" or previous_status == "Linked") and not self.status == previous_status:
			frappe.throw(
				_("""<b>You should not link this Loan Application manually as you need a Loan Document against it.</b>
					<br><br>If you're trying modify the Loan Application after a Loan has been Linked with it,
					<br>then you should cancel the Loan against it and then proceed."""), title=_("Warning!")
			)

		# just for safety, let's puth the status in the parent field to know what was the previous status
		self.parent = self.status
		self.db_update()
			
	def get_repayment_details(self):
		from fm.accounts import get_repayment_details
		
		# get the details of the loan
		get_repayment_details(self)

	def calculate_payable_amount(self):
		balance_amount = self.loan_amount
		self.total_payable_amount = 0
		self.total_payable_interest = 0

		while(balance_amount > 0):
			interest_amount = round(balance_amount * float(self.rate_of_interest) / 100)
			balance_amount = round(balance_amount + interest_amount - self.repayment_amount)

			self.total_payable_interest += interest_amount
			
		self.total_payable_amount = self.loan_amount + self.total_payable_interest

	def validate_customer_references(self):
		references = frappe.get_list("Referencia", { "parent": self.customer }, ["first_name"])

		if not references or len(references) < 2:
			frappe.throw(_("You need at least two references for this customer!"))
			

@frappe.whitelist()
def make_loan(source_name, target_doc = None):
	doc = get_mapped_doc("Loan Application", source_name, {
		"Loan Application": {
			"doctype": "Loan",
			"validation": {
				"docstatus": ["=", 1],
				"status": ["=","Approved"],
			},
			"field_map": {
				"total_payment": "15600"
			}
		}
	}, target_doc)

	doc.status = "Sanctioned" # status = [Approved] is not valid in Loan DocType

	# set account defaults for Loan
	if doc.customer_currency == "DOP":
		doc.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
		doc.payment_account = frappe.db.get_single_value("FM Configuration", "payment_account")
		doc.customer_loan_account = frappe.db.get_single_value("FM Configuration", "customer_loan_account")
		doc.disbursement_account = frappe.db.get_single_value("FM Configuration", "disbursement_account")
		doc.interest_income_account = frappe.db.get_single_value("FM Configuration", "interest_income_account")
		doc.expenses_account = frappe.db.get_single_value("FM Configuration", "expenses_account")
	else:
		doc.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment").replace("DOP", "USD")
		doc.payment_account = frappe.db.get_single_value("FM Configuration", "payment_account").replace("DOP", "USD")
		doc.customer_loan_account = frappe.db.get_single_value("FM Configuration", "customer_loan_account").replace("DOP", "USD")
		doc.disbursement_account = frappe.db.get_single_value("FM Configuration", "disbursement_account").replace("DOP", "USD")
		doc.interest_income_account = frappe.db.get_single_value("FM Configuration", "interest_income_account").replace("DOP", "USD")
		doc.expenses_account = frappe.db.get_single_value("FM Configuration", "expenses_account").replace("DOP", "USD")
	
    
	# doc.validate()
	return doc

def get_previous_status(loan):
	return frappe.db.get_value("Loan Application", loan, "parent")
