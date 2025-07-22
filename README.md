# reportAI

# REPORTAI Project Documentation

## 1. Overview

`REPORTAI` is a modular Python application designed to automate the collection, processing, and summarization of research reports (e.g., PDFs) sourced from email attachments and various web sources. The pipeline consists of three main stages:

1. **Data Acquisition**  – Download raw reports (PDFs) from email and web sources.
2. **Ingestion & Vectorization** – Parse and ingest PDFs, convert text into embeddings for downstream retrieval.
3. **Summarization** – Generate concise summaries of ingested reports using AI-based techniques.

The project is organized into a clear directory structure under `src/`, with standalone folders for each functional component and helper modules for shared utilities.

---

## 2. Top-Level Structure

```
REPORTAI/
├── downloads/             # Destination for all downloaded PDFs and report artifacts
├── emails/                # Raw email files or exported messages
├── run/                   # Entry-point scripts and run configurations
│   └── run.py
├── src/                   # Main application codebase
│   ├── ai_summary/        # AI summarization & vectorization logic
│   ├── configuration/     # Environment and system configuration
│   ├── downloaders/       # Modules to fetch reports (email + web)
│   ├── helpers/           # Shared utility functions
│   └── summarization/     # (Optional) alternative summarization routines
├── .gitignore             # Git exclusion rules
└── README.md              # High-level project description & setup
```

---

## 3. Detailed Directory & File Descriptions

### 3.1 `downloads/` and `emails/`

* **Purpose:**

  * `downloads/` stores all downloaded research reports (PDFs) fetched by the pipeline.
  * `emails/` holds raw email exports or message files (e.g., `.msg` or `.eml`) used by the email scraper.
* **Contents:** Initially empty; populated at runtime by the downloader modules.

### 3.2 `run/` Folder

* **`run.py`** – The orchestrator script executed by the user. Its responsibilities:

  1. Add `src/` to the Python path.
  2. Invoke downloader modules (e.g., `email_scraper`, `pdf_downloader`).
  3. Kick off ingestion and vectorization via `ingest_and_vectorize_reports()` from `ai_summary`. (this will hit limits - only uncomment email_scraper() and pdf_downloader() )

```python

# run/run.py
def main():
    print("🔥  run.py starting up…")
    # Step 1: scrape emails
    # email_scraper(lookback_days=12)

    # Step 2: download PDFs from configured sources
    pdf_downloader()

    # Step 3: ingest & vectorize documents for AI summarization
    ingest_and_vectorize_reports()
```

### 3.3 `src/` Folder

#### 3.3.1 `configuration/`

* **`system_config.py`**

  * Centralizes all environment-specific settings:

    * Folder paths (e.g., `DOWNLOAD_FOLDER`, `MSG_FOLDER`).
    * Database credentials (`DB_NAME`, `DB_HOST`, etc.).
    * API keys and external service parameters.
  * Imported throughout the codebase to avoid hardcoding values.

#### 3.3.2 `downloaders/`

Contains modules responsible for fetching raw reports from different sources:

* **`email_scraper.py`**

  * Connects to a mailbox (e.g., via MAPI or IMAP) to scan recent messages.
  * Downloads attachments matching report criteria into `downloads/` and moves emails to `emails/`.

* **`pdf_downloader.py`**

  * Scans a predefined list of URLs or APIs (e.g., bank research portals).
  * Fetches and stores PDF reports locally.

* **`GS_downloader.py`**, **`JPM_downloader.py`**

  * Vendor-specific downloaders (e.g., Goldman Sachs, J.P. Morgan) with custom authentication and scraping logic.

#### 3.3.3 `ai_summary/`

Implements the ingestion and vectorization pipeline:

* **`summarization_vectorization.py`**

  * Reads PDF text.
  * Splits documents into chunks (for embedding limits).
  * Calls an embedding model (e.g., OpenAI or local transformer) to generate vectors.
  * Stores embeddings in a vector database for retrieval.

* **`__init__.py`** – Initializes the package and exposes key functions (e.g., `ingest_and_vectorize_reports`).

#### 3.3.4 `helpers/`

Shared utilities to support downloader and summarization modules:

* **`database_helpers.py`**

  * Functions to establish and manage database connections.
  * Ensures schema creation (tables for metadata, embedding storage).

* **`downloader_helpers.py`**

  * Helper routines for HTTP requests, session management, retry logic.
  * Generic file I/O and path handling to keep downloader code DRY.

#### 3.3.5 `summarization/`

(Optional) Contains alternate or legacy summarization implementations, such as rule-based text summarizers or prompts for AI models. Can be deprecated or swapped out depending on quality.

---

## 4. Workflow Summary

1. **Configuration Loading**: `system_config.py` is imported to fetch folder paths, database credentials, and API keys.
2. **Data Download**: Running `run.py` triggers downloader modules:

   * **Email Scraper** collects report attachments.
   * **PDF Downloader** fetches vendor research.
3. **Ingestion & Vectorization**:

   * Text is extracted from each PDF.
   * Documents are chunked and sent to an embedding API.
   * Embeddings and metadata are saved for downstream search and summarization.
4. **Summarization & Retrieval**:

   * Client applications can query the vector database.
   * Summaries are generated on demand via AI-based prompts.

---

## 5. Getting Started

1. **Environment Setup**:

   * Clone the repository and create a Python virtual environment.
   * Install dependencies from `requirements.txt` (if present) or manually install libraries (e.g., `psycopg`, `openai`, `PyPDF2`).
2. **Configuration**:

   * Edit `src/configuration/system_config.py` to set database credentials, API keys, and folder paths.

3. **Run the Pipeline**:

   ```bash
   python run/run.py
   ```
4. **Extend**:

   * Add new downloaders under `src/downloaders/`.
   * Enhance summarization strategies in `src/ai_summary/` or `src/summarization/`.




