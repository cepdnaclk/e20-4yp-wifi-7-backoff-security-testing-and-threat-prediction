"""
Health API
Simple Flask API for health checks and status.
"""

from flask import Flask, jsonify
import logging
from typing import Dict, Callable
import time

logger = logging.getLogger(__name__)

app = Flask(__name__)


class HealthAPI:
    """
    Health check API for GCN detector.

    Provides endpoints for:
    - /health - Basic health check
    - /status - Detailed status information
    """

    def __init__(self, port: int = 8080):
        """
        Initialize health API.

        Args:
            port: Port to run on
        """
        self.port = port
        self.start_time = time.time()

        # Callbacks for status checks
        self.model_loaded_callback = None
        self.kafka_connected_callback = None
        self.db_connected_callback = None
        self.get_stats_callback = None

    def set_callbacks(
        self,
        model_loaded: Callable = None,
        kafka_connected: Callable = None,
        db_connected: Callable = None,
        get_stats: Callable = None
    ):
        """
        Set callbacks for status checks.

        Args:
            model_loaded: Function that returns True if model is loaded
            kafka_connected: Function that returns True if Kafka is connected
            db_connected: Function that returns True if DB is connected
            get_stats: Function that returns stats dict
        """
        self.model_loaded_callback = model_loaded
        self.kafka_connected_callback = kafka_connected
        self.db_connected_callback = db_connected
        self.get_stats_callback = get_stats

    def get_health(self) -> Dict:
        """
        Get health status.

        Returns:
            Health status dict
        """
        model_loaded = self.model_loaded_callback() if self.model_loaded_callback else False
        kafka_connected = self.kafka_connected_callback() if self.kafka_connected_callback else False
        db_connected = self.db_connected_callback() if self.db_connected_callback else False

        # Overall health
        healthy = model_loaded and kafka_connected and db_connected

        return {
            'status': 'healthy' if healthy else 'unhealthy',
            'model_loaded': model_loaded,
            'kafka_connected': kafka_connected,
            'db_connected': db_connected,
            'uptime_seconds': int(time.time() - self.start_time)
        }

    def get_status(self) -> Dict:
        """
        Get detailed status.

        Returns:
            Status dict with statistics
        """
        health = self.get_health()

        # Add stats if available
        if self.get_stats_callback:
            stats = self.get_stats_callback()
            health.update(stats)

        return health

    def run(self):
        """
        Run Flask server in background thread.
        """
        @app.route('/health', methods=['GET'])
        def health_endpoint():
            return jsonify(self.get_health())

        @app.route('/status', methods=['GET'])
        def status_endpoint():
            return jsonify(self.get_status())

        # Run in production mode (no debug)
        logger.info(f"Starting health API on port {self.port}")
        app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
