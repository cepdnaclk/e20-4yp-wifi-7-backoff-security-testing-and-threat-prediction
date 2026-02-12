# Windowizer Service Dockerfile
# WP8 Phase 2: Window aggregation service

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY *.py ./
COPY config.yaml ./

# Make windowizer.py executable
RUN chmod +x windowizer.py

# Run as non-root user
RUN useradd -m -u 1000 windowizer && \
    chown -R windowizer:windowizer /app
USER windowizer

# Health check (placeholder - will add HTTP endpoint in future)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep -f windowizer.py || exit 1

# Run windowizer
CMD ["python", "windowizer.py", "/app/config.yaml"]
