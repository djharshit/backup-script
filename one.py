import os
import shutil
import datetime
import requests
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

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
        file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        logging.info(f'File uploaded successfully with ID: {file["id"]}')
    except Exception as e:
        logging.error(f"An error occurred: {e}")


# Implement rotational backup strategy
def cleanup_old_backups(service) -> None:
    now = datetime.datetime.now()

    logging.info(f"Deleting old backups from local directory")
    for file in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, file)

        if os.path.isfile(file_path):
            creation_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
            age = (now - creation_time).days

            if age > RETENTION:
                os.remove(file_path)

    query = f"'{GDRIVE_FOLDER_ID}' in parents and mimeType='application/zip'"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name, createdTime)").execute()
    items = results.get("files", [])

    logging.info(f"Deleting old backup from Google Drive")
    for item in items:
        creation_time = datetime.datetime.strptime(item["createdTime"], "%Y-%m-%dT%H:%M:%S.%fZ")
        age = (now - creation_time).days

        if age > RETENTION:
            service.files().delete(fileId=item["id"]).execute()


# Generate timestamped backup filename
timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
project_name = os.path.basename(PROJECT_PATH)
backup_filename = f"{project_name}_{timestamp}.zip"
backup_path = os.path.join(BACKUP_DIR, backup_filename)

# Configur
scopes = ["https://www.googleapis.com/auth/drive.file"]
service_account_file = "credentials.json"
credentials = Credentials.from_service_account_file(service_account_file, scopes=scopes)
drive_service = build("drive", "v3", credentials=credentials)

# Compress the project folder
logging.info(f"Creating backup: {backup_filename}")
shutil.make_archive(backup_path.replace(".zip", ""), "zip", PROJECT_PATH)

# Upload the backup to Google Drive
upload_to_google_drive(backup_filename)

logging.info("Cleaning up old backups...")
cleanup_old_backups(drive_service)

if USE_WEBHOOK:
    try:
        payload = {"project": PROJECT_PATH, "date": timestamp, "message": "BackupSuccessful"}

        logging.info("Sending webhook notification...")
        response = requests.post(WEBHOOK_URL, json=payload)

        if response.status_code == 200:
            logging.info("Webhook notification sent successfully")
        else:
            logging.error("Failed to send webhook notification")

    except Exception as e:
        logging.error(f"An error occurred: {e}")


logging.info("Backup process completed successfully!")
