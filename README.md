# Automated Backup and Rotation Script

## Overview

This script automates the backup process for a project's code files, implements a rotational backup strategy, and integrates with Google Drive to push the backups to a specified folder. Additionally, it deletes older backups according to the rotational strategy and sends a webhook notification on successful backup.

## Requirements

- Python 3.x
- Google API Python Client
- Google Auth
- Requests

## Installation

1. Clone the repository:

```sh
git clone https://github.com/djharshit/backup-script
cd backup-script
```

2. Install the required Python packages:

```sh
pip3 install -r requirements.txt
```

3. Set up your environment variables in a `.env` file:

```env
PROJECT_PATH=/path/to/your/project
GDRIVE_FOLDER_ID=your_google_drive_folder_id
RETENTION=retention_number
USE_WEBHOOK=True
WEBHOOK_URL=your_webhook_url
```

## Configuration

1. **Google Drive Integration:**

- Ensure you have a [credentials.json](./credentials.json) file for Google Drive API authentication. Place the file in the root directory of the project.

2. **Environment Variables:**

- PROJECT_PATH: Path to the project folder you want to back up.
- GDRIVE_FOLDER_ID: Google Drive folder ID where backups will be uploaded.
- RETENTION: Number of days to retain backups.
- WEBHOOK_URL: URL to send a webhook notification on successful backup.
- USE_WEBHOOK: Set to `True` to enable webhook notifications.

## Usage

Run the script:

```sh
python3 one.py
```

### Logging

The script logs all activities to logs.log file, including backup creation, upload status, and cleanup of old backups.

### Cleanup Old Backups

The script deletes old backups from the backups directory based on the retention period specified in the environment variables.
