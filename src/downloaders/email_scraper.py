# import os
# import shutil
# import sys
# from datetime import datetime, timedelta

# import win32com.client
# import psycopg

# import configuration.system_config as sys_config
# import helpers.database_helpers as database_helpers

# TEST_MODE       = False
# download_folder = sys_config.DOWNLOAD_FOLDER
# msg_folder      = sys_config.MSG_FOLDER
# MAX_EMAILS      = sys_config.DB_MAX_EMAILS

# def email_scraper(lookback_days=None):
#     print("▶︎  email_scraper() invoked", flush=True)

#     # 1) Determine lookback window
#     if lookback_days is None:
#         lookback_days = sys_config.DB_LAG_DAYS
#     fallback_dt = datetime.now() - timedelta(days=lookback_days)
#     print(f"DEBUG: fallback lookback_dt = {fallback_dt}", flush=True)

#     database_helpers.ensure_folders()

#     conn_params = {
#         "host":   sys_config.DB_HOST,
#         "port":   sys_config.DB_PORT,
#         "dbname": sys_config.DB_NAME,
#         "user":   sys_config.DB_USERNAME,
#         "password": sys_config.DB_PASSWORD,
#     }

#     # 2) Create table & fetch last imported timestamp
#     with psycopg.connect(**conn_params, autocommit=True) as conn, conn.cursor() as cur:
#         cur.execute("""
#         CREATE TABLE IF NOT EXISTS emails_final (
#           entry_id    TEXT PRIMARY KEY,
#           received_ts TIMESTAMP NOT NULL,
#           bank_tag    VARCHAR(20) NOT NULL,
#           subject     TEXT NOT NULL,
#           body_snip   TEXT,
#           file_path   TEXT NOT NULL,
#           html_path   TEXT,
#           raw_msg     BYTEA NOT NULL,
#           imported_at TIMESTAMPTZ DEFAULT now()
#         );
#         CREATE INDEX IF NOT EXISTS idx_emails_tag_date
#           ON emails_final(bank_tag, received_ts DESC);
#         """)
#         cur.execute("SELECT MAX(received_ts) FROM emails_final;")
#         last_ts = cur.fetchone()[0]
#         print(f"DEBUG: last_ts from DB = {last_ts}", flush=True)

#     # 3) Decide the real cutoff: whichever is newer, last_ts or fallback
#     if last_ts and last_ts > fallback_dt:
#         cutoff_dt = last_ts
#         print("DEBUG: using last_ts as cutoff", flush=True)
#     else:
#         cutoff_dt = fallback_dt
#         print("DEBUG: using fallback cutoff (no run for a while) →", cutoff_dt, flush=True)

#     # 4) Grab all messages, sorted descending by ReceivedTime
#     outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
#     inbox   = outlook.GetDefaultFolder(6)
#     items   = inbox.Items
#     items.Sort("[ReceivedTime]", True)

#     # 5) Loop in Python until we hit cutoff_dt or MAX_EMAILS
#     saved = deleted = 0
#     with psycopg.connect(**conn_params, autocommit=True) as conn, conn.cursor() as cur:
#         msg   = items.GetFirst()
#         count = 0
#         while msg and count < MAX_EMAILS:
#             # pull and normalize ReceivedTime
#             rcvd = msg.ReceivedTime
#             # strip any tzinfo so comparison with cutoff_dt (naive) works
#             rcvd = rcvd.replace(tzinfo=None)

#             # if this message is at-or-before our cutoff, stop looping
#             if rcvd <= cutoff_dt:
#                 break

#             subj     = msg.Subject or "NoSubject"
#             body     = msg.Body or ""
#             combined = f"{subj}\n{body}"

#             try:
#                 # 5a) Delete unwanted
#                 if database_helpers.is_unwanted(combined):
#                     msg.Delete()
#                     deleted += 1
#                     print(f"Deleted unwanted: {subj}", flush=True)
#                 else:
#                     # 5b) Save & insert
#                     bank    = database_helpers.detect_bank_from_text(combined)
#                     ts_str  = rcvd.strftime("%Y-%m-%d_%H-%M-%S")
#                     base_fn = f"{ts_str} - {database_helpers.clean_filename(subj)}"
#                     folder  = os.path.join(msg_folder, bank)
#                     os.makedirs(folder, exist_ok=True)

#                     html_path = os.path.join(folder, base_fn + ".html")
#                     msg.SaveAs(html_path, 5)

#                     tmp_eml  = os.path.join("C:\\Temp", base_fn + ".eml")
#                     os.makedirs(os.path.dirname(tmp_eml), exist_ok=True)
#                     msg.SaveAs(tmp_eml)
#                     eml_path = os.path.join(folder, base_fn + ".eml")
#                     shutil.move(tmp_eml, eml_path)

#                     raw_bytes = open(eml_path, "rb").read()

#                     cur.execute(
#                         """
#                         INSERT INTO emails_final
#                           (entry_id, received_ts, bank_tag, subject,
#                            body_snip, file_path, html_path, raw_msg)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#                         ON CONFLICT (entry_id) DO NOTHING;
#                         """,
#                         (
#                             msg.EntryID,
#                             rcvd,
#                             bank,
#                             subj,
#                             body[:2000],
#                             eml_path,
#                             html_path,
#                             psycopg.Binary(raw_bytes),
#                         )
#                     )

#                     saved += 1
#                     print(f"Saved: {base_fn}.html → {bank}", flush=True)

#             except Exception as e:
#                 print(f"Error on email #{count}: {e}", file=sys.stderr, flush=True)

#             count += 1
#             msg = items.GetNext()

#     print(f"Done: {saved} saved, {deleted} deleted.", flush=True)


import os
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta

import win32com.client
import psycopg

import configuration.system_config as sys_config
import helpers.database_helpers as database_helpers

TEST_MODE       = False
download_folder = sys_config.DOWNLOAD_FOLDER
msg_folder      = sys_config.MSG_FOLDER
MAX_EMAILS      = sys_config.DB_MAX_EMAILS

def email_scraper(lookback_days=None):
    print("▶︎  email_scraper() invoked", flush=True)

    # 1) Determine the fallback lookback window
    fallback_dt = datetime.now() - timedelta(days=lookback_days or sys_config.DB_LAG_DAYS)
    print(f"DEBUG: fallback lookback_dt = {fallback_dt}", flush=True)

    database_helpers.ensure_folders()

    conn_params = {
        "host":   sys_config.DB_HOST,
        "port":   sys_config.DB_PORT,
        "dbname": sys_config.DB_NAME,
        "user":   sys_config.DB_USERNAME,
        "password": sys_config.DB_PASSWORD,
    }

    # 2) Create table, fetch last imported timestamp AND existing IDs
    with psycopg.connect(**conn_params, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS emails_final (
          entry_id    TEXT PRIMARY KEY,
          received_ts TIMESTAMP NOT NULL,
          bank_tag    VARCHAR(20) NOT NULL,
          subject     TEXT NOT NULL,
          body_snip   TEXT,
          file_path   TEXT NOT NULL,
          html_path   TEXT,
          raw_msg     BYTEA NOT NULL,
          imported_at TIMESTAMPTZ DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_emails_tag_date
          ON emails_final(bank_tag, received_ts DESC);
        """)
        cur.execute("SELECT MAX(received_ts) FROM emails_final;")
        last_ts = cur.fetchone()[0]
        print(f"DEBUG: last_ts from DB = {last_ts}", flush=True)

        # grab every entry_id so we can report/skips duplicates
        cur.execute("SELECT entry_id FROM emails_final;")
        existing_ids = {row[0] for row in cur.fetchall()}

    # 3) Decide cutoff: explicit lookback overrides last_ts
    if lookback_days is not None:
        cutoff_dt = fallback_dt
        print("DEBUG: explicit lookback → using fallback cutoff:", cutoff_dt, flush=True)
    else:
        if last_ts and last_ts > fallback_dt:
            cutoff_dt = last_ts
            print("DEBUG: using last_ts as cutoff:", cutoff_dt, flush=True)
        else:
            cutoff_dt = fallback_dt
            print("DEBUG: using fallback cutoff (no recent run):", cutoff_dt, flush=True)

    # 4) Prepare Outlook
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox   = outlook.GetDefaultFolder(6)
    items   = inbox.Items
    items.Sort("[ReceivedTime]", True)

    # 5) Loop, track our buckets
    saved, deleted, skipped = [], [], []
    with psycopg.connect(**conn_params, autocommit=True) as conn, conn.cursor() as cur:
        msg   = items.GetFirst()
        count = 0
        while msg and count < MAX_EMAILS:
            entry_id = msg.EntryID
            rcvd = msg.ReceivedTime.replace(tzinfo=None)

            # stop once we hit or pass the cutoff
            if rcvd <= cutoff_dt:
                break

            # skip if already in DB
            if entry_id in existing_ids:
                skipped.append(entry_id)
                print(f"SKIP (already imported): {entry_id}", flush=True)
                msg = items.GetNext()
                count += 1
                continue

            subj     = msg.Subject or "NoSubject"
            body     = msg.Body or ""
            combined = f"{subj}\n{body}"

            try:
                if database_helpers.is_unwanted(combined):
                    msg.Delete()
                    deleted.append(entry_id)
                    print(f"Deleted unwanted: {subj}", flush=True)
                else:
                    bank    = database_helpers.detect_bank_from_text(combined)
                    ts_str  = rcvd.strftime("%Y-%m-%d_%H-%M-%S")
                    base_fn = f"{ts_str} - {database_helpers.clean_filename(subj)}"
                    folder  = os.path.join(msg_folder, bank)
                    os.makedirs(folder, exist_ok=True)

                    html_path = os.path.join(folder, base_fn + ".html")
                    msg.SaveAs(html_path, 5)

                    tmp_eml  = os.path.join("C:\\Temp", base_fn + ".eml")
                    os.makedirs(os.path.dirname(tmp_eml), exist_ok=True)
                    msg.SaveAs(tmp_eml)
                    eml_path = os.path.join(folder, base_fn + ".eml")
                    shutil.move(tmp_eml, eml_path)

                    raw_bytes = open(eml_path, "rb").read()

                    cur.execute(
                        """
                        INSERT INTO emails_final
                          (entry_id, received_ts, bank_tag, subject,
                           body_snip, file_path, html_path, raw_msg)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            entry_id,
                            rcvd,
                            bank,
                            subj,
                            body[:2000],
                            eml_path,
                            html_path,
                            psycopg.Binary(raw_bytes),
                        )
                    )
                    saved.append(entry_id)
                    print(f"Saved: {base_fn}.html → {bank}", flush=True)

            except Exception as e:
                print(f"Error on email #{count} ({entry_id}): {e}", file=sys.stderr, flush=True)

            count += 1
            msg = items.GetNext()

    # 6) Final summary
    print("─── Run complete ───")
    print(f"  Saved   : {len(saved)} emails → {saved}")
    print(f"  Deleted : {len(deleted)} emails → {deleted}")
    print(f"  Skipped : {len(skipped)} emails → {skipped}")
    print("────────────────────", flush=True)
