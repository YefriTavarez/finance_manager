# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from  fm.finance_manager.doctype.loan.loan import get_monthly_repayment_amount, check_repayment_method
   
from math import log

class LoanApplication(Document):
	def validate(self):
		# let's validate that the user has filled up the required fields
		check_repayment_method(
			self.repayment_method, 
			self.loan_amount, 
			self.monthly_repayment_amount, 
			self.repayment_periods
		)

		self.validate_loan_amount()
		self.get_repayment_details()

	def validate_loan_amount(self):
		# now let's fetch from the DB the maximum loan amount limit depending on the Loan Type
		maximum_loan_limit = frappe.db.get_single_value("FM Configuration", 'max_loan_amount_vehic' 
			if self.loan_type == "Vehicle" else 'max_loan_amount_vivienda')

		# throw an error if the loan amount is greater than what it should be
		if self.loan_amount > float(maximum_loan_limit):
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

			
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

@frappe.whitelist()
def make_loan(source_name, target_doc = None):
	doc = get_mapped_doc("Loan Application", source_name, {
		"Loan Application": {
			"doctype": "Loan",
			"validation": {
				"docstatus": ["=", 1],
				"status": ["=","Approved"],
			}
		}
	}, target_doc)

	doc.status = "Sanctioned" # status = [Approved] is not valid in Loan DocType 
	return doc
	