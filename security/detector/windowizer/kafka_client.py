"""
Kafka Client
Wrapper for Confluent Kafka consumer and producer.
"""

from typing import Dict, Callable, Optional
import json
import logging
from confluent_kafka import Consumer, Producer, KafkaError, KafkaException

logger = logging.getLogger(__name__)


class KafkaClient:
    """
    Kafka consumer and producer wrapper.
    """

    def __init__(
        self,
        brokers: str,
        input_topic: str,
        output_topic: str,
        consumer_group: str,
        auto_offset_reset: str = 'latest'
    ):
        """
        Initialize Kafka client.

        Args:
            brokers: Kafka broker addresses (e.g., "localhost:9092")
            input_topic: Topic to consume from
            output_topic: Topic to produce to
            consumer_group: Consumer group ID
            auto_offset_reset: Where to start consuming (earliest/latest)
        """
        self.brokers = brokers
        self.input_topic = input_topic
        self.output_topic = output_topic
        self.consumer_group = consumer_group

        # Consumer configuration
        consumer_conf = {
            'bootstrap.servers': brokers,
            'group.id': consumer_group,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': False,  # Manual commit
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 30000,  # 30 seconds
        }

        # Producer configuration
        producer_conf = {
            'bootstrap.servers': brokers,
            'acks': 1,
            'compression.type': 'snappy',
            'linger.ms': 10,  # Batch messages for 10ms
            'batch.size': 16384,  # 16KB batches
        }

        self.consumer = Consumer(consumer_conf)
        self.producer = Producer(producer_conf)

        # Subscribe to input topic
        self.consumer.subscribe([input_topic])
        logger.info(f"Subscribed to topic: {input_topic}")

        # Delivery tracking
        self.messages_sent = 0
        self.messages_delivered = 0
        self.messages_failed = 0

    def consume(self, timeout: float = 1.0) -> Optional[Dict]:
        """
        Consume one message from input topic.

        Args:
            timeout: Timeout in seconds

        Returns:
            Message dict or None if timeout
        """
        try:
            msg = self.consumer.poll(timeout)

            if msg is None:
                return None

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition
                    return None
                else:
                    raise KafkaException(msg.error())

            # Decode message
            value = json.loads(msg.value().decode('utf-8'))

            return value

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error consuming message: {e}", exc_info=True)
            return None

    def produce(self, message: Dict, callback: Optional[Callable] = None):
        """
        Produce message to output topic.

        Args:
            message: Message dict to send
            callback: Optional delivery callback
        """
        try:
            # Use default callback if none provided
            if callback is None:
                callback = self._delivery_report

            # Serialize message
            value = json.dumps(message).encode('utf-8')

            # Produce message
            self.producer.produce(
                self.output_topic,
                value=value,
                callback=callback
            )

            self.messages_sent += 1

            # Poll to handle callbacks
            self.producer.poll(0)

        except BufferError:
            logger.warning("Local producer queue is full, waiting...")
            self.producer.flush()
            # Retry
            self.producer.produce(
                self.output_topic,
                value=value,
                callback=callback
            )
        except Exception as e:
            logger.error(f"Error producing message: {e}", exc_info=True)
            self.messages_failed += 1

    def _delivery_report(self, err, msg):
        """
        Default delivery callback.

        Args:
            err: Error if delivery failed
            msg: Delivered message
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
            self.messages_failed += 1
        else:
            self.messages_delivered += 1
            logger.debug(
                f"Message delivered to {msg.topic()} "
                f"[partition {msg.partition()}] at offset {msg.offset()}"
            )

    def commit(self):
        """
        Commit current offset.
        """
        try:
            self.consumer.commit(asynchronous=False)
        except Exception as e:
            logger.error(f"Error committing offset: {e}", exc_info=True)

    def flush(self, timeout: float = 30.0):
        """
        Flush producer queue.

        Args:
            timeout: Timeout in seconds
        """
        remaining = self.producer.flush(timeout)
        if remaining > 0:
            logger.warning(f"{remaining} messages not delivered after flush")

    def close(self):
        """
        Close consumer and producer.
        """
        logger.info("Closing Kafka client...")

        # Flush producer
        self.flush()

        # Close consumer
        self.consumer.close()

        logger.info(
            f"Kafka client closed. "
            f"Sent: {self.messages_sent}, "
            f"Delivered: {self.messages_delivered}, "
            f"Failed: {self.messages_failed}"
        )

    def get_stats(self) -> Dict:
        """
        Get client statistics.

        Returns:
            Dict with message counts
        """
        return {
            'messages_sent': self.messages_sent,
            'messages_delivered': self.messages_delivered,
            'messages_failed': self.messages_failed,
            'pending': self.messages_sent - self.messages_delivered - self.messages_failed
        }
