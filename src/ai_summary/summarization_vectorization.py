#!/usr/bin/env python3
# ingest_reports.py
"""
Simple PDF ingestion and vectorization pipeline with print logging.
Run `ingest_and_vectorize_reports(dry_run=True)` from your REPL or another script.
"""
import os
import io
import base64
import time

import psycopg
import psycopg.errors
import anthropic
import voyageai
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from configuration import system_config as sysconfig

# ─── Configuration ─────────────────────────────────────────────────────────────
DSN = sysconfig.DSN               # Postgres connection info (string or dict)
CLAUDE_KEY = sysconfig.API_KEY     # Anthropic API key
VOYAGE_KEY = sysconfig.VOYAGE_KEY  # Voyage API key
POPPLER_PATH = sysconfig.POPPLER_PATH  # Path to poppler binaries

# ─── Initialize clients ─────────────────────────────────────────────────────────
claude_client = anthropic.Anthropic(api_key=CLAUDE_KEY)
voyage_client = voyageai.Client(api_key=VOYAGE_KEY)

# ─── Helpers ───────────────────────────────────────────────────────────────────
def extract_text(pdf_path: str) -> str:
    print(f"Extracting text from {pdf_path}")
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def pdf_images_to_base64(pdf_path: str) -> list[str]:
    print(f"Converting all pages of {pdf_path} to images")
    images = convert_from_path(
        pdf_path,
        poppler_path=POPPLER_PATH or None
    )
    encoded = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        encoded.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
    return encoded

def query_claude(text: str, images_b64: list[str], prompt: str) -> str:
    print("Querying Claude for summary")
    blocks = []
    if text:
        blocks.append({"type": "text", "text": text[:15000]})
    for img in images_b64:
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}})
    blocks.append({"type": "text", "text": prompt})

    resp = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        temperature=0.6,
        messages=[{"role": "user", "content": blocks}]
    )
    summary = resp.content
    # Ensure summary is a plain string
    if isinstance(summary, list):
        lines = []
        for item in summary:
            if hasattr(item, 'text'):
                lines.append(item.text)
            elif isinstance(item, dict) and 'text' in item:
                lines.append(item['text'])
            else:
                lines.append(str(item))
        summary = "".join(lines)
    return summary



def get_embedding(text: str) -> list[float]:
    print("Getting embedding from Voyage")
    resp = voyage_client.embed([text], model="voyage-large-2", input_type="document")
    return resp.embeddings[0]

# ─── Pipeline ─────────────────────────────────────────────────────────────────
def ingest_and_vectorize_reports(dry_run: bool = False):
    print(f"-------------- Starting ingestion: dry_run={dry_run} ----------------------")
    # Connect using dict or connection string
    if isinstance(DSN, dict):
        conn = psycopg.connect(**DSN, autocommit=True)
    else:
        conn = psycopg.connect(DSN, autocommit=True)
    cur = conn.cursor()

    # Ensure report_vectors table exists
    print("Ensuring 'report_vectors' table exists...")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS report_vectors (
            report_id UUID PRIMARY KEY,
            report_path TEXT NOT NULL,
            email_received_ts TIMESTAMP WITH TIME ZONE,
            embedding DOUBLE PRECISION[],
            summary TEXT
        );
        """
    )

    # Fetch reports that haven't been vectorized yet
    cur.execute(
        """
        SELECT r.report_id, r.report_path, e.received_ts
          FROM reports r
          JOIN emails_final e ON r.entry_id = e.entry_id
         WHERE r.report_id NOT IN (SELECT report_id FROM report_vectors)
         ORDER BY r.downloaded_at;
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("No new reports to ingest.")
        cur.close()
        conn.close()
        return

    for report_id, path, received_ts in rows:
        print(f"Processing report_id={report_id}, path={path}, received_ts={received_ts}")
        text = extract_text(path)
        images = pdf_images_to_base64(path)
        summary = query_claude(
            text,
            images,
            "You are a rates trader. Summarise this PDF into subsections with no opinions, then output topical tags: country, region, topic, impact, macro."
        )
        emb = get_embedding(summary)

        if dry_run:
            print(f"[DRY RUN] Would INSERT {report_id} with embedding length {len(emb)}")
        else:
            print(f"Inserting vectors for {report_id}")
            cur.execute(
                """
                INSERT INTO report_vectors
                  (report_id, report_path, email_received_ts, embedding, summary)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (report_id) DO NOTHING;
                """,
                (report_id, path, received_ts, emb, summary)
            )
            print(f"✔️ Ingested {report_id}")


        # pause 60 seconds before processing the next report
        print("Waiting 60 seconds before next report...")
        time.sleep(60)

    cur.close()
    conn.close()
    print("Batch complete.")
