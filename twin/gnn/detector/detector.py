#!/usr/bin/env python3
"""
GCN Detector Service
Main service for real-time attack detection using GCN.
"""

import sys
import signal
import time
import yaml
import logging
import json
import os
from pathlib import Path
from typing import Dict, List
from threading import Thread
from collections import defaultdict

from model_loader import ModelLoader
from inference_engine import InferenceEngine
from db_writer import DatabaseWriter
from health_api import HealthAPI

# Kafka client (similar to windowizer)
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GCNDetector:
    """
    Main GCN detector service.

    Consumes windowed feature segments, runs GCN inference,
    and emits predictions to Kafka and DB.
    """

    def __init__(self, config_path: str = '/app/config.yaml'):
        """
        Initialize GCN detector service.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        logger.info("Loaded configuration")

        # Initialize model loader
        self.model_loader = ModelLoader(
            registry_path=self.config['model']['registry_path'],
            active_version=self.config['model']['active_version'],
            device=self.config['model']['device']
        )

        # Load model
        logger.info("Loading GCN model...")
        if not self.model_loader.load_model():
            raise RuntimeError("Failed to load model")

        # Initialize inference engine
        self.inference_engine = InferenceEngine(
            model_loader=self.model_loader,
            use_derived_features=self.config['model']['use_derived_features'],
            threshold=self.config['inference']['threshold'],
            batch_size=self.config['inference'].get('batch_size', 32)
        )

        if not self.inference_engine.initialize():
            raise RuntimeError("Failed to initialize inference engine")

        # Initialize Kafka
        self._init_kafka()

        # Initialize database writer
        db_config = self.config['database']
        self.db_writer = DatabaseWriter(
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=os.getenv('PG_PASS', db_config.get('password', '')),
            table=db_config['table'],
            batch_size=db_config['batch_insert_size']
        )

        if not self.db_writer.connect():
            raise RuntimeError("Failed to connect to database")

        # Statistics
        self.stats = {
            'segments_received': 0,
            'predictions_made': 0,
            'attacks_detected': 0,
            'predictions_failed': 0,
            'db_writes_failed': 0
        }

        # Running flag
        self.running = True

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)

        # Initialize health API
        self.health_api = HealthAPI(
            port=self.config.get('health', {}).get('port', 8080)
        )
        self.health_api.set_callbacks(
            model_loaded=lambda: self.model_loader.model is not None,
            kafka_connected=lambda: self.consumer is not None,
            db_connected=lambda: self.db_writer.check_connection(),
            get_stats=lambda: self.stats.copy()
        )

        # Start health API in background thread
        self.health_thread = Thread(target=self.health_api.run, daemon=True)
        self.health_thread.start()

        logger.info("GCN Detector initialized")

    def _init_kafka(self):
        """Initialize Kafka consumer and producer."""
        kafka_config = self.config['kafka']

        # Consumer
        consumer_conf = {
            'bootstrap.servers': kafka_config['brokers'],
            'group.id': kafka_config['consumer_group'],
            'auto.offset.reset': kafka_config['auto_offset_reset'],
            'enable.auto.commit': False,
            'max.poll.interval.ms': 300000,
            'session.timeout.ms': 30000,
        }

        self.consumer = Consumer(consumer_conf)
        self.consumer.subscribe([kafka_config['input_topic']])

        logger.info(f"Subscribed to topic: {kafka_config['input_topic']}")

        # Producer
        producer_conf = {
            'bootstrap.servers': kafka_config['brokers'],
            'acks': 1,
            'compression.type': 'snappy',
        }

        self.producer = Producer(producer_conf)

        self.output_topic = kafka_config['output_topic']

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def consume_segment(self, timeout: float = 1.0) -> Dict:
        """
        Consume one segment from Kafka.

        Args:
            timeout: Timeout in seconds

        Returns:
            Segment dict or None
        """
        try:
            msg = self.consumer.poll(timeout)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    return None
                else:
                    raise KafkaException(msg.error())

            # Decode segment
            segment = json.loads(msg.value().decode('utf-8'))
            return segment

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode segment: {e}")
            return None
        except Exception as e:
            logger.error(f"Error consuming segment: {e}", exc_info=True)
            return None

    def produce_prediction(self, prediction: Dict):
        """
        Produce prediction to Kafka.

        Args:
            prediction: Prediction dict
        """
        try:
            value = json.dumps(prediction).encode('utf-8')
            self.producer.produce(self.output_topic, value=value)
            self.producer.poll(0)  # Trigger callbacks

        except Exception as e:
            logger.error(f"Error producing prediction: {e}", exc_info=True)

    def process_segment(self, segment: Dict):
        """
        Process one segment: run inference and emit results.

        Args:
            segment: Segment dict
        """
        try:
            self.stats['segments_received'] += 1

            # Run inference
            predictions = self.inference_engine.predict([segment])

            if not predictions:
                logger.error("Inference failed")
                self.stats['predictions_failed'] += 1
                return

            prediction = predictions[0]
            self.stats['predictions_made'] += 1

            if prediction['prediction'] == 1:
                self.stats['attacks_detected'] += 1
                logger.warning(
                    f"ATTACK DETECTED: {segment['experiment_id']}/{segment['entity_id']} "
                    f"segment {segment['segment_id']} "
                    f"(confidence: {prediction['confidence']:.2f})"
                )

            # Produce to Kafka
            self.produce_prediction(prediction)

            # Write to database
            if not self.db_writer.write_predictions([prediction]):
                self.stats['db_writes_failed'] += 1

        except Exception as e:
            logger.error(f"Error processing segment: {e}", exc_info=True)
            self.stats['predictions_failed'] += 1

    def run(self):
        """
        Main service loop.
        """
        logger.info("Starting GCN detector service...")
        logger.info(f"Model: {self.model_loader.loaded_version}")
        logger.info(f"Device: {self.model_loader.device}")
        logger.info(f"Consuming from: {self.config['kafka']['input_topic']}")
        logger.info(f"Producing to: {self.output_topic}")

        last_stats_time = time.time()
        last_model_check_time = time.time()
        stats_interval = 60  # Print stats every 60s
        model_check_interval = 60  # Check for model updates every 60s

        try:
            while self.running:
                # Consume segment
                segment = self.consume_segment(timeout=1.0)

                if segment is not None:
                    self.process_segment(segment)

                    # Commit periodically
                    if self.stats['segments_received'] % 10 == 0:
                        self.consumer.commit(asynchronous=False)

                # Check for model updates
                current_time = time.time()
                if current_time - last_model_check_time >= model_check_interval:
                    self.model_loader.reload_if_needed()
                    last_model_check_time = current_time

                # Print stats periodically
                if current_time - last_stats_time >= stats_interval:
                    self._print_stats()
                    last_stats_time = current_time

                # Check database connection
                if not self.db_writer.check_connection():
                    logger.warning("Database connection lost, reconnecting...")
                    self.db_writer.reconnect()

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def _print_stats(self):
        """Print service statistics."""
        logger.info("=== GCN Detector Stats ===")
        logger.info(f"Segments received: {self.stats['segments_received']}")
        logger.info(f"Predictions made: {self.stats['predictions_made']}")
        logger.info(f"Attacks detected: {self.stats['attacks_detected']}")
        logger.info(f"Prediction failures: {self.stats['predictions_failed']}")
        logger.info(f"DB write failures: {self.stats['db_writes_failed']}")

        if self.stats['predictions_made'] > 0:
            attack_rate = self.stats['attacks_detected'] / self.stats['predictions_made'] * 100
            logger.info(f"Attack rate: {attack_rate:.1f}%")

    def shutdown(self):
        """Shutdown service gracefully."""
        logger.info("Shutting down GCN detector...")

        # Flush producer
        logger.info("Flushing Kafka producer...")
        self.producer.flush(timeout=30)

        # Close consumer
        self.consumer.close()

        # Flush and close database
        logger.info("Flushing database writes...")
        self.db_writer.close()

        # Print final stats
        self._print_stats()

        logger.info("GCN Detector shutdown complete")


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

    detector = GCNDetector(config_path)
    detector.run()


if __name__ == '__main__':
    main()
