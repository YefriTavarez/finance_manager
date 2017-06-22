# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe.model.document import Document

class PolizadeSeguro(Document):
	def make_purchase_invoice(self):
		company = frappe.get_doc("Company", erpnext.get_default_company())

		item = frappe.get_doc("Item", { "tipo_de_seguro": self.tipo_seguro, "default_supplier": self.insurance_company })

		item_price = frappe.get_doc("Item Price", { "item_code": item.item_code, "buying": "1" })
		item_price.price_list_rate = self.amount
		item_price.db_update()

		price_list_rate = self.amount

		purchase = frappe.new_doc("Purchase Invoice")

		purchase.supplier = self.insurance_company
		purchase.is_paid = 1
		purchase.company = company.name
		purchase.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
		purchase.cash_bank_account = company.default_bank_account
		purchase.paid_amount = self.amount

		purchase.append("items", {
			"item_code": item.item_code,
			"is_fixed_item": 1,
			"item_name": item.item_name,
			"qty": 1,
			"price_list_rate": price_list_rate,
			"rate": price_list_rate
		})

		purchase.set_missing_values()

		return purchase




	

