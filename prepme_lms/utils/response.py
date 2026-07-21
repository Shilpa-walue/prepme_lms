"""
Standard API response envelope for Prepme LMS.

Every endpoint produces a consistent JSON payload:

	Success: {"success": true,  "message": "...", "data": {...}}
	Error:   {"success": false, "message": "...", "error_code": "..."}

IMPORTANT: never `return error_response(...)` from a whitelisted method.
Frappe overwrites `frappe.response["message"]` with whatever the method
returns, so call the helper and then `return` on the next line:

	error_response("Course not found", 404)
	return
"""

import frappe
from frappe import _


def success_response(message: str, data=None):
	"""Write a success envelope onto the outgoing response."""
	frappe.response["success"] = True
	frappe.response["message"] = _(message)

	if data is not None:
		frappe.response["data"] = data


def error_response(message: str, http_status_code: int = 400, error_code: str | None = None):
	"""Write an error envelope and set the HTTP status code."""
	frappe.local.response.http_status_code = http_status_code
	frappe.response["success"] = False
	frappe.response["message"] = _(message)

	if error_code:
		frappe.response["error_code"] = error_code

	frappe.response.pop("data", None)
