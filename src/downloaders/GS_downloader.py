# File: downloaders/gs_downloader.py
from pathlib import Path
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import time


def wait_for_new_pdf(folder: Path, before: set[str], timeout: int = 60) -> Path:
    """
    Poll *folder* until a new .pdf appears that wasn't in *before*.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        now = {f for f in os.listdir(folder) if f.lower().endswith(".pdf")}
        new = now - before
        if new:
            return folder / new.pop()
        time.sleep(15)
    raise TimeoutError("No new PDF detected in %s within %s s" % (folder, timeout))


def download_via_click(
    html_path: Path,
    download_folder: Path,
    xpath: str,
    timeout: int = 60,
) -> Path:
    """
    Opens the given HTML file in headless Chrome, clicks the element
    matching the provided XPath, waits for a new PDF download, and
    returns its Path.
    """
    # Ensure download directory exists
    download_folder.mkdir(parents=True, exist_ok=True)
    # Record existing PDFs
    before = {f for f in os.listdir(download_folder) if f.lower().endswith('.pdf')}

    # Configure headless Chrome
    options = Options()
    options.headless = True
    options.add_experimental_option(
        "prefs", {
            "download.default_directory": str(download_folder),
            "plugins.always_open_pdf_externally": True,
        }
    )

    driver = webdriver.Chrome(options=options)
    try:
        # Load the local HTML email
        driver.get(html_path.as_uri())
        # Click the PDF link via XPath
        driver.find_element(By.XPATH, xpath).click()
        # Wait for the PDF to appear
        return wait_for_new_pdf(download_folder, before, timeout)
    finally:
        driver.quit()


def dl_gs(html: Path, folder: Path) -> Path:
    """
    Downloader wrapper for Goldman Sachs research PDFs:
    looks for any <a> whose href contains "pdf" (case-insensitive) and clicks it.
    """
    # Use XPath that matches links ending in .pdf
    xpath = "//a[contains(translate(@href, 'PDF', 'pdf'), 'pdf')]"
    return download_via_click(html, folder, xpath)
