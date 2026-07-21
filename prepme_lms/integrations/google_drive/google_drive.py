import frappe

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from prepme_lms.config.google_drive import (
    GOOGLE_DRIVE_FOLDER_ID,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_DRIVE_SCOPES,
)


def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=GOOGLE_DRIVE_SCOPES,
    )

    return build(
        "drive",
        "v3",
        credentials=credentials,
    )


def create_folder_permission(email, role="reader"):
    """
    Share Google Drive folder with a user.
    """

    service = get_drive_service()

    permission = {
        "type": "user",
        "role": role,
        "emailAddress": email,
    }

    return service.permissions().create(
        fileId=GOOGLE_DRIVE_FOLDER_ID,
        body=permission,
        fields="id",
        sendNotificationEmail=False,
        supportsAllDrives=True,
    ).execute()