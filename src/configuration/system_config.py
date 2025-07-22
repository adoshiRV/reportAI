import os

# System config
DOWNLOAD_FOLDER = os.path.normpath(r"Z:/Business/Personnel/Arjun/GitHub/reportAI/downloads/reports")
MSG_FOLDER      = os.path.normpath(r"Z:/Business/Personnel/Arjun/GitHub/reportAI/emails")

# Database config
DB_NAME       = "postgres"
DB_USERNAME   = "postgres"
DB_PASSWORD   = "YOUR_DB_PASSWORD"

DB_HOST       = "localhost"
DB_PORT       = 5432

DSN = {
    "host":     DB_HOST,
    "port":     DB_PORT,
    "dbname":   DB_NAME,
    "user":     DB_USERNAME,
    "password": DB_PASSWORD,
}

# API keys
API_KEY     = "YOUR_API_KEY"
VOYAGE_KEY  = "YOUR_VOYAGE_KEY"

# Poppler path
POPPLER_PATH = r"C:\Release-24.08.0-0\poppler-24.08.0\Library\bin"
