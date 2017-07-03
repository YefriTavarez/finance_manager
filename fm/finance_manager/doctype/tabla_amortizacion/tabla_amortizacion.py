# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from fm.api import PENDING, FULLY_PAID, PARTIALLY_PAID, OVERDUE
from frappe.utils import flt

class TablaAmortizacion(Document):
	def update_status(self):
		customer_currency = frappe.get_value("Loan", 
			{ "name": self.parent }, "customer_currency")

		curex = frappe.get_doc("Currency Exchange", 
			{ "from_currency": "USD", "to_currency": "DOP" })

		exchange_rate = curex.exchange_rate

		if customer_currency == "DOP":
			exchange_rate = 1.000

		orignal_duty = flt(self.cuota) + flt(self.fine) + round(self.insurance / exchange_rate)
		current_duty = flt(self.capital) + flt(self.interes) + flt(self.fine) + round(self.insurance / exchange_rate)

		today = frappe.utils.nowdate()

		# ok, let's see if the repayment has been fully paid
		if orignal_duty == current_duty and str(self.fecha) < today:

			self.estado = OVERDUE
		elif orignal_duty == current_duty:

			self.estado = PENDING
		elif current_duty == 0.0:

			self.estado = FULLY_PAID
		elif current_duty < orignal_duty and current_duty > 0:

			self.estado = PARTIALLY_PAID
