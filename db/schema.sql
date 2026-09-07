CREATE TABLE IF NOT EXISTS stock_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume INTEGER,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS disclosure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    corp_code TEXT NOT NULL,
    report_name TEXT,
    report_date DATE NOT NULL,
    report_type TEXT,
    raw_summary TEXT,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(corp_code, report_name, report_date)
);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    news_date DATE NOT NULL,
    title TEXT,
    content TEXT,
    url TEXT UNIQUE,
    rule_sentiment_score REAL,
    llm_sentiment_score REAL,
    llm_model_used TEXT,
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    predict_date DATE NOT NULL,
    model_name TEXT,
    predicted_value REAL,
    actual_value REAL,
    metric_rmse REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
