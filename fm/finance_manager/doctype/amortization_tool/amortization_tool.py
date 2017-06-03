# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import fm.accounts

class AmortizationTool(Document):
	def calculate_everything(self):
		from fm.accounts import make_simple_repayment_schedule

		make_simple_repayment_schedule(self)
		
		# self.doctype = "Loan"
		# loan = frappe.get_doc(self.as_dict())

		# loan.make_simple_repayment_schedule()

		# self.doctype = "Amortization Tool"
		# loan.doctype = "Amortization Tool"
		return self

