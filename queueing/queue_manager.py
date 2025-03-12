"""
Queue Manager for handling message publishing and subscription using different strategies.
Provides a centralized interface for the application to interact with message queues.
"""
import os
import time
import logging
from typing import Dict, Any, Optional, List, Union, Callable

from queueing.queue_strategy import QueueStrategy, QueueStrategyFactory

# Configure logging
logger = logging.getLogger(__name__)

class QueueManager:
    """Manages queue operations using a specified strategy."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the QueueManager with the specified configuration.
        
        Args:
            config (Dict[str, Any], optional): Configuration dictionary. Defaults to None.
                If None, configuration is loaded from environment variables.
        """
        self.config = config or self._load_config_from_env()
        self.strategy: Optional[QueueStrategy] = None
        self.subscribers = {}  # Map of topic -> list of callbacks
        self.initialize()
    
    def _load_config_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        queue_type = os.environ.get("QUEUE_TYPE", "redis").lower()
        
        config = {
            "queue_type": queue_type,
            "enabled": os.environ.get("QUEUE_ENABLED", "true").lower() == "true"
        }
        
        # Redis-specific configuration
        if queue_type == "redis":
            config["redis_url"] = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        
        # MQTT-specific configuration
        elif queue_type == "mqtt":
            config["broker_url"] = os.environ.get("MQTT_BROKER_URL", "localhost")
            config["port"] = int(os.environ.get("MQTT_PORT", "1883"))
            config["client_id"] = os.environ.get("MQTT_CLIENT_ID", None)
            config["username"] = os.environ.get("MQTT_USERNAME", None)
            config["password"] = os.environ.get("MQTT_PASSWORD", None)
            config["qos"] = int(os.environ.get("MQTT_QOS", "0"))
            config["retain"] = os.environ.get("MQTT_RETAIN", "false").lower() == "true"
        
        return config
    
    def initialize(self) -> bool:
        """Initialize the queue strategy based on the configuration.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        if not self.config.get("enabled", True):
            logger.info("Queue functionality is disabled by configuration")
            return False
        
        queue_type = self.config.get("queue_type", "redis")
        
        try:
            # Create appropriate strategy based on queue type
            if queue_type == "redis":
                self.strategy = QueueStrategyFactory.create_strategy(
                    "redis",
                    url=self.config.get("redis_url", "redis://redis:6379/0")
                )
            elif queue_type == "mqtt":
                self.strategy = QueueStrategyFactory.create_strategy(
                    "mqtt",
                    broker_url=self.config.get("broker_url", "localhost"),
                    port=self.config.get("port", 1883),
                    client_id=self.config.get("client_id"),
                    username=self.config.get("username"),
                    password=self.config.get("password"),
                    qos=self.config.get("qos", 0),
                    retain=self.config.get("retain", False)
                )
            else:
                logger.warning(f"Unsupported queue type: {queue_type}. Falling back to logging strategy.")
                self.strategy = QueueStrategyFactory.create_strategy("logging")
            
            # Connect using the selected strategy
            return self.strategy.connect()
            
        except Exception as e:
            logger.error(f"Failed to initialize queue strategy: {str(e)}")
            # Fallback to logging strategy
            self.strategy = QueueStrategyFactory.create_strategy("logging")
            return False
    
    def publish(self, topic: str, data: Dict[str, Any]) -> bool:
        """Publish data to a topic using the configured strategy.
        
        Args:
            topic (str): The topic/channel to publish to.
            data (Dict[str, Any]): The data to publish.
            
        Returns:
            bool: True if publishing was successful, False otherwise.
        """
        if not self.config.get("enabled", True):
            logger.debug(f"Queue disabled, not publishing to {topic}")
            return False
        
        if self.strategy is None or not self.strategy.is_connected:
            if not self.initialize():
                logger.warning("Queue not initialized, cannot publish message")
                return False
        
        # Add timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return self.strategy.publish(topic, data)
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """Subscribe to a topic using the configured strategy.
        
        Args:
            topic (str): The topic/channel to subscribe to.
            callback (Callable): Function to call when a message is received.
                The callback should accept topic and message as arguments.
            
        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        if not self.config.get("enabled", True):
            logger.debug(f"Queue disabled, not subscribing to {topic}")
            return False
        
        if self.strategy is None or not self.strategy.is_connected:
            if not self.initialize():
                logger.warning("Queue not initialized, cannot subscribe to topic")
                return False
        
        # Add to subscribers dictionary for tracking
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        if callback not in self.subscribers[topic]:
            self.subscribers[topic].append(callback)
        
        # Use the strategy's subscribe method
        return self.strategy.subscribe(topic, callback)
    
    def unsubscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Unsubscribe from a topic using the configured strategy.
        
        Args:
            topic (str): The topic/channel to unsubscribe from.
            callback (Callable, optional): Specific callback to remove. 
                If None, all callbacks for this topic are removed.
            
        Returns:
            bool: True if unsubscription was successful, False otherwise.
        """
        if self.strategy is None or not self.strategy.is_connected:
            return False
        
        success = True
        
        # If a specific callback is provided, only remove that one
        if callback is not None and topic in self.subscribers:
            if callback in self.subscribers[topic]:
                self.subscribers[topic].remove(callback)
                
            # If there are no more callbacks for this topic, unsubscribe completely
            if not self.subscribers[topic]:
                success = self.strategy.unsubscribe(topic)
                if success:
                    del self.subscribers[topic]
        else:
            # Unsubscribe from the topic completely
            success = self.strategy.unsubscribe(topic)
            if success and topic in self.subscribers:
                del self.subscribers[topic]
        
        return success
    
    def close(self) -> None:
        """Close the queue connection and clean up subscriptions."""
        # Unsubscribe from all topics
        for topic in list(self.subscribers.keys()):
            self.unsubscribe(topic)
        
        # Close the strategy
        if self.strategy is not None:
            self.strategy.close()
            self.strategy = None
    
    @property
    def is_connected(self) -> bool:
        """Check if the queue is connected.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self.strategy is not None and self.strategy.is_connected
    
    @property
    def status(self) -> str:
        """Get the current status of the queue connection.
        
        Returns:
            str: Status description.
        """
        if not self.config.get("enabled", True):
            return "disabled"
        
        if self.strategy is None:
            return "not initialized"
        
        return self.strategy.status