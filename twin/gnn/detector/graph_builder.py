"""
Graph Builder
Builds PyTorch Geometric graphs from windowed feature segments.
"""

import torch
from torch_geometric.data import Data
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Builds temporal chain graphs for GCN inference.

    Each segment becomes a graph with:
    - Nodes: windows (e.g., 256 nodes)
    - Edges: temporal chain (t ↔ t+1)
    """

    def __init__(self, feature_keys: List[str]):
        """
        Initialize graph builder.

        Args:
            feature_keys: List of feature names (in order)
        """
        self.feature_keys = feature_keys

    def build_graph(self, segment: Dict) -> Data:
        """
        Build PyG graph from segment.

        Args:
            segment: Segment dict with 'windows' list

        Returns:
            PyG Data object
        """
        try:
            windows = segment['windows']
            num_windows = len(windows)

            # Extract features
            features = []
            for window in windows:
                feature_vector = [
                    float(window.get(key, 0.0))
                    for key in self.feature_keys
                ]
                features.append(feature_vector)

            # Convert to tensor [num_windows, num_features]
            x = torch.tensor(features, dtype=torch.float)

            # Build temporal chain edges (bidirectional)
            edge_index = self._build_temporal_chain_edges(num_windows)

            # Create PyG Data object
            data = Data(
                x=x,
                edge_index=edge_index,
                num_nodes=num_windows
            )

            # Add metadata
            data.experiment_id = segment['experiment_id']
            data.entity_id = segment['entity_id']
            data.segment_id = segment['segment_id']
            data.window_start_idx = segment['window_start_idx']
            data.window_end_idx = segment['window_end_idx']
            data.ts_start = segment['ts_start']
            data.ts_end = segment['ts_end']

            return data

        except Exception as e:
            logger.error(f"Error building graph: {e}", exc_info=True)
            raise

    def _build_temporal_chain_edges(self, num_nodes: int) -> torch.Tensor:
        """
        Build temporal chain edge index.

        Creates edges connecting consecutive windows: (t ↔ t+1) for all t

        Args:
            num_nodes: Number of windows (nodes) in segment

        Returns:
            Edge index tensor of shape [2, num_edges]
        """
        if num_nodes < 2:
            # Single node: no edges
            return torch.zeros((2, 0), dtype=torch.long)

        # Create forward edges: 0→1, 1→2, ..., (n-2)→(n-1)
        src = torch.arange(0, num_nodes - 1, dtype=torch.long)
        dst = src + 1

        # Make bidirectional (undirected graph)
        # Forward: 0→1, 1→2, ..., (n-2)→(n-1)
        # Backward: 1→0, 2→1, ..., (n-1)→(n-2)
        edge_index = torch.stack([
            torch.cat([src, dst]),  # Source nodes
            torch.cat([dst, src])   # Destination nodes
        ], dim=0)

        return edge_index

    def build_batch(self, segments: List[Dict]) -> Data:
        """
        Build batched graph from multiple segments.

        Args:
            segments: List of segment dicts

        Returns:
            Batched PyG Data object
        """
        from torch_geometric.data import Batch

        graphs = [self.build_graph(seg) for seg in segments]
        batch = Batch.from_data_list(graphs)

        return batch
