# -*- coding: utf-8 -*-
# Copyright (c) 2015, Soldeva, SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.model.document import Document

from frappe.utils import flt
from fm.api import FULLY_PAID

class PolizadeSeguro(Document):
	def before_submit(self):
		"""Automate the Purchase Invoice creation against a Poliza de Seguro"""

		# validate if exists a purchase invoice against the current document
		purchase_name = frappe.get_value("Purchase Invoice", { 
			"poliza_de_seguro": self.name, "docstatus": ["!=", "2"]
		}, "*")

		if purchase_name:
			return purchase_name

		# ok, let's continue as there is not an existing PINV

		item = frappe.new_doc("Item")
		company = frappe.get_doc("Company", erpnext.get_default_company())

		item_was_found = not not frappe.get_value("Item", { "item_group": "Insurances" })

		# let's see if it exists
		if item_was_found:

			item = frappe.get_doc("Item", { "item_group": "Insurances" })
		else:
			# ok, let's create it
			item.item_group = "Insurances"
			item.item_code = "Vehicle Insurance"
			item.item_name = item.item_code

			item.insert()

		pinv = frappe.new_doc("Purchase Invoice")

		pinv.supplier = self.insurance_company
		pinv.is_paid = 1.000
		pinv.company = company.name
		pinv.mode_of_payment = frappe.db.get_single_value("FM Configuration", "mode_of_payment")
		pinv.cash_bank_account = company.default_bank_account
		pinv.paid_amount = self.amount
		pinv.base_paid_amount = self.amount

		# ensure this doc is linked to the new purchase
		pinv.poliza_de_seguro = self.name

		pinv.append("items", {
			"item_code": item.item_code,
			"is_fixed_item": 1,
			"item_name": item.item_name,
			"qty": 1,
			"price_list_rate": self.amount,
			"rate": self.amount
		})

		pinv.submit()

		return pinv.as_dict()

	def on_submit(self):
		"""Run after submission"""

		# let's check if this insurance was term financed
		if not self.get("financiamiento"):
			return 0 # let's just ignore and do nothing else

		loan = frappe.get_doc("Loan", self.loan)

		# iterate every insurance repayment to map it and add its amount
		# to the insurance field in the repayment table
		for index, insurance in enumerate(self.cuotas):
			if not index: 
				create_first_payment(insurance)

				# skip the first one
				continue

			# get the first repayment that has not insurance and its payment date
			# is very first one after the start date of the insurance coverage
			loan_row = loan.next_repayment(by_insurance=True, with_date=self.start_date)

			if loan_row.estado == FULLY_PAID:
				frappe.throw("El pagare No. {0} ya se ha saldado, por lo que no sera posible \
					cobrarle a cliente en este pagare!".format(loan_row.idx))

			loan_row.insurance = insurance.amount

			curex = frappe.get_doc("Currency Exchange", 
				{"from_currency": "USD", "to_currency": "DOP"})

			exchange_rate = curex.exchange_rate

			if loan.customer_currency == "DOP":
				exchange_rate = 1.000

			# pending_amount will be what the customer has to pay for this repayment
			pending_amount = flt(loan_row.capital) + flt(loan_row.interes) + flt(loan_row.fine) \
				+ round(loan_row.insurance / exchange_rate)

			loan_row.monto_pendiente = pending_amount
		
			# ensures this repayment knows about this child
			loan_row.insurance_doc = insurance.name
			
			loan_row.db_update()

		debtors_account = frappe.db.get_single_value("FM Configuration", "customer_loan_account")
		stock_received = frappe.db.get_single_value("FM Configuration", "goods_received_but_not_billed")

		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Cash Entry"
		jv.company = loan.company
		jv.posting_date = loan.posting_date

		jv.append("accounts", {
			"account": stock_received,
			"debit_in_account_currency": self.amount
		})

		jv.append("accounts", {
			"account": debtors_account,
			"credit_in_account_currency": self.amount,
			"party_type": "Customer",
			"party_name": loan.customer
		})
		

		jv.user_remark = "Deuda generada para cliente {0} por concepto de compra \
			de poliza de seguro".format(loan.customer_name)

		jv.insurance = self.name
	
		jv.submit()

		return jv.as_dict()	



	def on_cancel(self):
		"""Run after cancelation"""

		# let's check if this insurance was term financed
		if not self.get("financiamiento"):
			return 0 # let's just ignore and do nothing else

		for index, insurance in enumerate(self.cuotas):
			if not index: 

				self.delete_payment(insurance.name)
				continue # skip the first one
			
			# now, let's fetch from the database the corresponding repayment
			loan_row = frappe.get_doc("Tabla Amortizacion", 
				{ "insurance_doc": insurance.name })

			# and unlink this insurance row from the repayment
			loan_row.insurance_doc = ""

			# clear any other amount
			loan_row.insurance = 0.000

			# pending amount will be what the customer has to pay for this repayment
			pending_amount = flt(loan_row.capital) + flt(loan_row.interes) + flt(loan_row.fine)

			loan_row.monto_pendiente = pending_amount

			loan_row.db_update()

		self.delete_payment(self.name)
		self.delete_purchase_invoice()

	def delete_purchase_invoice(self):
		"""Delete the Purchase Invoice after cancelation of the Poliza de Seguro"""

		filters = { "poliza_de_seguro": self.name }

		for current in frappe.get_list("Purchase Invoice", filters):
			
			pinv = frappe.get_doc("Purchase Invoice", current.name)

			# check to see if it was submitted
			if pinv.docstatus == 1.000:

				# let's cancel it first
				pinv.cancel()

			pinv.delete()

	def create_first_payment(self, insurance_row):
		poliza = frappe.get_value("Insurance Repayment Schedule", insurance_row.name, "parent")
		loan_name = frappe.get_value("Poliza de Seguro", poliza, "loan")
		loan = frappe.get_doc("Loan", loan_name)

		payment_account = frappe.db.get_single_value("FM Configuration", "payment_account")
		debtors_account = frappe.db.get_single_value("FM Configuration", "customer_loan_account")

		# insurance_row.amount
		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Cash Entry"
		jv.company = loan.company
		jv.posting_date = loan.posting_date

		jv.append("accounts", {
			"account": payment_account,
			"debit_in_account_currency": insurance.amount
		})

		jv.append("accounts", {
			"account": debtors_account,
			"credit_in_account_currency": insurance.amount,
			"party_type": "Customer",
			"party_name": loan.customer
		})

		jv.user_remark = "Pago inicial del seguro para cliente {0}".format(loan.customer_name)
		jv.insurance = self.name
	
		jv.submit()

		return jv.as_dict()	
		
	def delete_payment(self, insurance):
		filters = { "insurance": insurance }
		if frappe.get_value("Journal Entry", filters):
			jv = frappe.get_doc("Journal Entry", filters)

			if jv.docstatus == 1.000:
				jv.cancel()

			jv.delete()
