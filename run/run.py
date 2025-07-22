# run/run.py
import sys
from pathlib import Path

# Add the src directory to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from downloaders.email_scraper import email_scraper
from downloaders.pdf_downloader import pdf_downloader
from ai_summary.summarization_vectorization import ingest_and_vectorize_reports

print("🔥  run.py starting up…", flush=True)

# email_scraper(lookback_days=12)

pdf_downloader()

# ingest_and_vectorize_reports()