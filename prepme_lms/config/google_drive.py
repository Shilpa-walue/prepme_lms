import frappe

GOOGLE_DRIVE_FOLDER_ID = frappe.conf.get("google_drive_folder_id")

if not GOOGLE_DRIVE_FOLDER_ID:
    raise ValueError(
        "Missing 'google_drive_folder_id' in site_config.json"
    )

GOOGLE_SERVICE_ACCOUNT_FILE = frappe.get_site_path(
    "private",
    "files",
    "service_account.json",
)

GOOGLE_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]