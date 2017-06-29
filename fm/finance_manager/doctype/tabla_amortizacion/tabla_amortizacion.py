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

		duty = flt(self.cuota) + flt(self.fine) + flt(self.insurance)
		today = frappe.utils.nowdate()

		# ok, let's see if the repayment has been fully paid
		if self.monto_pendiente == duty and str(self.fecha) < today:

			self.estado = OVERDUE
		elif self.monto_pendiente == duty:

			self.estado = PENDING
		elif self.monto_pendiente == 0.0:

			self.estado = FULLY_PAID
		elif self.monto_pendiente < duty and self.monto_pendiente > 0:

			self.estado = PARTIALLY_PAID
