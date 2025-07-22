"""
run.py

Entry point for the reportAI pipeline. This script bootstraps the environment, 
downloads email and PDF reports, and ingests them into the AI summarization and 
vectorization workflow.
"""

import sys
from pathlib import Path

# === Configure Module Search Path ===
# Resolve the path to the project root (two levels up from this file)
# Add the src directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# === Project-Specific Imports ===
# The email_scraper module handles fetching and saving emails for downstream processing
from downloaders.email_scraper import email_scraper
# The pdf_downloader module handles extraction of PDF files from saved emails or other sources
from downloaders.pdf_downloader import pdf_downloader
# The summarization_vectorization module converts downloaded documents into vectors for semantic search
from ai_summary.summarization_vectorization import ingest_and_vectorize_reports


# Print a startup banner to indicate the script has begun execution
# flush=True ensures the message appears immediately in logs or console
print("🔥  run.py starting up…", flush=True)

# ----- Step 1: Email Scraping -----
# By default, email_scraper() will look back a configurable number of days (DB_LAG_DAYS).
# email_scraper(lookback_days=12)

pdf_downloader()

# ingest_and_vectorize_reports()