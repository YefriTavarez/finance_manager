# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

from fm.finance_manager.doctype.loan.loan import update_disbursement_status

def update_loan(doc, event):
	if doc.loan:
		loan = frappe.get_doc("Loan", doc.loan)
		update_disbursement_status(loan)

def remove_loan(doc, event):
	if doc.loan:
		doc.loan = None # to remove the link
		doc.db_update()

def update_loan_table(doc, event):
	loan = frappe.get_doc("Loan", doc.loan)
	row = loan.next_repayment()
	row.estado = "SALDADA"
	row.db_update()

@frappe.whitelist()
def loan_disbursed_amount(loan):
	return frappe.db.sql("""SELECT IFNULL(SUM(debit_in_account_currency), 0) AS disbursed_amount 
		FROM `tabGL Entry` 
		WHERE against_voucher_type = 'Loan' 
		AND against_voucher = %s""", 
		(loan), as_dict=1)[0]
