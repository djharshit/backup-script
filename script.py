import datetime
import logging
import os
import shutil

import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load environment variables
load_dotenv(override=True)

# Load configuration
PROJECT_PATH = os.environ.get("PROJECT_PATH", "")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
RETENTION = int(os.environ.get("RETENTION", 7))
USE_WEBHOOK = bool(os.environ.get("USE_WEBHOOK", False))
BACKUP_DIR = "backups/"

if not PROJECT_PATH or not GDRIVE_FOLDER_ID:
    logging.error("Environment variables are required")
    exit(1)

# Logging settings
LOG_FILE = "logs.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info("Backup process started")


# Upload to Google Drive using gdrive API
def upload_to_google_drive(backup_filename: str) -> None:
    logging.info("Uploading to Google Drive")
    file_metadata = {"name": backup_filename, "parents": [GDRIVE_FOLDER_ID]}
    media = MediaFileUpload(backup_path, resumable=True)

    # Upload the file
    try:
        file = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        logging.info(f'File uploaded successfully with ID: {file["id"]}')
    except Exception as e:
        logging.error(f"An error occurred: {e}")


# List files in a Google Drive folder
def list_files(service):
    query = f"'{GDRIVE_FOLDER_ID}' in parents"
    results = (
        service.files().list(q=query, fields="files(id, name, createdTime)").execute()
    )
    return results.get("files", [])


# Delete old gdrive backups that do not match the retention policy
def cleanup_old_gdrive_backups(service) -> None:
    """Delete old backups that do not match the retention policy."""
    files = list_files(service)

    for file in files:
        file_date = file["createdTime"].split("T")[0]

        if should_delete(file_date):
            service.files().delete(fileId=file["id"]).execute()
            logging.info(f"Deleted old backup: {file['name']}")


# Delete old local backups that do not match the retention policy
def cleanup_old_local_backups():
    if not os.path.exists(BACKUP_DIR):
        logging.info(f"Local backup directory '{BACKUP_DIR}' does not exist.")
        return

    files = os.listdir(BACKUP_DIR)

    for file_name in files:
        file_path = os.path.join(BACKUP_DIR, file_name)

        try:
            file_date = file_name.split("_")[1].split(".")[0]

        except Exception as e:
            logging.info(f"Skipping file {file_name}, error: {e}")
            continue

        if should_delete(file_date):
            os.remove(file_path)
            logging.info(f"Deleted old local backup: {file_name}")


# Check if a file should be deleted based on retention policy
def should_delete(file_date) -> bool:
    file_datetime = datetime.datetime.strptime(file_date, "%Y-%m-%d").date()
    today = datetime.date.today()

    if (today - file_datetime).days <= RETENTION:  # Keep the last X days
        return False

    sundays = [
        today - datetime.timedelta(days=today.weekday() + 1 + (7 * i))
        for i in range(RETENTION)
    ]
    if file_datetime in sundays:  # Keep the last X weeks
        return False

    first_days = [
        (today.replace(day=1) - datetime.timedelta(days=30 * i)).replace(day=1)
        for i in range(RETENTION)
    ]
    if file_datetime in first_days:  # Keep the last X months
        return False

    return True


# Generate timestamped backup filename
timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
project_name = os.path.basename(PROJECT_PATH)
backup_filename = f"{project_name}_{timestamp}.zip"
backup_path = os.path.join(BACKUP_DIR, backup_filename)

# Con
scopes = ["https://www.googleapis.com/auth/drive.file"]
service_account_file = "credentials.json"
credentials = Credentials.from_service_account_file(service_account_file, scopes=scopes)
drive_service = build("drive", "v3", credentials=credentials)

# Compress the project folder
logging.info(f"Creating backup: {backup_filename}")
shutil.make_archive(backup_path.replace(".zip", ""), "zip", PROJECT_PATH)

# Upload the backup to Google Drive
upload_to_google_drive(backup_filename)

logging.info("Cleaning up old backups")
cleanup_old_gdrive_backups(drive_service)
cleanup_old_local_backups()

if USE_WEBHOOK:
    try:
        payload = {
            "project": PROJECT_PATH,
            "date": timestamp,
            "message": "BackupSuccessful",
        }

        logging.info("Sending webhook notification")
        response = requests.post(WEBHOOK_URL, json=payload)

        if response.status_code == 200:
            logging.info("Webhook notification sent successfully")
        else:
            logging.error("Failed to send webhook notification")

    except Exception as e:
        logging.error(f"An error occurred: {e}")


logging.info("Backup process completed successfully!")
