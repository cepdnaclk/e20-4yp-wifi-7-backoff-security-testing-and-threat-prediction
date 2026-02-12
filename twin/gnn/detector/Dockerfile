FROM python:3.11-slim

# Install system dependencies for PyTorch Geometric
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r detector && useradd -r -g detector -u 1000 detector

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install NumPy 1.x (required for PyTorch Geometric compatibility)
RUN pip install --no-cache-dir "numpy<2.0"

# Install PyTorch CPU version (smaller image)
RUN pip install --no-cache-dir torch==2.0.0+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Install PyTorch Geometric and dependencies
RUN pip install --no-cache-dir torch-geometric==2.3.0
RUN pip install --no-cache-dir \
    torch-scatter==2.1.1+pt20cpu \
    torch-sparse==0.6.17+pt20cpu \
    torch-cluster==1.6.1+pt20cpu \
    torch-spline-conv==1.2.2+pt20cpu \
    -f https://data.pyg.org/whl/torch-2.0.0+cpu.html

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY --chown=detector:detector . .

# Switch to non-root user
USER detector

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health').raise_for_status()" || exit 1

# Run detector service
CMD ["python", "-u", "detector.py", "/app/config.yaml"]
