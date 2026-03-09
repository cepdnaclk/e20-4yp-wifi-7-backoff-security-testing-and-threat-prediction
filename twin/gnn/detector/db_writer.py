"""
Database Writer
Writes prediction results to TimescaleDB.
"""

import psycopg2
from psycopg2.extras import execute_batch
import json
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseWriter:
    """
    Writes GCN predictions to PostgreSQL/TimescaleDB.

    Uses batch inserts for efficiency.
    """

    def __init__(
        self,
        host: str,
        port: int,
        dbname: str,
        user: str,
        password: str,
        table: str = 'gcn_predictions',
        batch_size: int = 100
    ):
        """
        Initialize database writer.

        Args:
            host: Database host
            port: Database port
            dbname: Database name
            user: Database user
            password: Database password
            table: Table name
            batch_size: Batch insert size
        """
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password
        self.table = table
        self.batch_size = batch_size

        self.connection = None

        # Buffer for batch inserts
        self.buffer = []

    def connect(self) -> bool:
        """
        Connect to database.

        Returns:
            True if connection successful
        """
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            self.connection.autocommit = False

            logger.info(f"Connected to database: {self.dbname}@{self.host}")
            return True

        except Exception as e:
            logger.error(f"Error connecting to database: {e}", exc_info=True)
            return False

    def write_predictions(self, predictions: List[Dict]) -> bool:
        """
        Write predictions to database.

        Args:
            predictions: List of prediction dicts

        Returns:
            True if write successful
        """
        try:
            # Add to buffer
            self.buffer.extend(predictions)

            # Always flush immediately for real-time streaming.
            # Batching only makes sense for bulk inserts; in streaming mode
            # we typically get 1 prediction at a time and would never reach
            # batch_size, causing silent data loss.
            return self.flush()

        except Exception as e:
            logger.error(f"Error writing predictions: {e}", exc_info=True)
            return False

    def flush(self) -> bool:
        """
        Flush buffered predictions to database.

        Returns:
            True if flush successful
        """
        if not self.buffer:
            return True

        try:
            # Prepare values
            values = []
            for pred in self.buffer:
                values.append((
                    pred['experiment_id'],
                    pred['entity_id'],
                    pred['segment_id'],
                    pred['ts_start'],
                    pred['ts_end'],
                    pred['window_start_idx'],
                    pred['window_end_idx'],
                    pred['prediction'],
                    pred['confidence'],
                    json.dumps(pred['probabilities']),
                    pred['model_version'],
                    pred['model_path'],
                    pred.get('inference_time_ms'),
                    'gcn-detector'
                ))

            # Batch insert using a fresh cursor for each flush
            insert_query = f"""
                INSERT INTO {self.table} (
                    experiment_id, entity_id, segment_id,
                    ts_start, ts_end,
                    window_start_idx, window_end_idx,
                    prediction, confidence, probabilities,
                    model_version, model_path,
                    inference_time_ms, source
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """

            with self.connection.cursor() as cursor:
                execute_batch(cursor, insert_query, values, page_size=self.batch_size)
            self.connection.commit()

            logger.info(f"Flushed {len(self.buffer)} predictions to database")

            # Clear buffer
            self.buffer.clear()

            return True

        except Exception as e:
            logger.error(f"Error flushing predictions to database: {e}", exc_info=True)
            try:
                self.connection.rollback()
            except Exception:
                pass
            return False

    def close(self):
        """
        Close database connection.
        """
        try:
            # Flush remaining predictions
            self.flush()

            if self.connection:
                self.connection.close()

            logger.info("Database connection closed")

        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

    def check_connection(self) -> bool:
        """
        Check if database connection is alive.

        Returns:
            True if connection is alive
        """
        try:
            if self.connection is None:
                return False

            # Use connection.closed instead of executing a query
            # to avoid leaving an open transaction (idle in transaction state).
            if self.connection.closed != 0:
                return False

            # Poll with a lightweight no-op to detect broken pipes
            self.connection.poll()
            return True

        except Exception as e:
            logger.warning(f"Database connection check failed: {e}")
            return False

    def reconnect(self) -> bool:
        """
        Reconnect to database.

        Returns:
            True if reconnection successful
        """
        logger.info("Reconnecting to database...")

        try:
            self.close()
        except:
            pass

        return self.connect()
