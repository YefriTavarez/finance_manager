# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

from fm.finance_manager.doctype.loan.loan import update_disbursement_status

def update_loan(doc, event):
	if doc.loan:
		loan = frappe.get_doc("Loan", doc.loan)
		update_disbursement_status(loan)

@frappe.whitelist()
def loan_disbursed_amount(loan):
	return frappe.db.sql("""SELECT IFNULL(SUM(debit_in_account_currency), 0) AS disbursed_amount 
		FROM `tabGL Entry` 
		WHERE against_voucher_type = 'Loan' 
		AND against_voucher = %s""", 
		(loan), as_dict=1)[0]
