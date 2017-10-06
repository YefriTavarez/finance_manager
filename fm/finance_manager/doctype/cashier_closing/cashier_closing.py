# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

from fm.api import get_paid_amount2

class CashierClosing(Document):
	def onload(self):
		self.entries = []

		journal_list = frappe.get_list("Journal Entry", {
			"is_cashier_closing": "1"
		}, "*", limit_page_length=10, order_by="creation DESC")

		for journal_entry in journal_list:
			self.append("entries", {
				"date": journal_entry.posting_date,
				"user": journal_entry.owner,
				"type": journal_entry.remark.split(':')[1].strip(),
				"amount": get_paid_amount2(self.bank_account, journal_entry.name),
				"amount_usd": get_paid_amount2(self.bank_account_usd, journal_entry.name),
				"reference": journal_entry.name
			})

	def validate(self):
		self.entries = []