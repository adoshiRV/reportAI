
from configuration import system_config
import os
import re

msg_folder = system_config.MSG_FOLDER
download_folder = system_config.DOWNLOAD_FOLDER

# Bank tagging keywords
bank_keywords = {
    "GS": ["goldman", "goldman sachs"],
    "Citi": ["citi", "citigroup", "citibank"],
    "MS": ["morgan stanley"],
    "JPM": ["jpm", "jp morgan", "j.p. morgan"],
    "UBS": ["ubs"],
    "Barclays": ["barclays"],
    "BofA": ["bofa", "bank of america"],
    "HSBC": ["hsbc"],
    "ANZ": ["anz"],
    "RV" : ["rv","rvcapital"],
    "DB":["db", "deutsche bank","deutsche"],
    "Nomura":["nomura"],
    "SCB":["standard chartered bank","scb","standard chartered"],
    "CBA": ["commonwealth bank of australia", "Commonwealth Bank", "CommBank"]
}

default_bank = "MISC"

# Noise filters
unwanted_keywords = [
    "microsoft teams", "teams meeting", "zoom", "webex", "google meet",
    "slack", "chat message", "missed call", "voicemail", "invited",
    "github", "welcome", "password", "IT", "training", "webcast", "Add to Calendar","activation code"
]


def clean_filename(subject: str) -> str:
    safe = "".join(c for c in subject if c.isalnum() or c in " _-").strip()
    return safe[:50]

def detect_bank_from_text(text: str) -> str:
    txt = text.lower()
    for bank, kws in bank_keywords.items():
        for kw in kws:
            if re.search(rf"\b{re.escape(kw)}\b", txt):
                return bank
    return default_bank

def is_unwanted(text: str) -> bool:
    return any(kw in text.lower() for kw in unwanted_keywords)

def ensure_folders():
    os.makedirs(download_folder, exist_ok=True)
    for tag in list(bank_keywords) + [default_bank]:
        os.makedirs(os.path.join(msg_folder, tag), exist_ok=True)

def clear_msg_folder():
    for root, _, files in os.walk(msg_folder):
        for fn in files:
            if fn.lower().endswith(('.eml', '.html')):
                try:
                    os.remove(os.path.join(root, fn))
                except OSError:
                    pass