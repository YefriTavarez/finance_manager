# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

from  fm.finance_manager.doctype.loan.loan import get_monthly_repayment_amount, check_repayment_method
   
class LoanApplication(Document):
	def validate(self):
		frappe.errprint("On Validate")
		self.validate_loan_amount()
		frappe.errprint("On validate_loan_amount")
		self.get_repayment_details()
		frappe.errprint("On get_repayment_details")
		check_repayment_method(self.repayment_method, self.loan_amount, self.monthly_repayment_amount, self.repayment_periods)
		frappe.errprint("On check_repayment_method")

	def validate_loan_amount(self):
		maximum_loan_limit = frappe.db.get_value('Loan Type', self.loan_type, 'maximum_loan_amount')
		if maximum_loan_limit and self.loan_amount > maximum_loan_limit:
			frappe.throw(_("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit))

	def get_repayment_details(self):
		rate_interest=flt(self.rate_of_interest)/12/100
		if self.interest_type=="Simple":
			if self.repayment_method == "Repay Over Number of Periods":
				self.monthly_repayment_amount=round(((self.loan_amount * rate_interest * self.repayment_periods)+self.loan_amount)/self.repayment_periods)
		
			if self.repayment_method == "Repay Fixed Amount per Period":
				if((self.monthly_repayment_amount-(self.loan_amount * rate_interest))<0): 
					frappe.throw(_("Loan Amount is not Enough to cover the interest {0}").format(self.loan_amount * self.rate_of_interest))
				self.repayment_periods=math.ceil(self.loan_amount/(self.monthly_repayment_amount-(self.loan_amount * rate_interest)))	
				
		else:
			if self.repayment_method == "Repay Over Number of Periods":
				self.monthly_repayment_amount = get_monthly_repayment_amount(self.repayment_method, self.loan_amount, self.rate_of_interest, self.repayment_periods)

			if self.repayment_method == "Repay Fixed Amount per Period":
				monthly_interest_rate = flt(self.rate_of_interest) / (12 *100)
				self.repayment_periods = math.ceil((math.log(self.monthly_repayment_amount) - math.log(self.monthly_repayment_amount - \
				(self.loan_amount*monthly_interest_rate)))/(math.log(1+monthly_interest_rate)))

		self.total_payable_amount = self.monthly_repayment_amount * self.repayment_periods
		self.total_payable_interest = self.total_payable_amount - self.loan_amount

@frappe.whitelist()
def make_loan(source_name, target_doc = None):
	doclist = get_mapped_doc("Loan Application", source_name, {
		"Loan Application": {
			"doctype": "Loan",
			"validation": {
				"docstatus": ["=", 1]
			}
		}
	}, target_doc)

	return doclist