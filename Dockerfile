FROM python:3.11-slim

# Install chromium system dependencies
RUN apt-get update && apt-get install -y \
    libxkbcommon0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    libxss1 \
    libxcb1 \
    libx11-xcb1 \
    fontconfig \
    fonts-liberation \
    libasound2t64 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libgbm1 \
    libdrm2 \
    libgl1 \
    libegl1 \
    wget \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium

# Verify no missing libs
# RUN ldd /ms-playwright/chromium-*/chrome-linux/chrome | grep "not found" \
#     && echo "WARNING: missing libs!" || echo "All libs OK"

# ✅ Now using the correct paths
RUN echo "=== Checking chrome ===" && \
    ldd /ms-playwright/chromium-1208/chrome-linux64/chrome | grep "not found" \
    && echo "WARNING: chrome has missing libs!" || echo "chrome: All libs OK"

RUN echo "=== Checking chrome-headless-shell ===" && \
    ldd /ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell | grep "not found" \
    && echo "WARNING: headless-shell has missing libs!" || echo "chrome-headless-shell: All libs OK"

# Copy source code
COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "function_2:app"]