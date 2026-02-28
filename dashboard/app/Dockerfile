# ── Stage 1: Build React frontend ─────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent

COPY frontend/ .
RUN npm run build

# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy built frontend into static/
COPY --from=frontend-build /build/frontend/dist ./static/

# Copy model registry (read-only at runtime)
# The registry is volume-mounted at runtime; this COPY is just a fallback placeholder.
RUN mkdir -p /registry

ENV PG_HOST=localhost \
    PG_PORT=5432 \
    PG_DB=udr \
    PG_USER=udr \
    PG_PASS=udr_pass \
    REGISTRY_PATH=/registry \
    PORT=8888

EXPOSE 8888

CMD ["python", "-m", "uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8888", \
     "--workers", "1"]
