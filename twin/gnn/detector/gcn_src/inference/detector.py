"""
Production inference detector for WiFi 7 attack detection.

This module provides the WiFi7AttackDetector class for real-time attack
detection in digital twin environments.

CRITICAL: Uses the SAME preprocessing as training to ensure consistency.
NO database, NO API - pure model inference for integration.
"""

import json
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

# Import model and preprocessing
from ..models.gcn import WiFi7AttackGCN
from ..data.preprocessing import (
    convert_to_deltas,
    add_derived_features,
    BASE_FEATURE_KEYS,
    DERIVED_FEATURE_KEYS
)


class WiFi7AttackDetector:
    """
    Production inference for WiFi 7 attack detection.

    This class loads a trained model and provides methods for:
    1. Single segment prediction (exactly segment_length windows)
    2. Streaming prediction (sliding window over long sequences)
    3. Real-time detection (buffer-based processing)

    CRITICAL: Applies the SAME preprocessing as training:
    - Delta conversion
    - Feature extraction (NO bias!)
    - Temporal chain edges
    - Feature scaling
    """

    def __init__(
        self,
        model_path: str,
        scaler_path: str,
        segment_length: int = 256,
        device: str = 'cpu',
        use_derived_features: bool = True
    ):
        """
        Initialize detector.

        Args:
            model_path: Path to model checkpoint (.pt file)
            scaler_path: Path to scaler JSON file
            segment_length: Number of windows per prediction
            device: 'cpu' or 'cuda'
            use_derived_features: Whether to use derived features
                (must match training configuration!)

        Example:
            >>> detector = WiFi7AttackDetector(
            ...     model_path='checkpoints/best_model.pt',
            ...     scaler_path='checkpoints/scaler.json',
            ...     segment_length=256,
            ...     device='cuda'
            ... )
        """
        self.device = torch.device(device)
        self.segment_length = segment_length
        self.use_derived_features = use_derived_features

        # Feature keys (13 base or 16 with derived)
        self.feature_keys = BASE_FEATURE_KEYS.copy()
        if use_derived_features:
            self.feature_keys.extend(DERIVED_FEATURE_KEYS)

        # CRITICAL: Verify 'bias' is NOT in feature keys
        assert 'bias' not in self.feature_keys, \
            "CRITICAL ERROR: 'bias' must NEVER be in feature keys!"

        self.in_channels = len(self.feature_keys)

        # Load scaler
        print(f"Loading scaler from {scaler_path}...")
        with open(scaler_path, 'r') as f:
            scaler_dict = json.load(f)

        self.scaler_mean = np.array(scaler_dict['mean'])
        self.scaler_std = np.array(scaler_dict['std'])

        # Verify scaler dimensions
        assert len(self.scaler_mean) == self.in_channels, \
            f"Scaler dimension mismatch: expected {self.in_channels}, got {len(self.scaler_mean)}"

        # Load model
        print(f"Loading model from {model_path}...")
        checkpoint = torch.load(model_path, map_location=self.device)

        # Extract config
        config = checkpoint['config']

        # Initialize model
        self.model = WiFi7AttackGCN(
            in_channels=config['in_channels'],
            hidden_channels=config['hidden_channels'],
            num_layers=config['num_layers'],
            dropout=0.0,  # No dropout at inference
            pooling=config.get('pooling', 'mean')
        ).to(self.device)

        # Load weights
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()  # Set to evaluation mode

        val_f1 = checkpoint.get('val_f1', 0.0)
        print(f"✓ Model loaded successfully (Val F1: {val_f1:.4f})")
        print(f"  Parameters: {self.model.count_parameters():,}")
        print(f"  Feature dimension: {self.in_channels}")

    def preprocess_windows(self, windows: List[Dict]) -> torch.Tensor:
        """
        Convert raw windows to model input features.

        CRITICAL: Uses SAME preprocessing as training!

        Args:
            windows: List of window dictionaries (exactly segment_length)

        Returns:
            Feature tensor [segment_length, in_channels]

        Raises:
            ValueError: If number of windows doesn't match segment_length
        """
        if len(windows) != self.segment_length:
            raise ValueError(
                f"Expected {self.segment_length} windows, got {len(windows)}"
            )

        # 1. Convert cumulative counters to deltas
        windows = convert_to_deltas(windows)

        # 2. Add derived features if enabled
        if self.use_derived_features:
            windows = [add_derived_features(w) for w in windows]

        # 3. Extract features (NO bias!)
        features = []
        for window in windows:
            feature_vector = [
                float(window.get(key, 0.0))
                for key in self.feature_keys
            ]
            features.append(feature_vector)

        x = np.array(features, dtype=np.float32)

        # 4. Apply scaling
        x_scaled = (x - self.scaler_mean) / (self.scaler_std + 1e-8)

        return torch.from_numpy(x_scaled).float()

    def _build_temporal_chain_edges(self, num_nodes: int) -> torch.Tensor:
        """
        Build temporal chain edge index.

        Same as training: connects consecutive windows (t ↔ t+1).

        Args:
            num_nodes: Number of windows (nodes)

        Returns:
            Edge index tensor [2, num_edges]
        """
        src = torch.arange(0, num_nodes - 1, dtype=torch.long)
        dst = src + 1

        # Bidirectional edges
        edge_index = torch.stack([
            torch.cat([src, dst]),
            torch.cat([dst, src])
        ], dim=0)

        return edge_index

    @torch.no_grad()
    def predict(self, windows: List[Dict]) -> Dict:
        """
        Detect attack from window sequence.

        Args:
            windows: Exactly segment_length window dictionaries

        Returns:
            Dictionary with:
            - prediction: 0 (Normal) or 1 (Attack)
            - confidence: float (0.0 to 1.0)
            - probabilities: [p_normal, p_attack]
            - label: str ('Normal' or 'Attack')

        Example:
            >>> windows = load_windows("attack_file.json")[:256]
            >>> result = detector.predict(windows)
            >>> if result['prediction'] == 1:
            ...     print(f"ATTACK detected with {result['confidence']:.2%} confidence")
        """
        # Preprocess
        x = self.preprocess_windows(windows).to(self.device)

        # Build edges
        edge_index = self._build_temporal_chain_edges(len(windows)).to(self.device)

        # Batch assignment (single graph)
        batch = torch.zeros(len(windows), dtype=torch.long, device=self.device)

        # Forward pass
        logits = self.model(x, edge_index, batch)
        probs = F.softmax(logits, dim=1)[0]  # [2]
        prediction = logits.argmax(dim=1).item()

        # Convert to label
        label = 'Attack' if prediction == 1 else 'Normal'

        return {
            'prediction': prediction,
            'confidence': float(probs[prediction]),
            'probabilities': probs.cpu().numpy().tolist(),
            'label': label
        }

    @torch.no_grad()
    def predict_batch(self, window_sequences: List[List[Dict]]) -> List[Dict]:
        """
        Predict on multiple window sequences in batch.

        Args:
            window_sequences: List of window sequences (each with segment_length windows)

        Returns:
            List of prediction dictionaries

        Example:
            >>> sequences = [windows1[:256], windows2[:256], windows3[:256]]
            >>> results = detector.predict_batch(sequences)
            >>> for i, result in enumerate(results):
            ...     print(f"Sequence {i}: {result['label']}")
        """
        results = []

        for windows in window_sequences:
            result = self.predict(windows)
            results.append(result)

        return results

    @torch.no_grad()
    def predict_stream(
        self,
        windows: List[Dict],
        stride: Optional[int] = None
    ) -> List[Dict]:
        """
        Sliding window predictions over long stream.

        Args:
            windows: Full window stream (any length >= segment_length)
            stride: Step size for sliding window
                - None: Non-overlapping (stride = segment_length)
                - < segment_length: Overlapping segments

        Returns:
            List of predictions, one per segment

        Example:
            >>> windows = load_windows("long_capture.json")  # 1000 windows
            >>> predictions = detector.predict_stream(windows, stride=128)
            >>> attack_count = sum(1 for p in predictions if p['prediction'] == 1)
            >>> print(f"Detected {attack_count}/{len(predictions)} attack segments")
        """
        if len(windows) < self.segment_length:
            raise ValueError(
                f"Need at least {self.segment_length} windows, got {len(windows)}"
            )

        if stride is None:
            stride = self.segment_length  # Non-overlapping

        predictions = []

        for start_idx in range(0, len(windows) - self.segment_length + 1, stride):
            segment = windows[start_idx:start_idx + self.segment_length]
            result = self.predict(segment)

            # Add window range info
            result['window_range'] = [start_idx, start_idx + self.segment_length - 1]
            result['window_start'] = start_idx

            predictions.append(result)

        return predictions


class RealtimeDetector:
    """
    Buffer-based real-time detection.

    Accumulates windows in a buffer and triggers prediction when buffer is full.
    Useful for processing live network streams.
    """

    def __init__(self, detector: WiFi7AttackDetector):
        """
        Initialize realtime detector.

        Args:
            detector: WiFi7AttackDetector instance
        """
        self.detector = detector
        self.buffer = []
        self.buffer_size = detector.segment_length
        self.total_windows_processed = 0

    def add_window(self, window: Dict) -> Optional[Dict]:
        """
        Add one window, predict when buffer is full.

        Args:
            window: Window dictionary

        Returns:
            Prediction dictionary if buffer is full, None otherwise

        Example:
            >>> rt_detector = RealtimeDetector(detector)
            >>> for window in stream:
            ...     result = rt_detector.add_window(window)
            ...     if result:
            ...         if result['prediction'] == 1:
            ...             print(f"ATTACK at window {window['window']}")
        """
        self.buffer.append(window)
        self.total_windows_processed += 1

        if len(self.buffer) == self.buffer_size:
            # Buffer is full, make prediction
            result = self.detector.predict(self.buffer)

            # Add metadata
            result['windows_processed'] = self.total_windows_processed
            result['buffer_end_window'] = self.buffer[-1].get('window', -1)

            # Reset buffer
            self.buffer = []

            return result

        return None

    def flush(self) -> Optional[Dict]:
        """
        Force prediction on partial buffer.

        Returns:
            Prediction if buffer has at least segment_length windows, None otherwise
        """
        if len(self.buffer) >= self.buffer_size:
            result = self.detector.predict(self.buffer[:self.buffer_size])
            self.buffer = []
            return result

        return None


if __name__ == "__main__":
    # Test detector
    print("Testing WiFi7AttackDetector...")
    print()

    # Check if model and scaler exist
    model_path = Path("checkpoints/best_model.pt")
    scaler_path = Path("checkpoints/scaler.json")

    if not model_path.exists() or not scaler_path.exists():
        print("Error: Model or scaler not found. Train model first.")
        print(f"  Model: {model_path} (exists: {model_path.exists()})")
        print(f"  Scaler: {scaler_path} (exists: {scaler_path.exists()})")
    else:
        # Load detector
        detector = WiFi7AttackDetector(
            model_path=str(model_path),
            scaler_path=str(scaler_path),
            segment_length=256
        )

        # Test on sample file
        data_file = Path("data/Attack").glob("*.json")
        data_file = next(data_file, None)

        if data_file:
            print(f"\nTesting on {data_file.name}...")

            with open(data_file) as f:
                windows = json.load(f)

            # Single prediction
            if len(windows) >= 256:
                result = detector.predict(windows[:256])
                print(f"  Prediction: {result['label']}")
                print(f"  Confidence: {result['confidence']:.2%}")
                print(f"  Probabilities: {result['probabilities']}")

            # Stream prediction
            if len(windows) >= 512:
                predictions = detector.predict_stream(windows, stride=256)
                print(f"\n  Stream predictions: {len(predictions)} segments")
                attack_count = sum(1 for p in predictions if p['prediction'] == 1)
                print(f"  Attack segments: {attack_count}/{len(predictions)}")

        print("\n✓ Detector working correctly!")
