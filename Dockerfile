# SQL Query Explanation & Optimization Engine
# Dockerfile for containerized deployment
#
# This is a placeholder Dockerfile for Phase 0.
# Will be enhanced in future phases for production deployment.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check (placeholder)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (placeholder)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# TODO: Add production optimizations in future phases:
# - Multi-stage build
# - Non-root user
# - Security hardening
# - Performance tuning
