# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "fm"
app_title = "Finance Manager"
app_publisher = "Soldeva, SRL"
app_description = "Una applicacion para la gestion de una financiera."
app_icon = "octicon octicon-flame"
app_color = "#496"
app_email = "servicios@soldeva.com"
app_license = "General Public Licence v3"

fixtures = ["Custom Script", "Custom Field", "Role", "Print Format", "FM Configuration", "Translation"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fm/css/fm.css"
# app_include_js = "/assets/fm/js/fm.js"

# include js, css files in header of web template
# web_include_css = "/assets/fm/css/fm.css"
# web_include_js = "/assets/fm/js/fm.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "fm.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "fm.install.before_install"
after_install = "frappe.utils.fixtures.sync_fixtures"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

doc_events = {
	"Journal Entry": {
		"on_submit": "fm.accounts.update_loan",
		"on_cancel": "fm.accounts.update_loan",
		"on_trash": "fm.accounts.remove_loan",
	},
	"Payment Entry": {
		"on_submit": "fm.accounts.update_loan_table",
		"on_cancel": "fm.accounts.update_loan_table",
		"on_trash": "fm.accounts.remove_loan"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"fm.scheduler.calculate_fines"
	]
}

# scheduler_events = {
# 	"all": [
# 		"fm.tasks.all"
# 	],
# 	"daily": [
# 		"fm.tasks.daily"
# 	],
# 	"hourly": [
# 		"fm.tasks.hourly"
# 	],
# 	"weekly": [
# 		"fm.tasks.weekly"
# 	]
# 	"monthly": [
# 		"fm.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "fm.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "fm.event.get_events"
# }

