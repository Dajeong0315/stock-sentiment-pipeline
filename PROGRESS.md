# PROGRESS

마지막 갱신: 2026-09-07

## MVP 체크리스트
- [x] 수집 스크립트가 3개 소스 각각 정상 실행되어 SQLite에 새 row가 append됨
  - 주가(yfinance): 동작 확인 (64건)
  - 뉴스(Naver 검색, Selenium): 동작 확인 (24건, 규칙기반 점수화 포함)
  - 공시(OpenDART): 동작 확인 (실제 API 키로 삼성전자 공시 18건 수집, corp_code=00126380 정확성 확인됨)
- [x] 규칙기반 감정점수화가 뉴스 텍스트에 대해 정상 동작함 (정규식 정제 + Kiwi 형태소분석 + 수작업 사전)
- [x] 예측모델이 에러 없이 학습·추론 완료되고 RMSE가 METRICS.md에 기록됨 (Ridge/RandomForest, baseline 대비 결과는 METRICS.md 참고)
- [x] Ollama 로컬 LLM(Qwen2.5-3B-Instruct, 4bit)이 뉴스 텍스트에 대해 감정점수를 반환하고, 규칙기반과의 비교표/차트가 생성됨 (일치율 54.2%, n=24)
- [x] 결합 프로토타입이 하나의 종합 시그널을 산출함 (`combined_signal/combine.py`)
- [x] Streamlit 대시보드가 로컬에서 구동되어 최신 데이터를 반영함
- [x] 마크다운 리포트가 최신 실행 결과로 자동 갱신됨 (`reports/output/latest_report.md`)
- [x] METRICS.md, PROGRESS.md 존재 및 최신 상태 — PORTFOLIO_NOTES.md는 MVP 완료 후 1차 작성 예정
- [x] 매 실행마다 git commit 로그가 남음 (`scripts/run_pipeline.py`가 manual 모드에서 자동 커밋)

## 남은 작업 (MVP 마무리)
전부 완료. 남은 것은 선택사항: `scheduler/daily_job.py`를 실제로 장시간 띄워 매일 08:00
자동 수집이 실행되는지는 로컬에서 사용자가 직접 확인 필요 (모듈 임포트와 job 함수 단발
실행은 검증됨).

완료됨: 3개 소스 전부 실제 API/사이트로 수집 검증, PORTFOLIO_NOTES.md 1차 작성,
`--mode scheduled`/`--mode manual` 양쪽 실행 검증, Streamlit 대시보드 브라우저 렌더링 확인,
GitHub 원격 저장소(https://github.com/Dajeong0315/stock-sentiment-pipeline) 연결 및 push 완료.

## 확장 범위 진행 상태 (MVP 완료 전에는 착수하지 않음)
- [ ] Docker 컨테이너화 — 미착수
- [ ] Kubernetes 매니페스트 — 미착수
- [ ] GitHub Actions CI — 미착수
- [ ] KcELECTRA 파인튜닝 비교 — 미착수
- [ ] GPU 확보 시 7B급 모델 교체 — 미착수 (해당 없음, CPU 전용 환경)
- [ ] PDF 리포트 내보내기 — 미착수
- [ ] Slack/이메일 알림 — 미착수
- [ ] 다른 종목으로 TICKER 교체 재사용성 검증 — 미착수

## 알려진 한계 (정직하게 기록)
- 뉴스 수집은 Naver 검색 결과 페이지의 제목 + 기사 자체 페이지의 `og:description` 메타 태그를 사용함 (전체 본문 크롤링 아님) — 언론사별 파서를 만들지 않는 대신 선택한 견고성 우선 설계
- Naver 검색 결과 마크업은 빌드마다 해시된 CSS 클래스를 사용해 불안정함 — `data-sds-comp="Profile"` 속성 기반으로 추출하도록 구현했으나, Naver가 이 속성 자체를 바꾸면 `collectors/naver_selectors.py`부터 다시 점검해야 함
- 가격 예측모델은 3개월치 일별 데이터(n<50)로 학습해 RMSE가 baseline을 넘지 못함 — 데이터가 누적되면 재평가 필요
