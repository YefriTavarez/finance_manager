# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import fm.accounts

class AmortizationTool(Document):
	def calculate_everything(self):
		from fm.accounts import make_simple_repayment_schedule

		make_simple_repayment_schedule(self)

		return self

