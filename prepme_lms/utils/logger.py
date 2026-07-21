import json

import frappe


def _format(title, message, data=None):
    log_message = f"{title} | {message}"

    if data:
        log_message += f" | {json.dumps(data, default=str)}"

    return log_message


def _logger():
    return frappe.logger(
        "prepme_lms",
        allow_site=True,
        file_count=20,
    )


def log_info(title, message, data=None):
    _logger().info(
        _format(title, message, data)
    )


def log_warning(title, message, data=None):
    _logger().warning(
        _format(title, message, data)
    )


def log_error(title, message, data=None):
    log_message = _format(title, message, data)

    _logger().error(log_message)

    frappe.log_error(
        title=title,
        message=log_message,
    )


def log_exception(title, exception):
    _logger().exception(
        f"{title} | {exception}"
    )

    frappe.log_error(
        title=title,
        message=frappe.get_traceback(),
    )