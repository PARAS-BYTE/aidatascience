# ============================================================
# Multi-Stage Production Dockerfile for AI Data Science Platform
# Builds React Frontend + FastAPI Backend + ML Engine
# Compatible with: Hugging Face Spaces (Port 7860), Render, Railway, Cloud VPS
# ============================================================

# Stage 1: Build React 18 TypeScript Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.11 Backend & ML Runtime
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend:/app

# Install native dependencies for DuckDB, scikit-learn, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python ML & backend requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application and ML engine
COPY backend /app/backend
COPY ml_engine /app/ml_engine
COPY data /app/data
COPY models /app/models

# Copy built React frontend into /app/frontend/dist
# FastAPI automatically serves this at root '/'
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Default persistent directories
ENV UPLOAD_DIR=/app/data/uploads
ENV PROCESSED_DIR=/app/data/processed
ENV RESULTS_DIR=/app/data/results
ENV MODEL_DIR=/app/models/artifacts
ENV ENVIRONMENT=production

# Expose Hugging Face Spaces default port (7860) and standard (8000)
EXPOSE 7860 8000

# Start Uvicorn: binds to $PORT if set (Render/Railway), otherwise 7860 (Hugging Face)
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-7860}"]
