from __future__ import annotations
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Tuple
import configuration.system_config as system_config

import psycopg

# ─── SILENCE EXTERNAL LOGS ───────────────────────────────────────────────────
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Mute TensorFlow logging
# Reduce Selenium & urllib3 noise
import logging
logging.getLogger('selenium').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# ─── Bank-specific downloader imports ────────────────────────────────────────
from downloaders.JPM_downloader import dl_jpm
from downloaders.GS_downloader import dl_gs
# ... add additional bank downloader imports here

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
DSN = system_config.DSN
BASE_DOWNLOAD = Path(system_config.DOWNLOAD_FOLDER)

# ─── HANDLERS ─────────────────────────────────────────────────────────────────
# Each handler takes (html_path, out_folder) and returns the Path to the downloaded PDF
HANDLERS: Dict[str, Callable[[Path, Path], Path]] = {
    "JPM": dl_jpm,
    "GS": dl_gs,
}

# ─── UTILITIES ───────────────────────────────────────────────────────────────
ILLEGAL_FS_CHARS = re.compile(r'[\\/*?:"<>|]')

def clean_filename(name: str) -> str:
    return ILLEGAL_FS_CHARS.sub("", name).strip()

# ─── DATABASE SCHEMA ─────────────────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS reports (
  report_id     UUID PRIMARY KEY,
  entry_id      TEXT REFERENCES emails_final(entry_id),
  bank_tag      VARCHAR(20) NOT NULL,
  report_url    TEXT NOT NULL,
  report_path   TEXT NOT NULL,
  downloaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS bin (
  bin_id        UUID PRIMARY KEY,
  entry_id      TEXT,
  bank_tag      VARCHAR(20),
  html_path     TEXT,
  error_msg     TEXT,
  attempted_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE emails_final
  ADD COLUMN IF NOT EXISTS report_path TEXT;
"""

def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
        conn.commit()

# ─── CUTOFF & FETCH ──────────────────────────────────────────────────────────
def get_cutoff(cur: psycopg.Cursor, bank_tag: str) -> datetime:
    cur.execute(
        """
        SELECT MAX(e.received_ts)
          FROM reports r
          JOIN emails_final e ON r.entry_id = e.entry_id
         WHERE r.bank_tag = %s
        """,
        (bank_tag,)
    )
    result = cur.fetchone()[0]
    return result or datetime(1970, 1, 1)


def fetch_unprocessed(
    cur: psycopg.Cursor,
    bank_tag: str,
    cutoff: datetime,
) -> List[Tuple[str, Path, datetime]]:
    cur.execute(
        """
        SELECT entry_id, html_path, received_ts
          FROM emails_final
         WHERE bank_tag = %s
           AND html_path IS NOT NULL
           AND received_ts > %s
        """,
        (bank_tag, cutoff),
    )
    return [(e, Path(h), t) for e, h, t in cur.fetchall()]

# ─── RECORDING ────────────────────────────────────────────────────────────────
def record_success(
    cur: psycopg.Cursor,
    entry_id: str,
    bank_tag: str,
    report_path: Path,
) -> None:
    rid = uuid.uuid4()
    # Insert into reports table
    cur.execute(
        """
        INSERT INTO reports (report_id, entry_id, bank_tag, report_url, report_path)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(rid), entry_id, bank_tag, str(report_path), str(report_path)),
    )
    # Update emails_final with the downloaded path
    cur.execute(
        """
        UPDATE emails_final
           SET report_path = %s
         WHERE entry_id = %s
        """,
        (str(report_path), entry_id),
    )

# ─── RECORD FAILURE ─────────────────────────────────────────────────────────
def record_failure(
    cur: psycopg.Cursor,
    entry_id: str,
    bank_tag: str,
    html_path: Path,
    error: Exception,
) -> None:
    bid = uuid.uuid4()
    cur.execute(
        """
        INSERT INTO bin (bin_id, entry_id, bank_tag, html_path, error_msg)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(bid), entry_id, bank_tag, str(html_path), str(error)),
    )

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
def process_bank(conn: psycopg.Connection, bank_tag: str) -> None:
    downloader = HANDLERS.get(bank_tag)
    if downloader is None:
        return

    with conn.cursor() as cur:
        cutoff = get_cutoff(cur, bank_tag)
        rows = fetch_unprocessed(cur, bank_tag, cutoff)

    for entry_id, html_path, received_ts in rows:
        # prepare names
        subject_raw = html_path.stem.split(" - ", 1)[-1]
        subject_clean = clean_filename(subject_raw) or "untitled"
        timestamp = received_ts.strftime("%Y%m%d_%H%M%S")
        basename = f"{subject_clean}_{bank_tag}_{timestamp}.pdf"
        out_folder = BASE_DOWNLOAD / f"{received_ts:%Y}/{received_ts:%m}/{received_ts:%d}" / bank_tag
        out_folder.mkdir(parents=True, exist_ok=True)

        try:
            temp_pdf = downloader(html_path, out_folder)
            final_pdf = out_folder / basename
            temp_pdf.rename(final_pdf)
            with conn.cursor() as cur:
                record_success(cur, entry_id, bank_tag, final_pdf)
                conn.commit()
            print(f"\n{basename}: ✓ saved to {final_pdf.relative_to(BASE_DOWNLOAD)}")
        except Exception as e:
            conn.rollback()
            with conn.cursor() as cur:
                record_failure(cur, entry_id, bank_tag, html_path, e)
                conn.commit()
            print(f"\n{basename}: ✗ binned")


def pdf_downloader() -> None:

    print("--------------------- Running PDF Downloader --------------------")
    BASE_DOWNLOAD.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(**DSN, autocommit=False) as conn:
        ensure_schema(conn)
        for bank in HANDLERS:
            process_bank(conn, bank)
