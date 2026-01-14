# Project Overview and Methodology

## 1. Goal

The primary goal of this project is to detect anomalous behavior in a system by analyzing event sequences. The system classifies behavior into three categories:

1.  **Normal:** Represents standard, non-malicious system operation.
2.  **Positive Bias Attack:** Represents a specific type of anomalous behavior.
3.  **Negative Bias Attack:** Represents a second type of anomalous behavior.

The project leverages Graph Neural Networks (GNNs) to learn the complex relationships and temporal dependencies within event data to identify these patterns.

## 2. Methodology: Graph-Based Event Analysis

The core methodology is to represent sequences of system events as graphs and use a Graph Convolutional Network (GCN) to classify them.

### 2.1. Graph Construction

Each dataset instance (a sequence of events) is transformed into a graph:

-   **Nodes (N):** Each node in the graph represents a "window" or a specific moment in time containing a collection of events.
-   **Node Features (X):** Each node has a 14-dimensional feature vector. This vector is derived from the raw event data through a feature engineering process, capturing the state of the system within that window.
-   **Edges (A):** The adjacency matrix `A` represents the relationships between these time windows. In this model, it appears to represent the temporal flow, connecting adjacent time windows.

### 2.2. Model Architecture

The project uses a custom GCN model named `AttackGCN`:

-   **Input:** The model takes the normalized adjacency matrix `A` and the node feature matrix `X` as input.
-   **GCN Layers:** It consists of two GCN layers. Each layer aggregates information from a node's neighbors, allowing the model to learn relationships between different time windows.
    -   *Layer 1:* Performs the first round of message passing.
    -   *Layer 2:* Performs a second round of message passing on the output of the first layer, capturing more complex, higher-order relationships.
-   **Graph Pooling:** After the GCN layers, a graph pooling operation (mean pooling) is applied. This aggregates all the node information into a single vector that represents the entire graph (the entire sequence of events).
-   **Classification:** A final fully-connected linear layer acts as a classifier, taking the graph representation and producing logits for the three output classes (Normal, Positive Attack, Negative Attack).

### 2.3. Training and Evaluation

-   **Training:** The model is trained using a standard supervised learning approach with an Adam optimizer and Cross-Entropy Loss function. It learns to minimize the difference between its predictions and the true labels from the training data.
-   **Evaluation:** The model's performance is assessed using standard classification metrics, including accuracy, precision, recall, and F1-score, providing a comprehensive view of its ability to correctly identify each class of behavior.
