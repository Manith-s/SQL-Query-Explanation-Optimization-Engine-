# SQL Query Explanation & Optimization Engine
# Dockerfile for containerized deployment
#
# This is a placeholder Dockerfile for Phase 0.
# Will be enhanced in future phases for production deployment.

FROM python:3.11-slim AS builder
WORKDIR /w
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip build && python -m build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=src \
    QEO_LOG_FORMAT=json \
    CORS_ALLOW_ORIGINS=* \
    OPT_TIMEOUT_MS_DEFAULT=10000

RUN useradd -ms /bin/bash appuser
WORKDIR /app
COPY --from=builder /w/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl
COPY src ./src

EXPOSE 8000
USER appuser
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',8000)); print('ok')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
