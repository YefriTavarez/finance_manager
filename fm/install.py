import frappe
import fm.fixtures

def after_install():
	frappe.utils.fixtures.sync_fixtures()

	fixtures_list = [
		fm.fixtures.custom_script_list, 
		fm.fixtures.custom_field_list, 
		fm.fixtures.currency_list
	]

	for fixture in fixtures_list:
		obj = frappe._dict(fixture)

		insert_list(obj.get("doc_type"), obj.get("data"))

def insert_list(doc_type, record_list):
	for record in record_list:
		doc = frappe.get_doc(record)

		doc.insert()