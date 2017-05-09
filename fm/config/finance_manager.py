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
					"description": _("Application from cutomers"),
				},
				{
					"type": "doctype",
					"name": "Loan",
					"description": _("Loan and repayment schedules"),
				},
			]
		},
		{
			"label": _("Customers"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer",
					"description": _("Customer database."),
				},
				{
					"type": "doctype",
					"label": _("Customer Group"),
					"name": "Customer Group",
					"icon": "fa fa-sitemap",
					"link": "Tree/Customer Group",
					"description": _("Manage Customer Group Tree."),
				},
				{
					"type": "doctype",
					"name": "Contact",
					"description": _("All Contacts."),
				},
				{
					"type": "doctype",
					"name": "Contact",
					"label": "Refencias",
					"description": _("All References"),
				},
				{
					"type": "doctype",
					"name": "Address",
					"description": _("All Addresses."),
				},

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
		}
	]
