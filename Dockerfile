# ============= Dockerfile =============
# Multi-stage build for FastAPI Finance Monitor

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /root/.local /root/.local

# Update PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app/ ./app

# Create non-privileged user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health', timeout=5)"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ============= docker-compose.yml =============
# Создайте отдельный файл docker-compose.yml с содержимым:

# version: '3.8'
# 
# services:
#   finance-monitor:
#     build: .
#     container_name: fastapi-finance-monitor
#     ports:
#       - "8000:8000"
#     environment:
#       - HOST=0.0.0.0
#       - PORT=8000
#       - UPDATE_INTERVAL=30
#       - LOG_LEVEL=INFO
#     restart: unless-stopped
#     healthcheck:
#       test: ["CMD", "curl", "-f", "http://localhost:8000"]
#       interval: 30s
#       timeout: 10s
#       retries: 3
#       start_period: 40s
#     networks:
#       - finance-network
# 
#   # Опционально: Redis для кэширования
#   redis:
#     image: redis:7-alpine
#     container_name: finance-monitor-redis
#     ports:
#       - "6379:6379"
#     volumes:
#       - redis-data:/data
#     restart: unless-stopped
#     networks:
#       - finance-network
# 
# networks:
#   finance-network:
#     driver: bridge
# 
# volumes:
#   redis-data:


# ============= .dockerignore =============
# Создайте файл .dockerignore:

# __pycache__
# *.pyc
# *.pyo
# *.pyd
# .Python
# venv/
# ENV/
# env/
# .env
# .env.local
# .git
# .gitignore
# .vscode
# .idea
# *.log
# *.csv
# *.db
# README.md
# docs/
# tests/


# ============= Инструкции по использованию =============

# 1. Сборка образа:
# docker build -t fastapi-finance-monitor .

# 2. Запуск контейнера:
# docker run -d -p 8000:8000 --name finance-monitor fastapi-finance-monitor

# 3. Запуск с docker-compose:
# docker-compose up -d

# 4. Просмотр логов:
# docker logs -f finance-monitor

# 5. Остановка:
# docker-compose down

# 6. Перезапуск:
# docker-compose restart

# 7. Обновление:
# docker-compose down
# docker-compose build --no-cache
# docker-compose up -d
