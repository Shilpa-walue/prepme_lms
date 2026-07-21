import frappe

from googleapiclient.errors import HttpError

from prepme_lms.integrations.google_drive.google_drive import (
    create_folder_permission,
)


def grant_drive_access(student_id):

    try:

        student = frappe.get_doc("Student", student_id)

    except frappe.DoesNotExistError:

        frappe.log_error(
            title="Google Drive Share Failed",
            message=f"Student '{student_id}' not found.",
        )
        return

    email = student.email_id

    if not email:

        frappe.log_error(
            title="Google Drive Share Failed",
            message=(
                f"Student '{student.name}' "
                "does not have an email address."
            ),
        )
        return

    try:

        result = create_folder_permission(email)

        frappe.logger().info(
            f"Google Drive access granted "
            f"Student={student.name} "
            f"Email={email} "
            f"Permission={result.get('id')}"
        )

    except HttpError as e:

        frappe.log_error(
            title="Google Drive API Error",
            message=str(e),
        )

    except Exception:

        frappe.log_error(
            title="Unexpected Google Drive Error",
            message=frappe.get_traceback(),
        )

def after_student_insert(doc, method=None):
    """
    Triggered after a Student document is created.
    Enqueues the Google Drive sharing job.
    """
    frappe.enqueue(
        "prepme_lms.services.google_drive.drive_service.grant_drive_access",
        student_id=doc.name,
        queue="short",
    )