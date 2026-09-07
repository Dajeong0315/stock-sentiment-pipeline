FROM python:3.13-slim

# Selenium needs an actual Chromium binary + matching driver, not just the pip package
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*
ENV CHROME_BIN=/usr/bin/chromium

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Overridden per-service in docker-compose.yml (dashboard vs scheduler)
CMD ["streamlit", "run", "dashboard/app.py", "--server.address", "0.0.0.0"]
