#!/usr/bin/env python3
"""
Windowizer Service
Main service that aggregates raw telemetry into windowed feature segments.
"""

import sys
import signal
import time
import yaml
import logging
import json
from pathlib import Path
from typing import Dict
from collections import defaultdict

from window_aggregator import WindowAggregator
from delta_converter import DeltaConverter
from segment_builder import SegmentBuilder
from kafka_client import KafkaClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Windowizer:
    """
    Main windowizer service.

    Consumes raw telemetry events, aggregates into windows,
    converts deltas, and emits segments.
    """

    def __init__(self, config_path: str = '/app/config.yaml'):
        """
        Initialize windowizer service.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Allow runtime overrides via env vars (for benchmarking different configurations)
        import os
        if os.environ.get('SEGMENT_LENGTH'):
            self.config['windowing']['segment_length'] = int(os.environ['SEGMENT_LENGTH'])
        if os.environ.get('KAFKA_GROUP'):
            self.config['kafka']['consumer_group'] = os.environ['KAFKA_GROUP']
        if os.environ.get('KAFKA_AUTO_OFFSET_RESET'):
            self.config['kafka']['auto_offset_reset'] = os.environ['KAFKA_AUTO_OFFSET_RESET']

        logger.info("Loaded configuration")

        # Initialize components
        self.aggregator = WindowAggregator(
            window_interval_ms=self.config['windowing']['window_interval_ms'],
            base_feature_keys=self.config['features']['base_feature_keys']
        )

        self.delta_converter = DeltaConverter(
            cumulative_counters=self.config['features']['cumulative_counters']
        )

        self.segment_builder = SegmentBuilder(
            segment_length=self.config['windowing']['segment_length'],
            max_buffer_size=self.config['windowing'].get('max_buffer_size', 10000)
        )

        # Initialize Kafka client
        self.kafka = KafkaClient(
            brokers=self.config['kafka']['brokers'],
            input_topic=self.config['kafka']['input_topic'],
            output_topic=self.config['kafka']['output_topic'],
            consumer_group=self.config['kafka']['consumer_group'],
            auto_offset_reset=self.config['kafka']['auto_offset_reset']
        )

        # State tracking
        # Map: (experiment_id, entity_id) -> window_index
        self.window_indices = defaultdict(int)
        # Pending windows across batches to avoid zero-filling split windows.
        # Key: (experiment_id, window_ts, entity_id)
        # Value: {'window_data': {metric: value}, 'first_seen': epoch_seconds}
        self.pending_windows = {}
        self.window_timeout_ms = self.config['windowing'].get('timeout_ms', 5000)
        self.missing_metric_strategy = self.config['features'].get('missing_metric_strategy', 'zero')

        # Batch of events to aggregate
        self.event_batch = []
        self.batch_size = 100  # Process 100 events at a time

        # Running flag
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

        logger.info("Windowizer initialized")

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def process_event(self, event: Dict):
        """
        Process a single telemetry event.

        Args:
            event: Telemetry event dict
        """
        # Add to batch
        self.event_batch.append(event)

        # Process batch when full
        if len(self.event_batch) >= self.batch_size:
            self._process_batch()

    def _process_batch(self):
        """Process accumulated event batch."""
        if not self.event_batch:
            return

        # Aggregate events into windows
        windows = self.aggregator.aggregate_events(self.event_batch)
        self._merge_pending_windows(windows)
        self._process_pending_windows(force=False)

        # Clear batch
        self.event_batch.clear()

    def _merge_pending_windows(self, windows: Dict):
        """
        Merge newly aggregated windows into pending state.

        Args:
            windows: Dict[(experiment_id, window_ts, entity_id), metrics]
        """
        now = time.time()

        for window_key, window_data in windows.items():
            if window_key not in self.pending_windows:
                self.pending_windows[window_key] = {
                    'window_data': window_data.copy(),
                    'first_seen': now
                }
            else:
                self.pending_windows[window_key]['window_data'].update(window_data)

    def _process_pending_windows(self, force: bool = False):
        """
        Emit ready windows from pending state.

        Windows are processed in timestamp order per entity. This guarantees
        ordered sequences for delta conversion and avoids partial-window
        corruption at batch boundaries.

        Args:
            force: If True, flush all pending windows (fill missing metrics)
        """
        if not self.pending_windows:
            return

        now = time.time()
        pending_by_entity = defaultdict(list)

        for window_key in self.pending_windows.keys():
            experiment_id, _, entity_id = window_key
            pending_by_entity[(experiment_id, entity_id)].append(window_key)

        windows_by_entity = defaultdict(list)

        for entity_key, entity_window_keys in pending_by_entity.items():
            experiment_id, entity_id = entity_key
            entity_window_keys.sort(key=lambda key: key[1])  # ISO timestamp order

            for window_key in entity_window_keys:
                state = self.pending_windows[window_key]
                window_data = state['window_data']

                complete = self.aggregator.is_window_complete(window_data)
                expired = force or ((now - state['first_seen']) * 1000 >= self.window_timeout_ms)

                # Preserve order: stop when earliest pending window is still incomplete.
                if not complete and not expired:
                    break

                if not complete:
                    logger.warning(
                        f"Window timeout for {window_key}; filling missing metrics "
                        f"with strategy='{self.missing_metric_strategy}'"
                    )
                    window_data = self.aggregator.fill_missing_metrics(
                        window_data,
                        self.missing_metric_strategy
                    )

                _, window_ts, _ = window_key
                window_idx = self.window_indices[entity_key]
                self.window_indices[entity_key] += 1

                windows_by_entity[entity_key].append({
                    'window_data': window_data,
                    'window_ts': window_ts,
                    'window_idx': window_idx
                })

                del self.pending_windows[window_key]

        # Apply delta conversion and segment building.
        for entity_key, entity_windows in windows_by_entity.items():
            experiment_id, entity_id = entity_key

            entity_windows.sort(key=lambda w: w['window_idx'])

            window_dicts = [w['window_data'] for w in entity_windows]

            converted_windows = self.delta_converter.convert_windows(
                window_dicts,
                experiment_id,
                entity_id
            )

            for i, window in enumerate(converted_windows):
                window_ts = entity_windows[i]['window_ts']
                window_idx = entity_windows[i]['window_idx']

                segment = self.segment_builder.add_window(
                    window=window,
                    experiment_id=experiment_id,
                    entity_id=entity_id,
                    window_ts=window_ts,
                    window_idx=window_idx
                )

                # Emit segment if ready
                if segment is not None:
                    self._emit_segment(segment)

            # Flush after a batch of windows is processed to ensure delivery
            self.kafka.flush()

    def _emit_segment(self, segment: Dict):
        """
        Emit segment to Kafka.

        Args:
            segment: Segment dict
        """
        try:
            # Produce to output topic
            self.kafka.produce(segment)

            logger.info(
                f"Emitted segment {segment['segment_id']} for "
                f"{segment['experiment_id']}/{segment['entity_id']}: "
                f"{segment['window_start_idx']}-{segment['window_end_idx']}"
            )

        except Exception as e:
            logger.error(f"Error emitting segment: {e}", exc_info=True)

    def run(self):
        """
        Main service loop.
        """
        logger.info("Starting windowizer service...")
        logger.info(f"Consuming from: {self.config['kafka']['input_topic']}")
        logger.info(f"Producing to: {self.config['kafka']['output_topic']}")

        last_stats_time = time.time()
        stats_interval = 60  # Print stats every 60s

        try:
            while self.running:
                # Consume message
                event = self.kafka.consume(timeout=1.0)

                if event is not None:
                    self.process_event(event)
                else:
                    # No message available, process any pending batch
                    if self.event_batch:
                        self._process_batch()
                    elif self.pending_windows:
                        # Flush timed-out windows even without new events.
                        self._process_pending_windows(force=False)

                # Commit periodically (every 10 messages)
                if self.kafka.messages_delivered % 10 == 0 and self.kafka.messages_delivered > 0:
                    self.kafka.commit()

                # Print stats periodically
                current_time = time.time()
                if current_time - last_stats_time >= stats_interval:
                    self._print_stats()
                    last_stats_time = current_time

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def _print_stats(self):
        """Print service statistics."""
        kafka_stats = self.kafka.get_stats()
        buffer_status = self.segment_builder.get_buffer_status()

        logger.info("=== Windowizer Stats ===")
        logger.info(f"Kafka - Sent: {kafka_stats['messages_sent']}, "
                   f"Delivered: {kafka_stats['messages_delivered']}, "
                   f"Failed: {kafka_stats['messages_failed']}")
        logger.info(f"Active entities: {len(buffer_status)}")

        for entity, status in buffer_status.items():
            logger.info(f"  {entity}: {status['progress']} "
                       f"(segments: {status['segments_emitted']})")

    def shutdown(self):
        """Shutdown service gracefully."""
        logger.info("Shutting down windowizer...")

        # Process any remaining events
        if self.event_batch:
            logger.info("Processing remaining events...")
            self._process_batch()

        # Flush any remaining pending windows.
        if self.pending_windows:
            logger.info("Flushing pending windows...")
            self._process_pending_windows(force=True)

        # Flush incomplete segments (optional - may want to skip partial segments)
        # partial_segments = self.segment_builder.flush_incomplete_segments()
        # for segment in partial_segments:
        #     self._emit_segment(segment)

        # Flush Kafka producer
        logger.info("Flushing Kafka producer...")
        self.kafka.flush()

        # Close Kafka client
        self.kafka.close()

        # Print final stats
        self._print_stats()

        logger.info("Windowizer shutdown complete")


def main():
    """Main entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else '/app/config.yaml'

    # Check if config exists
    if not Path(config_path).exists():
        # Try local path
        config_path = 'config.yaml'
        if not Path(config_path).exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)

    windowizer = Windowizer(config_path)
    windowizer.run()


if __name__ == '__main__':
    main()
