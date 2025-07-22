# File: downloaders/jpm_downloader.py
import os
from pathlib import Path
import requests
from urllib.parse import urlparse, parse_qs, unquote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def find_jpmorgan_link(html_path: str) -> str:
    """
    1. Load the local HTML file in headless Chrome.
    2. Locate the <p class="originaldocumentlink"> element.
    3. Extract its <a> href; unwrap SafeLinks if present.
    """
    file_url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(file_url)
        wrapper = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.originaldocumentlink"))
        )
        a = wrapper.find_element(By.TAG_NAME, "a")
        href = a.get_attribute("href")
    finally:
        driver.quit()

    parsed = urlparse(href)
    qs = parse_qs(parsed.query)
    return unquote_plus(qs.get("url", [href])[0])


def download_pdf_with_requests(pdf_url: str, download_folder: str) -> str:
    """
    Download the given PDF URL over HTTP.
    Returns the local file path.
    """
    os.makedirs(download_folder, exist_ok=True)
    resp = requests.get(pdf_url, stream=True)
    resp.raise_for_status()
    filename = os.path.basename(urlparse(pdf_url).path) or "document.pdf"
    out_path = os.path.join(download_folder, filename)
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(1024):
            f.write(chunk)
    return out_path


def dl_jpm(html: Path, folder: Path) -> Path:
    """
    Resolver + downloader for JPMorgan research PDFs.
    """
    pdf_url = find_jpmorgan_link(str(html))
    local_path = download_pdf_with_requests(pdf_url, str(folder))
    return Path(local_path)
