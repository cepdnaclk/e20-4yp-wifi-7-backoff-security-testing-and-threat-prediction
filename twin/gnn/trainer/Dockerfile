FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install NumPy 1.x for PyTorch Geometric compatibility
RUN pip install --no-cache-dir "numpy<2.0"

# Install PyTorch Geometric and sparse dependencies for CUDA 12.1
RUN pip install --no-cache-dir torch-geometric==2.5.3
RUN pip install --no-cache-dir \
    torch-scatter \
    torch-sparse \
    torch-cluster \
    -f https://data.pyg.org/whl/torch-2.3.0+cu121.html

# Install remaining dependencies
RUN pip install --no-cache-dir \
    scikit-learn>=1.3.0 \
    pyyaml>=6.0 \
    tqdm>=4.65.0 \
    matplotlib>=3.7.0 \
    seaborn>=0.12.0

# Copy GCN source from detector (training code lives there)
COPY gcn_src/ /app/gcn_src/
COPY run_training.py /app/run_training.py
COPY run_training_v4.py /app/run_training_v4.py

# Default entrypoint (v3). Override with --entrypoint for v4.
ENTRYPOINT ["python", "-u", "run_training.py"]
