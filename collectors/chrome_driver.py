"""Shared headless Chrome factory — used by the Naver news collector and the PDF exporter
so there's one place that knows how to launch/configure the browser."""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def build_headless_chrome():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")
    options.add_argument(f"user-agent={USER_AGENT}")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
