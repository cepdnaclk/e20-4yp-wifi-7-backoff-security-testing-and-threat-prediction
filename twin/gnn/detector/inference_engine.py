"""
Inference Engine
Runs GCN inference on batched segments.
"""

import torch
import torch.nn.functional as F
from typing import Dict, List, Tuple
import logging
import time

from model_loader import ModelLoader
from graph_builder import GraphBuilder
from feature_processor import FeatureProcessor

logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    Runs GCN inference on windowed segments.

    Coordinates model loading, graph building, feature processing,
    and prediction generation.
    """

    def __init__(
        self,
        model_loader: ModelLoader,
        use_derived_features: bool = True,
        threshold: float = 0.5,
        batch_size: int = 32
    ):
        """
        Initialize inference engine.

        Args:
            model_loader: ModelLoader instance
            use_derived_features: Whether to add derived features
            threshold: Prediction threshold (p_attack > threshold → attack)
            batch_size: Batch size for inference
        """
        self.model_loader = model_loader
        self.use_derived_features = use_derived_features
        self.threshold = threshold
        self.batch_size = batch_size

        # Will be initialized after model loads
        self.feature_processor = None
        self.graph_builder = None

    def initialize(self) -> bool:
        """
        Initialize engine after model is loaded.

        Returns:
            True if initialization successful
        """
        if self.model_loader.model is None:
            logger.error("Model not loaded, cannot initialize engine")
            return False

        # Initialize feature processor
        self.feature_processor = FeatureProcessor(
            scaler=self.model_loader.scaler,
            use_derived_features=self.use_derived_features
        )

        # Initialize graph builder
        self.graph_builder = GraphBuilder(
            feature_keys=self.feature_processor.feature_keys
        )

        logger.info("Inference engine initialized")
        return True

    def predict(self, segments: List[Dict]) -> List[Dict]:
        """
        Run inference on batch of segments.

        Args:
            segments: List of segment dicts

        Returns:
            List of prediction dicts
        """
        if not segments:
            return []

        try:
            start_time = time.time()

            # Process segments (add derived features)
            processed_segments = [
                self.feature_processor.process_segment(seg)
                for seg in segments
            ]

            # Build batched graph
            batch_data = self.graph_builder.build_batch(processed_segments)

            # For v3 models: append segment-length conditioning feature before scaling.
            # The v3 scaler has 17 dimensions (16 features + log2(L)/8.0).
            # Compute seg_len per node from the batch assignment tensor.
            scaler_dim = len(self.feature_processor.scaler_mean)
            if scaler_dim == 17 and batch_data.x.shape[1] == 16:
                batch_counts = torch.bincount(batch_data.batch)
                seg_len_vals = torch.log2(batch_counts.float().clamp(min=1)) / 8.0
                per_node_seg_len = seg_len_vals[batch_data.batch].unsqueeze(1)
                batch_data.x = torch.cat([batch_data.x, per_node_seg_len], dim=1)

            # Scale features
            batch_data.x = self.feature_processor.scale_features(batch_data.x)

            # Move to device
            device = self.model_loader.device
            batch_data = batch_data.to(device)

            # Run inference
            with torch.no_grad():
                logits = self.model_loader.model(
                    batch_data.x,
                    batch_data.edge_index,
                    batch_data.batch
                )
                probs = F.softmax(logits, dim=1)
                preds = (probs[:, 1] > self.threshold).long()

            # Convert to CPU
            probs_np = probs.cpu().numpy()
            preds_np = preds.cpu().numpy()

            inference_time = (time.time() - start_time) * 1000  # ms

            # Build results
            results = []
            for i, segment in enumerate(segments):
                result = {
                    'experiment_id': segment['experiment_id'],
                    'entity_id': segment['entity_id'],
                    'segment_id': segment['segment_id'],
                    'window_start_idx': segment['window_start_idx'],
                    'window_end_idx': segment['window_end_idx'],
                    'ts_start': segment['ts_start'],
                    'ts_end': segment['ts_end'],
                    'prediction': int(preds_np[i]),
                    'confidence': float(probs_np[i].max()),
                    'probabilities': probs_np[i].tolist(),
                    'model_version': self.model_loader.loaded_version,
                    'model_path': self.model_loader.loaded_path,
                    'inference_time_ms': inference_time / len(segments)
                }
                results.append(result)

            logger.info(
                f"Inference complete: {len(segments)} segments in {inference_time:.1f}ms "
                f"({inference_time/len(segments):.1f}ms per segment)"
            )

            return results

        except Exception as e:
            logger.error(f"Error during inference: {e}", exc_info=True)
            return []

    def predict_batch(self, segments: List[Dict]) -> List[Dict]:
        """
        Run inference with batching.

        Args:
            segments: List of segment dicts

        Returns:
            List of prediction dicts
        """
        all_results = []

        # Process in batches
        for i in range(0, len(segments), self.batch_size):
            batch = segments[i:i + self.batch_size]
            results = self.predict(batch)
            all_results.extend(results)

        return all_results
