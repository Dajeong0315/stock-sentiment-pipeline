# 주가·공시·뉴스 통합 분석 + 로컬 LLM 감정점수화 파이프라인

주가(Yahoo Finance) + 공시(OpenDART) + 뉴스(Naver 뉴스 검색)를 수집하고, 규칙기반(정규식+Kiwi
형태소분석)과 로컬 오픈소스 LLM(Ollama + Qwen2.5-3B-Instruct, 4bit) 두 가지 방식으로 뉴스
감정을 점수화해 비교하는 개인 프로젝트. scikit-learn 가격예측 모델과 결합해 하나의 종합
시그널을 만들고, Streamlit 대시보드와 마크다운 리포트로 확인할 수 있다.

대상 종목은 예시로 삼성전자(`005930.KS`)를 쓰지만 `.env`의 `TICKER`/`DART_CORP_CODE`만
바꾸면 다른 종목에도 그대로 적용되도록 설계했다.

**현재 완료 단계: MVP 완료** (공시 수집은 OpenDART API 키 설정 후 최종 검증 필요 — [PROGRESS.md](PROGRESS.md) 참고)
**확장 범위(Docker/K8s/CI 등)는 착수하지 않음** — 자세한 내용은 [PORTFOLIO_NOTES.md](PORTFOLIO_NOTES.md) 참고.

## 실행 환경

- CPU 전용 (GPU 불필요) — 로컬 LLM은 4bit 양자화된 3B급 모델만 사용
- 예산 0원 — 전부 오픈소스/무료 도구 (yfinance, OpenDART 무료 API, Selenium, Kiwi, scikit-learn, Ollama, Streamlit)
- Python 3.13, Windows 기준으로 작성 (경로 구분자 등은 `pathlib`로 처리해 OS 무관)

## 설치

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # 값 채워넣기
```

`.env`에 채워야 할 값:
- `OPENDART_API_KEY` — https://opendart.fss.or.kr 에서 무료 발급
- `TICKER` — Yahoo Finance 티커 (기본 `005930.KS`)
- `DART_CORP_CODE` — OpenDART corp_code (기본값은 삼성전자; 모르면 비워두면 `DART_CORP_NAME_HINT`로 자동 조회 시도)

Ollama 설치 및 모델 다운로드:

```bash
winget install Ollama.Ollama
ollama pull qwen2.5:3b-instruct-q4_K_M
```

## 실행 방법

```bash
# 전체 파이프라인 1회 수동 실행 (수집 + EDA/모델 + LLM 감정 + 대시보드용 데이터 + 리포트 + git commit)
python scripts/run_pipeline.py --mode manual

# 수집만 (스케줄러가 매일 호출하는 것과 동일한 경량 모드)
python scripts/run_pipeline.py --mode scheduled

# 매일 자동 수집되게 하려면 (블로킹 프로세스 방식)
python -m scheduler.daily_job

# 대시보드
streamlit run dashboard/app.py
```

Windows에서 프로세스를 계속 띄워두지 않고 OS 스케줄러로 등록하려면:

```bash
schtasks /create /tn "StockSentimentDaily" /tr "\"%CD%\.venv\Scripts\python.exe\" \"%CD%\scripts\run_pipeline.py\" --mode scheduled" /sc daily /st 08:00
```

개별 모듈 실행 (디버깅용):

```bash
python -m collectors.price_collector
python -m collectors.dart_collector
python -m collectors.news_collector
python -m analysis.model
python -m analysis.compare_sentiment
python -m combined_signal.combine
python -m reports.generate_report
```

## 데이터 저장 구조 (SQLite)

서버 설치 없이 바로 append 가능하고, 필요 시 Postgres로 스키마 그대로 이관 가능해서 SQLite를 사용.
전체 스키마는 [db/schema.sql](db/schema.sql) 참고. 테이블 4개:

- `stock_price` — 일별 OHLCV, `(ticker, trade_date)` UNIQUE로 중복 수집 방지
- `disclosure` — OpenDART 공시 목록, `(corp_code, report_name, report_date)` UNIQUE
- `news` — 뉴스 제목/본문(og:description)/URL + 규칙기반·LLM 감정점수, `url` UNIQUE
- `prediction_log` — 예측모델 실행 이력 (모델명, 예측값, 실측값, RMSE)

## 파이프라인 구조

```
수집 (yfinance/OpenDART/Selenium)
  → 정규식 정제 + Kiwi 형태소분석 기반 규칙기반 감정점수화
  → SQLite 저장 (append, UNIQUE 제약으로 중복 방지)
  → [scheduled 모드] 여기서 종료 (로그만 남김)
  → [manual 모드] EDA/파생변수 → scikit-learn 예측모델 학습·추론
                 → Ollama 로컬 LLM 감정점수화 (규칙기반과 병렬 비교)
                 → 가격신호+감정신호 결합 프로토타입
                 → Streamlit 대시보드용 데이터 갱신 + 마크다운 리포트 생성
                 → METRICS.md 갱신 → git commit
```

## 프로젝트 구조

```
config.py                 # TICKER 등 설정값 (하드코딩 금지, .env에서 로드)
db/                        # SQLite 스키마 + 연결/insert 헬퍼
collectors/                # price/dart/news 수집기 (naver_selectors.py에 CSS 셀렉터 상수 분리)
nlp/                        # 정규식 정제, Kiwi 규칙기반 감정사전, Ollama LLM 감정 프롬프트
analysis/                  # 파생변수, scikit-learn 모델, 규칙기반 vs LLM 비교
combined_signal/           # 가격예측 + 감정신호 결합 프로토타입
dashboard/                 # Streamlit 대시보드
reports/                   # 마크다운 리포트 생성 + METRICS.md 자동 갱신
scheduler/                 # APScheduler 기반 일 1회 자동 수집
scripts/run_pipeline.py    # 전체 진입점 (scheduled/manual 분기)
```

## 알려진 한계

[PROGRESS.md](PROGRESS.md)의 "알려진 한계" 섹션 참고 — 뉴스 본문은 전체 크롤링이 아닌
`og:description` 메타 태그 기반이고, Naver 검색 마크업은 구조 변경에 취약하며, 예측모델은
소규모 데이터(n<50)로 baseline을 넘지 못한다는 점을 숨기지 않고 기록해 둔다.
