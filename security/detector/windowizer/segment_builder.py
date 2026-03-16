"""
Segment Builder
Buffers windows into fixed-length segments for GCN inference.
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SegmentBuilder:
    """
    Buffers windows into fixed-length segments.

    Maintains buffers per (experiment_id, entity_id) and emits complete
    segments of length L.
    """

    def __init__(self, segment_length: int, max_buffer_size: int = 10000):
        """
        Initialize segment builder.

        Args:
            segment_length: Number of windows per segment (e.g., 256)
            max_buffer_size: Maximum windows to buffer per entity
        """
        self.segment_length = segment_length
        self.max_buffer_size = max_buffer_size

        # Buffers: {(experiment_id, entity_id): [windows...]}
        self.buffers = {}

        # Metadata: {(experiment_id, entity_id): {...}}
        self.metadata = {}

    def add_window(
        self,
        window: Dict,
        experiment_id: str,
        entity_id: str,
        window_ts: str,
        window_idx: int
    ) -> Optional[Dict]:
        """
        Add window to buffer and emit segment if complete.

        Args:
            window: Window dict with metrics
            experiment_id: Experiment ID
            entity_id: Entity ID
            window_ts: Window timestamp (ISO format)
            window_idx: Window index in sequence

        Returns:
            Complete segment dict if ready, None otherwise
        """
        buffer_key = (experiment_id, entity_id)

        # Initialize buffer if needed
        if buffer_key not in self.buffers:
            self.buffers[buffer_key] = []
            self.metadata[buffer_key] = {
                'segment_count': 0,
                'first_window_idx': window_idx,
                'first_window_ts': window_ts
            }

        # Add window to buffer
        window_with_meta = {
            'window_idx': window_idx,
            'ts': window_ts,
            **window
        }
        self.buffers[buffer_key].append(window_with_meta)

        # Check buffer size limit
        if len(self.buffers[buffer_key]) > self.max_buffer_size:
            logger.warning(
                f"Buffer overflow for {experiment_id}/{entity_id}: "
                f"{len(self.buffers[buffer_key])} windows. "
                f"Dropping oldest windows."
            )
            # Drop oldest windows to stay under limit
            overflow = len(self.buffers[buffer_key]) - self.max_buffer_size
            self.buffers[buffer_key] = self.buffers[buffer_key][overflow:]

        # Check if segment is complete
        if len(self.buffers[buffer_key]) >= self.segment_length:
            return self._emit_segment(buffer_key)

        return None

    def _emit_segment(self, buffer_key: tuple) -> Dict:
        """
        Emit a complete segment and update buffer.

        Args:
            buffer_key: (experiment_id, entity_id)

        Returns:
            Segment dict
        """
        experiment_id, entity_id = buffer_key

        # Extract segment from buffer (first segment_length windows)
        segment_windows = self.buffers[buffer_key][:self.segment_length]

        # Remove emitted windows from buffer
        self.buffers[buffer_key] = self.buffers[buffer_key][self.segment_length:]

        # Extract metadata
        first_window = segment_windows[0]
        last_window = segment_windows[-1]
        segment_id = f"seg_{self.metadata[buffer_key]['segment_count']}"

        # Update segment count
        self.metadata[buffer_key]['segment_count'] += 1

        # Build segment dict
        segment = {
            'experiment_id': experiment_id,
            'entity_id': entity_id,
            'segment_id': segment_id,
            'window_start_idx': first_window['window_idx'],
            'window_end_idx': last_window['window_idx'],
            'ts_start': first_window['ts'],
            'ts_end': last_window['ts'],
            'windows': segment_windows
        }

        logger.info(
            f"Emitted segment {segment_id} for {experiment_id}/{entity_id}: "
            f"windows {first_window['window_idx']}-{last_window['window_idx']}"
        )

        return segment

    def flush_incomplete_segments(self) -> List[Dict]:
        """
        Flush all incomplete segments (for graceful shutdown).

        Returns:
            List of partial segments
        """
        segments = []

        for buffer_key in list(self.buffers.keys()):
            if len(self.buffers[buffer_key]) > 0:
                # Emit partial segment
                experiment_id, entity_id = buffer_key
                segment_windows = self.buffers[buffer_key]

                first_window = segment_windows[0]
                last_window = segment_windows[-1]
                segment_id = f"seg_{self.metadata[buffer_key]['segment_count']}_partial"

                segment = {
                    'experiment_id': experiment_id,
                    'entity_id': entity_id,
                    'segment_id': segment_id,
                    'window_start_idx': first_window['window_idx'],
                    'window_end_idx': last_window['window_idx'],
                    'ts_start': first_window['ts'],
                    'ts_end': last_window['ts'],
                    'windows': segment_windows,
                    'partial': True  # Mark as partial
                }

                segments.append(segment)

                logger.info(
                    f"Flushed partial segment {segment_id} for {experiment_id}/{entity_id}: "
                    f"{len(segment_windows)} windows"
                )

                # Clear buffer
                self.buffers[buffer_key] = []

        return segments

    def get_buffer_status(self) -> Dict:
        """
        Get current buffer status.

        Returns:
            Dict with buffer statistics
        """
        status = {}
        for buffer_key, windows in self.buffers.items():
            experiment_id, entity_id = buffer_key
            status[f"{experiment_id}/{entity_id}"] = {
                'buffered_windows': len(windows),
                'segments_emitted': self.metadata[buffer_key]['segment_count'],
                'first_window_idx': self.metadata[buffer_key]['first_window_idx'],
                'progress': f"{len(windows)}/{self.segment_length}"
            }
        return status
