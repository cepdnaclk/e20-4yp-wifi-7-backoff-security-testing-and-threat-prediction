"""
Graph Convolutional Network (GCN) model for WiFi 7 backoff attack detection.

This module implements the WiFi7AttackGCN model that performs graph-level
binary classification (Attack vs Normal) on temporal window graphs.

Model Architecture:
1. GCN Layers: Message passing over temporal chain graph
2. Batch Normalization: Stabilizes training
3. Global Pooling: Aggregates node features into graph embedding
4. MLP Classifier: Binary classification head

Key Design Decisions:
- 2-3 GCN layers (more → oversmoothing risk)
- Skip connections (prevents oversmoothing, helps gradient flow)
- Batch normalization (stabilizes training)
- Dropout (prevents overfitting)
- Global pooling (mean/max/concat)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool, global_max_pool


class WiFi7AttackGCN(nn.Module):
    """
    GCN for WiFi 7 backoff attack detection.

    Architecture:
    1. GCN layers: Temporal message passing
    2. Batch normalization: Stabilizes training
    3. Skip connections: Prevents oversmoothing
    4. Global pooling: Graph-level representation
    5. MLP classifier: Binary prediction

    How it works:
    - Input: Graph with L windows (nodes) connected by temporal chain
    - GCN layers: Each window aggregates features from neighbors
    - Global pool: All L windows → single graph embedding
    - Classifier: Graph embedding → binary prediction (Attack/Normal)
    """

    def __init__(
        self,
        in_channels: int = 13,        # Feature dimension (13 base or 16 with derived)
        hidden_channels: int = 64,    # Hidden dimension
        num_layers: int = 2,          # Number of GCN layers
        dropout: float = 0.3,         # Dropout rate
        pooling: str = 'mean'         # 'mean', 'max', or 'concat'
    ):
        """
        Initialize WiFi7AttackGCN.

        Args:
            in_channels: Input feature dimension
                - 13: Base features only
                - 16: Base + derived features
            hidden_channels: Hidden layer dimension (default: 64)
            num_layers: Number of GCN layers (default: 2)
                - 2 layers: Good for segment_length=256
                - 3 layers: For longer sequences
            dropout: Dropout probability (default: 0.3)
            pooling: Global pooling strategy
                - 'mean': Average pooling (captures overall behavior)
                - 'max': Max pooling (captures peak anomalies)
                - 'concat': Concatenate mean + max

        Example:
            >>> model = WiFi7AttackGCN(
            ...     in_channels=13,
            ...     hidden_channels=64,
            ...     num_layers=2,
            ...     dropout=0.3,
            ...     pooling='mean'
            ... )
            >>> print(model)
        """
        super().__init__()

        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.num_layers = num_layers
        self.dropout = dropout
        self.pooling = pooling

        # GCN layers
        self.convs = nn.ModuleList()
        self.convs.append(GCNConv(in_channels, hidden_channels))

        for _ in range(num_layers - 1):
            self.convs.append(GCNConv(hidden_channels, hidden_channels))

        # Batch normalization (one per GCN layer)
        # Stabilizes training, allows higher learning rates
        self.batch_norms = nn.ModuleList([
            nn.BatchNorm1d(hidden_channels)
            for _ in range(num_layers)
        ])

        # Classifier head
        # Determine input dimension based on pooling strategy
        pool_dim = hidden_channels
        if pooling == 'concat':
            pool_dim = hidden_channels * 2  # Mean + Max concatenated

        self.fc1 = nn.Linear(pool_dim, hidden_channels // 2)
        self.fc2 = nn.Linear(hidden_channels // 2, 2)  # Binary classification

    def forward(self, x, edge_index, batch):
        """
        Forward pass.

        Args:
            x: Node features [num_nodes, in_channels]
                - num_nodes = batch_size * segment_length
                - in_channels = 13 or 16
            edge_index: Graph connectivity [2, num_edges]
                - Temporal chain edges (t ↔ t+1)
            batch: Batch assignment [num_nodes]
                - Maps each node to its graph in the batch

        Returns:
            logits: Class logits [batch_size, 2]
                - logits[:, 0]: Score for Normal
                - logits[:, 1]: Score for Attack

        Example:
            >>> x = torch.randn(256 * 32, 13)  # 32 graphs, 256 nodes each
            >>> edge_index = ...  # Temporal chain edges
            >>> batch = torch.arange(32).repeat_interleave(256)
            >>> logits = model(x, edge_index, batch)
            >>> logits.shape
            torch.Size([32, 2])
        """
        # GCN layers with skip connections
        h = x

        for i, conv in enumerate(self.convs):
            # Graph convolution
            h_new = conv(h, edge_index)

            # Batch normalization
            h_new = self.batch_norms[i](h_new)

            # Activation
            h_new = F.relu(h_new)

            # Dropout
            h_new = F.dropout(h_new, p=self.dropout, training=self.training)

            # Skip connection (residual)
            # Prevents oversmoothing: preserves node identity
            if i > 0 and h.shape == h_new.shape:
                h = h + h_new  # Residual connection
            else:
                h = h_new

        # Global pooling: Aggregate all nodes in each graph
        # [num_nodes, hidden_channels] → [batch_size, hidden_channels]
        if self.pooling == 'mean':
            graph_emb = global_mean_pool(h, batch)
        elif self.pooling == 'max':
            graph_emb = global_max_pool(h, batch)
        elif self.pooling == 'concat':
            # Concatenate mean and max pooling
            mean_emb = global_mean_pool(h, batch)
            max_emb = global_max_pool(h, batch)
            graph_emb = torch.cat([mean_emb, max_emb], dim=1)
        else:
            raise ValueError(f"Unknown pooling strategy: {self.pooling}")

        # Classification head
        # [batch_size, pool_dim] → [batch_size, hidden_channels//2] → [batch_size, 2]
        out = F.relu(self.fc1(graph_emb))
        out = F.dropout(out, p=self.dropout, training=self.training)
        logits = self.fc2(out)

        return logits

    def predict(self, x, edge_index, batch):
        """
        Make predictions (inference mode).

        Args:
            x: Node features [num_nodes, in_channels]
            edge_index: Graph connectivity [2, num_edges]
            batch: Batch assignment [num_nodes]

        Returns:
            predictions: Predicted classes [batch_size]
            probabilities: Class probabilities [batch_size, 2]
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x, edge_index, batch)
            probs = F.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)

        return preds, probs

    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def get_architecture_info(self) -> dict:
        """Get detailed architecture information."""
        info = {
            'in_channels': self.in_channels,
            'hidden_channels': self.hidden_channels,
            'num_layers': self.num_layers,
            'dropout': self.dropout,
            'pooling': self.pooling,
            'total_parameters': self.count_parameters(),
        }

        # Count parameters per layer
        info['parameters_breakdown'] = {
            'gcn_layers': sum(p.numel() for conv in self.convs for p in conv.parameters()),
            'batch_norms': sum(p.numel() for bn in self.batch_norms for p in bn.parameters()),
            'classifier': sum(p.numel() for p in [self.fc1, self.fc2] for p in p.parameters())
        }

        return info

    def __repr__(self) -> str:
        """String representation of the model."""
        info = self.get_architecture_info()
        return (
            f"WiFi7AttackGCN(\n"
            f"  in_channels={info['in_channels']},\n"
            f"  hidden_channels={info['hidden_channels']},\n"
            f"  num_layers={info['num_layers']},\n"
            f"  dropout={info['dropout']},\n"
            f"  pooling='{info['pooling']}',\n"
            f"  total_parameters={info['total_parameters']:,}\n"
            f")"
        )


def create_model(config: dict) -> WiFi7AttackGCN:
    """
    Create WiFi7AttackGCN model from configuration.

    Args:
        config: Configuration dictionary with model parameters

    Returns:
        Initialized model

    Example:
        >>> config = {
        ...     'in_channels': 13,
        ...     'hidden_channels': 64,
        ...     'num_layers': 2,
        ...     'dropout': 0.3,
        ...     'pooling': 'mean'
        ... }
        >>> model = create_model(config)
    """
    model = WiFi7AttackGCN(
        in_channels=config.get('in_channels', 13),
        hidden_channels=config.get('hidden_channels', 64),
        num_layers=config.get('num_layers', 2),
        dropout=config.get('dropout', 0.3),
        pooling=config.get('pooling', 'mean')
    )

    return model


if __name__ == "__main__":
    # Test the model
    print("Testing WiFi7AttackGCN...")
    print()

    # Create model
    model = WiFi7AttackGCN(
        in_channels=13,
        hidden_channels=64,
        num_layers=2,
        dropout=0.3,
        pooling='mean'
    )

    print(model)
    print()

    # Print architecture info
    info = model.get_architecture_info()
    print("Architecture Info:")
    print(f"  Total parameters: {info['total_parameters']:,}")
    print(f"  GCN layers: {info['parameters_breakdown']['gcn_layers']:,}")
    print(f"  Batch norms: {info['parameters_breakdown']['batch_norms']:,}")
    print(f"  Classifier: {info['parameters_breakdown']['classifier']:,}")
    print()

    # Test forward pass with dummy data
    print("Testing forward pass...")
    batch_size = 4
    segment_length = 256
    num_nodes = batch_size * segment_length

    # Dummy features
    x = torch.randn(num_nodes, 13)

    # Dummy temporal chain edges (simplified)
    edges_per_graph = (segment_length - 1) * 2  # Bidirectional
    edge_index = torch.randint(0, segment_length, (2, edges_per_graph * batch_size))

    # Batch assignment
    batch = torch.arange(batch_size).repeat_interleave(segment_length)

    # Forward pass
    model.eval()
    with torch.no_grad():
        logits = model(x, edge_index, batch)

    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {logits.shape}")
    print(f"  Output sample: {logits[0]}")
    print()

    # Test prediction
    preds, probs = model.predict(x, edge_index, batch)
    print(f"  Predictions: {preds}")
    print(f"  Probabilities shape: {probs.shape}")
    print(f"  Probabilities sample: {probs[0]}")

    print("\n✓ Model working correctly!")
