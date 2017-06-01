# -*- coding: utf-8 -*-
# Copyright (c) 2017, Soldeva, SRL and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

class TestLoan(unittest.TestCase):
	# def set_missing_values(self):
	# 	# to fecth the default company
	# 	# self.company = frappe.defaults.get_global_default("company")

	# 	frappe.get_test_records("Company")

	def test_loan_expenses_rate(self):
		self.assertTrue(True)