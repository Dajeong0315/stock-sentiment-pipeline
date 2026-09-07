"""Central config, loaded from .env. Swap TICKER/DART_CORP_CODE to reuse this pipeline for another stock."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TICKER = os.getenv("TICKER", "005930.KS")
DART_CORP_CODE = os.getenv("DART_CORP_CODE", "00126380")
DART_CORP_NAME_HINT = os.getenv("DART_CORP_NAME_HINT", "삼성전자")

OPENDART_API_KEY = os.getenv("OPENDART_API_KEY", "")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")

DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/pipeline.sqlite")
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports" / "output"

NAVER_NEWS_SEARCH_URL = "https://search.naver.com/search.naver?where=news&query={query}"
NEWS_SEARCH_QUERY = os.getenv("NEWS_SEARCH_QUERY", DART_CORP_NAME_HINT)
NEWS_MAX_ARTICLES_PER_RUN = int(os.getenv("NEWS_MAX_ARTICLES_PER_RUN", "30"))

for _dir in (DATA_DIR, LOG_DIR, REPORT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
