from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Docs"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Loan Application",
				},
				{
					"type": "doctype",
					"name": "Loan",
				},
				{
					"type": "doctype",
					"name": "Poliza de Seguro",
				},
				{
					"type": "doctype",
					"name": "Amortization Tool",
				},
			]
		},
		{
			"label": _("Others"),
			"icon": "fa fa-star",
			"items": [
				{
					"type": "doctype",
					"name": "Sales Invoice",
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
				},
				{
					"type": "doctype",
					"name": "Journal Entry",
				},
			]
		},
		{
			"label": _("Customers"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer",
				},
				{
					"type": "doctype",
					"label": _("Customer Group"),
					"name": "Customer Group",
					"icon": "fa fa-sitemap",
					"link": "Tree/Customer Group",
				}
			]
		},
		{
			"label": _("Bienes"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle",
					"label": "Vehiculo"
				},
				{
					"type": "doctype",
					"name": "Vivienda"
				}
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"name": "General Ledger",
					"doctype": "GL Entry",	
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Balance Sheet",
					"doctype": "GL Entry",	
					"is_query_report": True
				},
				{

					"type": "report",
					"name": "Sales Register",
					"doctype": "Sales Invoice",	
					"label": "Reporte de Alquiler",
					"is_query_report": True
				},				
				{

					"type": "report",
					"name": "Purchase Register",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Receivable",
					"doctype": "Sales Invoice",	
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Accounts Payable",
					"doctype": "Purchase Invoice",
					"is_query_report": True
				},
				{
					"type": "report",
					"name": "Balance Sheet",
					"doctype": "GL Entry",	
					"is_query_report": True
				},

			]
		},
		{
			"label": _("Configuration"),
			"items": [
				{
					"type": "doctype",
					"name": "FM Configuration",
					"label": _("Control Panel")
				},
				{
					"type": "doctype",
					"name": "Currency Exchange",
				},
			]
		}
	]
