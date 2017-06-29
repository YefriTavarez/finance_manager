# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe.model.document import Document
from frappe.utils import flt

class PolizadeSeguro(Document):
	def make_purchase_invoice(self):

		# validate if exists a purchase invoice against the current document
		purchase_name = frappe.get_value("Purchase Invoice", 
			{ "poliza_de_seguro": self.name, "docstatus": ["!=", "2"] }, "*")

		if purchase_name:
			return purchase_name

		# ok, let's continue as there is not an existing PI

		item = frappe.new_doc("Item")
		company = frappe.get_doc("Company", erpnext.get_default_company())

		try:
			# let's see if it exists
			item = frappe.get_doc("Item", { "item_group": "Insurances" })
		except:
			# ok, let's create it
			item.item_group = "Insurances"
			item.item_code = "Vehicle Insurance"
			item.item_name = item.item_code
			item.insert()

		purchase = frappe.new_doc("Purchase Invoice")

		purchase.supplier = self.insurance_company
		purchase.is_paid = 1
		purchase.company = company.name
		purchase.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
		purchase.cash_bank_account = company.default_bank_account
		purchase.paid_amount = self.amount

		# ensure this doc is linked to the new purchase
		purchase.poliza_de_seguro = self.name

		purchase.append("items", {
			"item_code": item.item_code,
			"is_fixed_item": 1,
			"item_name": item.item_name,
			"qty": 1,
			"price_list_rate": self.amount,
			"rate": self.amount
		})

		purchase.save()

		return purchase.as_dict()

	def before_submit(self):
		if not self.get("financiamiento"):
			return 0 # if the insurance was not financed

		loan = frappe.get_doc("Loan", self.loan)

		for insurance in self.cuotas:

			paid_amount = 0

			pagare = loan.next_repayment(by_insurance=True, with_date=self.start_date)

			# let's see how much the customer has paid so far for this pagare
			for journal in frappe.get_list("Journal Entry", { "pagare": pagare.name }, "total_amount"):
				paid_amount += journal.total_amount

			pagare.insurance = insurance.amount

			# duty will be what the customer has to pay for this pagare
			duty = flt(pagare.cuota) + flt(pagare.fine) + flt(pagare.insurance)

			pagare.monto_pendiente = duty - paid_amount
		
			# ensures this pagare knows about this child
			pagare.insurance_doc = insurance.name
			
			pagare.db_update()

	def on_cancel(self):
		if not self.get("financiamiento"):
			return 0

		for insurance in self.cuotas:
			try:
				paid_amount = 0

				pagare = frappe.get_doc("Tabla Amortizacion", 
					{ "insurance_doc": insurance.name })

				# let's see how much the customer has paid so far for this repayment
				for journal in frappe.get_list("Journal Entry", { "pagare": pagare.name }, "total_amount"):
					paid_amount += journal.total_amount

				pagare.insurance = 0

				# duty will be what the customer has to pay for this pagare
				duty = flt(pagare.cuota) + flt(pagare.fine) + flt(pagare.insurance)

				pagare.monto_pendiente = duty - paid_amount

				pagare.insurance_doc = None

				pagare.db_update()
			except:
				pass

		self.delete_purchase_invoice()

	def delete_purchase_invoice(self):
		try:
			purchase = frappe.get_doc("Purchase Invoice", {
				"poliza_de_seguro": self.name
			})

			if purchase.docstatus == 1:
				purchase.cancel()

			purchase.delete()
		except:
			pass
