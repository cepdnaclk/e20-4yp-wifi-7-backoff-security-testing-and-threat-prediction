# GNN Attack Detection System - Comprehensive Documentation

## Executive Summary

The Graph Neural Network (GNN) attack detection system in `twin/gnn/` implements a deep learning approach to detect Wi-Fi 7 Multi-Link Operation (MLO) backoff manipulation attacks. The system uses a Graph Convolutional Network (GCN) to classify network behavior into three categories: Normal, Positive Bias Attack, and Negative Bias Attack.

**Key Capabilities:**
- Multi-class classification (3 classes)
- Graph-based temporal modeling of network metrics
- Support for two graph topology strategies (chain and k-NN)
- Feature normalization and class balancing
- Early stopping and model checkpointing

---

## System Architecture

### Component Overview

```
twin/gnn/
├── backoff_dataset.py     # Data loading, graph construction, feature extraction
├── attack_model.py        # GCN model architecture
├── train_attack.py        # Training pipeline with evaluation
└── eval.py                # (Empty - evaluation integrated in train_attack.py)
```

### Data Flow Pipeline

```
JSON Files (telemetry data)
    ↓
[backoff_dataset.py: load_json()]
    ↓
Window-based metrics (list of dicts)
    ↓
[make_samples(): Feature extraction + Graph construction]
    ↓
GraphSample objects (A, X, y)
    ↓
[Feature scaling: StandardScaler]
    ↓
[train_attack.py: Training loop]
    ↓
AttackGCN model predictions
    ↓
Classification outputs (0, 1, or 2)
```

---

## Data Processing Pipeline

### 1. Input Data Format

**Source:** JSON files containing window-based network telemetry metrics

**Expected Structure:**
```json
[
  {
    "window": 0,
    "bias": 0.0,
    "net_throughput_mbps": 54.2,
    "net_avg_delay_ms": 12.3,
    "net_avg_jitter_ms": 2.1,
    "net_packet_loss_ratio": 0.01,
    "net_active_flows": 5,
    "mac_total_tx": 1024,
    "mac_total_rx": 980,
    "mac_total_ack": 950,
    "mac_total_retrans": 30,
    "mac_drop_count": 20,
    "phy_drop_count": 5,
    "avg_backoff_slots": 15.7,
    "channel_busy_ratio": 0.35
  },
  ...
]
```

**File Organization:**
- `data/normal/*.json` → Label 0 (Normal)
- `data/attack/*positive*.json` → Label 1 (Positive Bias Attack)
- `data/attack/*negative*.json` → Label 2 (Negative Bias Attack)

### 2. Feature Extraction

**14-Dimensional Feature Vector** (defined in `backoff_dataset.py:11-26`):

| Index | Feature Name | Description |
|-------|--------------|-------------|
| 0 | `bias` | Backoff bias value |
| 1 | `net_throughput_mbps` | Network throughput (Mbps) |
| 2 | `net_avg_delay_ms` | Average packet delay (ms) |
| 3 | `net_avg_jitter_ms` | Average jitter (ms) |
| 4 | `net_packet_loss_ratio` | Packet loss ratio [0-1] |
| 5 | `net_active_flows` | Number of active flows |
| 6 | `mac_total_tx` | Total MAC layer transmissions |
| 7 | `mac_total_rx` | Total MAC layer receptions |
| 8 | `mac_total_ack` | Total acknowledgments |
| 9 | `mac_total_retrans` | Total retransmissions |
| 10 | `mac_drop_count` | MAC layer packet drops |
| 11 | `phy_drop_count` | Physical layer packet drops |
| 12 | `avg_backoff_slots` | Average backoff slots |
| 13 | `channel_busy_ratio` | Channel busy ratio [0-1] |

**Feature Preprocessing:**
- Missing values → 0.0
- NaN/Inf values → 0.0 (via `np.nan_to_num()`)
- Normalization: StandardScaler (mean=0, std=1) fit on training set

### 3. Graph Construction

The system converts temporal window sequences into graph structures where:
- **Nodes** = Time windows (each window is a node with 14-dim features)
- **Edges** = Relationships between windows (topology-dependent)
- **Graph** = Represents temporal evolution of network behavior

#### 3.1 Chain Topology (`_make_chain_topology`)

**Strategy:** Sequential temporal connections
```
Window 0 ↔ Window 1 ↔ Window 2 ↔ ... ↔ Window N
   ↓          ↓          ↓              ↓
  self      self       self           self
```

**Adjacency Matrix Construction:**
1. Connect consecutive windows: `A[i, i+1] = A[i+1, i] = 1.0`
2. Add self-loops: `A[i, i] = 1.0`
3. Normalize: `D^(-1/2) * A * D^(-1/2)` (symmetric normalization)

**Use Case:** Simple temporal dependencies, computationally efficient

#### 3.2 k-NN Topology (`_make_knn_topology`)

**Strategy:** Feature similarity-based connections

**Algorithm:**
1. Scale features using StandardScaler
2. Compute k-nearest neighbors based on Euclidean distance
3. Convert distances to similarity weights: `weight = 1 / (distance + ε)`
4. Make symmetric: `A = max(A, A^T)`
5. Add self-loops and normalize

**Parameters:**
- `k=5` (default): Each node connects to 5 most similar nodes
- Fallback: Fully connected graph if N ≤ k

**Use Case:** Captures complex temporal patterns and non-sequential dependencies

### 4. Sliding Window Graph Generation

**Configuration** (in `train_attack.py:888-891`):
```python
GRAPH_LEN = 32    # Number of windows per graph
STRIDE = 8        # Sliding window stride
TOPOLOGY = 'knn'  # Topology type
K_NEIGHBORS = 5   # k for k-NN
```

**Example:**
```
File with 100 windows → Generated graphs:
- Graph 1: Windows [0:32]
- Graph 2: Windows [8:40]
- Graph 3: Windows [16:48]
...
Total: ⌊(100 - 32) / 8⌋ + 1 = 9 graphs
```

### 5. GraphSample Data Structure

**Definition** (`backoff_dataset.py:31-36`):
```python
@dataclass
class GraphSample:
    A: np.ndarray   # [N, N] normalized adjacency matrix
    X: np.ndarray   # [N, 14] node feature matrix
    y: int          # Class label (0, 1, or 2)
    meta: dict      # Metadata (debug info, window ranges)
```

---

## Model Architecture: AttackGCN

### Model Definition (`attack_model.py:5-31`)

```python
class AttackGCN(nn.Module):
    Input: A [N,N], X [N,14]
    Output: logits [3]
```

### Architecture Layers

```
Input Layer:
  A: [N, N] - Adjacency matrix
  X: [N, 14] - Node features

↓

GCN Layer 1:
  H = A @ X              # Graph convolution
  H = Linear(14 → 32)    # Transform
  H = ReLU(H)            # Activation
  Output: [N, 32]

↓

GCN Layer 2:
  H = A @ H              # Graph convolution
  H = Linear(32 → 32)    # Transform
  H = ReLU(H)            # Activation
  Output: [N, 32]

↓

Global Pooling:
  g = mean(H, dim=0)     # Average all nodes
  Output: [32]

↓

Classification Layer:
  logits = Linear(32 → 3)
  Output: [3] class logits
```

### Key Design Choices

1. **Two-Layer GCN**: Balances expressiveness vs. over-smoothing
2. **Mean Pooling**: Graph-level representation from node features
3. **Hidden Dimension**: 32 (tunable parameter)
4. **No Dropout**: Current implementation (can add for regularization)

### Forward Pass Example

```python
# Input graph with 32 windows (nodes)
A = torch.tensor(adjacency, shape=[32, 32])
X = torch.tensor(features, shape=[32, 14])

# Forward pass
logits = model(A, X)  # Shape: [3]

# Prediction
pred_class = torch.argmax(logits)  # 0, 1, or 2
```

---

## Training Pipeline

### Training Configuration (`train_attack.py:887-891, 956-958`)

```python
HYPERPARAMETERS = {
    'graph_len': 32,
    'stride': 8,
    'topology': 'knn',
    'k_neighbors': 5,
    'hidden_dim': 32,
    'learning_rate': 0.001,
    'max_epochs': 150,
    'batch_size': 1,  # Per-graph training
    'patience': 10,   # Early stopping
    'min_delta': 0.001
}
```

### Data Splitting Strategy

**Per-File Split** (`train_attack.py:818-847`):
```python
def process_and_split_file(path, label, ...):
    # Load windows from ONE file
    windows = load_json(path)

    # Generate graphs from windows
    file_samples = make_samples(windows, label, ...)

    # Split THIS file's samples 80/20
    cut_idx = int(len(file_samples) * 0.8)
    train_part = file_samples[:cut_idx]
    test_part = file_samples[cut_idx:]

    return train_part, test_part
```

**Global Split:**
- Training: 80% of samples from each file
- Test: 20% of samples from each file
- Validation: 80/20 split of training set → Final: 64% train / 16% val / 20% test

### Class Imbalance Handling (`train_attack.py:924-938`)

**Oversampling Strategy:**
```python
class_counts = {0: 500, 1: 200, 2: 150}  # Example
max_count = 500

# Oversample minority classes to match majority
for class_i in [0, 1, 2]:
    class_samples = [s for s in train if s.y == class_i]
    oversampled = random.choice(class_samples, size=max_count, replace=True)
    balanced_train.extend(oversampled)

# Result: {0: 500, 1: 500, 2: 500}
```

### Training Loop (`train_attack.py:971-1027`)

```python
for epoch in range(1, 151):
    # TRAINING PHASE
    model.train()
    for sample in train_samples:
        A, X, y = sample.A, sample.X, sample.y
        logits = model(A, X)
        loss = CrossEntropyLoss(logits, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    # VALIDATION PHASE
    model.eval()
    val_loss, correct = 0, 0
    for sample in val_samples:
        logits = model(A, X)
        pred = argmax(logits)
        correct += (pred == y)

    val_accuracy = correct / len(val_samples)

    # EARLY STOPPING
    if val_loss < best_val_loss - min_delta:
        best_val_loss = val_loss
        save_checkpoint(model)
        epochs_no_improve = 0
    else:
        epochs_no_improve += 1

    if epochs_no_improve >= patience:
        break  # Stop training
```

### Loss Function

**CrossEntropyLoss** for multi-class classification:
```python
loss = nn.CrossEntropyLoss()
# Input: logits [3]
# Target: class_index (0, 1, or 2)
```

### Optimizer

**Adam Optimizer:**
- Learning rate: 0.001 (reduced from 0.01 for stability)
- No weight decay (current implementation)

---

## Model Output and Predictions

### Prediction Process

```python
# During inference
model.eval()
with torch.no_grad():
    A = torch.tensor(adjacency, dtype=torch.float32)
    X = torch.tensor(features, dtype=torch.float32)

    logits = model(A, X)  # [3] raw scores

    # Get class prediction
    pred_class = torch.argmax(logits, dim=0).item()

    # Get class probabilities (optional)
    probs = torch.softmax(logits, dim=0)
    # probs[0] = P(Normal)
    # probs[1] = P(Positive Attack)
    # probs[2] = P(Negative Attack)
```

### Output Classes

| Class ID | Label | Meaning |
|----------|-------|---------|
| 0 | Normal | No attack detected |
| 1 | Positive Attack | Positive bias backoff manipulation |
| 2 | Negative Attack | Negative bias backoff manipulation |

### Label Extraction Logic (`train_attack.py:801-816`)

```python
def get_label_from_filename(path):
    filename = Path(path).name.lower()

    if "normal" in filename:
        return 0
    elif "negative" in filename:
        return 2
    elif "positive" in filename:
        return 1
    else:
        return 1  # Default to positive if unclear
```

---

## Evaluation Metrics

### Metrics Computed (`train_attack.py:849-885`)

1. **Accuracy**: Overall correct predictions / total predictions
2. **Confusion Matrix**: True vs. Predicted class distribution
3. **Classification Report**:
   - Precision per class
   - Recall per class
   - F1-Score per class
   - Support (sample count per class)

### Example Output

```
==================== Final Test Set Results ====================

--- Confusion Matrix ---
[[95  3  2]   # True Normal: 95 correct, 3 as Positive, 2 as Negative
 [ 4 88  8]   # True Positive: 4 as Normal, 88 correct, 8 as Negative
 [ 2  5 93]]  # True Negative: 2 as Normal, 5 as Positive, 93 correct

--- Detailed Classification Report ---
                    precision  recall  f1-score  support
Normal                0.9406   0.9500   0.9453      100
Positive Attack       0.9167   0.8800   0.8980      100
Negative Attack       0.9029   0.9300   0.9162      100

accuracy                                 0.9200      300
```

### Training Visualization (`train_attack.py:1034-1080`)

**Plots Generated:**
- Training Loss (raw + smoothed)
- Validation Loss (raw + smoothed)
- Validation Accuracy (raw + smoothed)

**Smoothing:** Exponential Moving Average (α=0.8)

**Output:** `GNN/artifacts/training_metrics.png`

---

## Model Artifacts

### Saved Files

**Location:** `GNN/artifacts/`

1. **Model Weights:**
   - `attack_gnn_v2_large_datasetV2.pt`
   - PyTorch state_dict containing trained parameters

2. **Scaler Parameters:**
   - `attack_gnn_v2_large_datasetV2.json`
   - Contains mean and std for feature normalization
   ```json
   {
     "mean": [0.0, 54.2, 12.3, ...],  # 14 values
     "std": [1.0, 15.7, 3.2, ...]     # 14 values
   }
   ```

3. **Training Metrics Plot:**
   - `training_metrics.png`
   - Visual summary of training progress

### Loading Trained Model

```python
import torch
from attack_model import AttackGCN

# Initialize model
model = AttackGCN(in_dim=14, hidden=32, n_classes=3)

# Load weights
model.load_state_dict(torch.load('GNN/artifacts/attack_gnn_v2_large_datasetV2.pt'))
model.eval()

# Load scaler
with open('GNN/artifacts/attack_gnn_v2_large_datasetV2.json') as f:
    scaler_params = json.load(f)
    mean = np.array(scaler_params['mean'])
    std = np.array(scaler_params['std'])
```

---

## Integration with Telemetry Pipeline

### Current Data Source

**Status:** Manual data loading from JSON files

**Expected Location:**
- `data/normal/*.json` (normal behavior)
- `data/attack/*.json` (attack scenarios)

### Potential Integration Points

1. **Real-time Detection:**
   ```
   TimescaleDB → Query windows → make_samples() → Model inference → Alert
   ```

2. **Batch Processing:**
   ```
   Harmonizer → Store in DB → Periodic GNN evaluation → Dashboard
   ```

3. **Feature Alignment:**
   - Ensure ns-3 telemetry exports match 14-feature schema
   - Map harmonizer output to GNN input format

### Data Requirements

**Minimum for One Graph:**
- At least 32 time windows (with `GRAPH_LEN=32`)
- All 14 features populated (missing values → 0.0)
- Consistent window indexing (`"window": <int>`)

---

## Limitations and Considerations

### Current Limitations

1. **No Real-time Integration:**
   - Model operates on pre-collected JSON files
   - Not connected to live telemetry pipeline

2. **Fixed Graph Size:**
   - `GRAPH_LEN=32` is hardcoded
   - Variable-length sequences require padding or batching

3. **No Batch Training:**
   - Trains one graph at a time
   - Could benefit from mini-batch gradient descent

4. **CPU-Only:**
   - No GPU acceleration implemented
   - `device = "cpu"` hardcoded

5. **Binary Attack Detection:**
   - Assumes clean labels (normal vs. attack)
   - No handling of mixed or transitional states

### Scalability Considerations

1. **Memory:**
   - k-NN graph construction: O(N²) space for adjacency matrix
   - Large N (>1000 windows) may cause memory issues

2. **Computation:**
   - k-NN search: O(N² * F) time
   - GCN forward pass: O(N² * hidden_dim)

3. **Data Loading:**
   - No data caching
   - Re-loads JSON files every training run

### Robustness Issues

1. **Feature Imputation:**
   - Missing values → 0.0 (simple but potentially biased)
   - No sophisticated imputation strategy

2. **Outliers:**
   - No outlier detection or clipping
   - StandardScaler sensitive to extreme values

3. **Class Imbalance:**
   - Oversampling may cause overfitting
   - No class weights in loss function

---

## Recommendations for Improvement

### Short-term Enhancements

1. **Add Batch Training:**
   ```python
   # Use PyTorch Geometric batching
   from torch_geometric.data import Batch
   batch = Batch.from_data_list([graph1, graph2, ...])
   ```

2. **Implement Dropout:**
   ```python
   self.dropout = nn.Dropout(p=0.5)
   H = self.dropout(F.relu(self.fc1(H)))
   ```

3. **Add Model Checkpointing:**
   - Save best model during training
   - Load best model for final evaluation

4. **Logging:**
   - Use TensorBoard or wandb for experiment tracking
   - Log hyperparameters, metrics, and artifacts

### Long-term Improvements

1. **Pipeline Integration:**
   - Connect to TimescaleDB for real-time data
   - Implement streaming inference service
   - Add Grafana dashboard for GNN predictions

2. **Advanced Architectures:**
   - Graph Attention Networks (GAT)
   - Temporal Graph Networks (TGN)
   - Graph Transformers

3. **Multi-task Learning:**
   - Jointly predict attack type and severity
   - Add auxiliary tasks (e.g., throughput prediction)

4. **Explainability:**
   - Implement GNNExplainer for feature importance
   - Visualize attention weights (if using GAT)
   - Generate counterfactual explanations

5. **Distributed Training:**
   - Multi-GPU support with PyTorch DDP
   - Larger batch sizes for better gradient estimates

---

## Usage Example

### Training a Model

```bash
cd twin/gnn

# Ensure data is in correct folders
ls data/normal/*.json
ls data/attack/*.json

# Run training
python train_attack.py
```

**Output:**
```
Processing 50 Normal files and 100 Attack files...
Using graph topology: knn with k=5
Initial training set class counts: {0: 500, 1: 800, 2: 600}
After oversampling, training set has 2400 samples.
Final Dataset: 1920 Training, 480 Validation, 450 Test

Starting Training...
Epoch 01 | Avg Train Loss: 0.8432 | Avg Val Loss: 0.7123 | Val Acc: 0.6750
Epoch 02 | Avg Train Loss: 0.6789 | Avg Val Loss: 0.5891 | Val Acc: 0.7542
...
Early stopping triggered at epoch 45. Best validation loss: 0.2134

==================== Final Test Set Results ====================
...
accuracy: 0.9156

Saved clean training metrics plot to: GNN/artifacts/training_metrics.png
Saved model to: GNN/artifacts/attack_gnn_v2_large_datasetV2.pt
```

### Inference Example

```python
import json
import numpy as np
import torch
from backoff_dataset import make_samples, load_json
from attack_model import AttackGCN

# Load model and scaler
model = AttackGCN(in_dim=14, hidden=32, n_classes=3)
model.load_state_dict(torch.load('GNN/artifacts/attack_gnn_v2_large_datasetV2.pt'))
model.eval()

with open('GNN/artifacts/attack_gnn_v2_large_datasetV2.json') as f:
    scaler = json.load(f)
    mean, std = np.array(scaler['mean']), np.array(scaler['std'])

# Load and preprocess data
windows = load_json('data/test/new_scenario.json')
samples = make_samples(windows, label=0, graph_len=32, stride=8, topology='knn', k=5)

# Scale features
for s in samples:
    s.X = ((s.X - mean) / std).astype(np.float32)

# Predict
predictions = []
with torch.no_grad():
    for s in samples:
        A = torch.tensor(s.A, dtype=torch.float32)
        X = torch.tensor(s.X, dtype=torch.float32)
        logits = model(A, X)
        pred = torch.argmax(logits).item()
        predictions.append(pred)

# Majority vote
final_prediction = max(set(predictions), key=predictions.count)
class_names = ['Normal', 'Positive Attack', 'Negative Attack']
print(f"Prediction: {class_names[final_prediction]}")
```

---

## Conclusion

The GNN attack detection system provides a robust framework for identifying Wi-Fi 7 MLO backoff manipulation attacks using temporal graph modeling. The current implementation demonstrates strong performance on pre-collected data and is ready for integration into the larger telemetry pipeline.

**Next Steps:**
1. Integrate with TimescaleDB telemetry data
2. Implement real-time inference service
3. Add Grafana dashboard for attack visualization
4. Explore advanced GNN architectures (GAT, TGN)

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Author:** Claude Code (automated documentation)
**Related Files:** `twin/gnn/*.py`, `docs/BLUEPRINT.md`, `docs/CURRENT-STATE.md`
