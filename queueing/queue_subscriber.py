"""
Queue Subscription Client
Provides a generic interface for subscribing to queue messages.
"""
import os
import json
import time
import signal
import logging
from typing import Dict, Any, Optional, Callable, List, Union

from queueing.queue_manager import QueueManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class QueueSubscriber:
    """Generic subscriber for queue messages."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Queue Subscriber.
        
        Args:
            config (Dict[str, Any], optional): Configuration dictionary.
                If None, configuration is loaded from environment variables.
        """
        self.queue_manager = QueueManager(config)
        self.subscribed_topics = set()
        self.running = False
        self.callbacks = {}  # Map of topic -> list of callbacks
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle signals for graceful shutdown."""
        logger.info("Shutdown signal received, closing connections...")
        self.close()
    
    def subscribe(self, topic: str, callback: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> bool:
        """Subscribe to a topic.
        
        Args:
            topic (str): The topic to subscribe to.
            callback (Callable, optional): Function to call when a message is received.
                If None, the default_callback will be used.
                
        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        if not callback:
            callback = self.default_callback
            
        # Store the callback locally
        if topic not in self.callbacks:
            self.callbacks[topic] = []
        
        if callback not in self.callbacks[topic]:
            self.callbacks[topic].append(callback)
        
        # Subscribe using the queue manager
        success = self.queue_manager.subscribe(topic, callback)
        
        if success:
            self.subscribed_topics.add(topic)
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to subscribe to topic: {topic}")
            
        return success
    
    def unsubscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Unsubscribe from a topic.
        
        Args:
            topic (str): The topic to unsubscribe from.
            callback (Callable, optional): Specific callback to remove.
                If None, all callbacks for this topic are removed.
                
        Returns:
            bool: True if unsubscription was successful, False otherwise.
        """
        success = self.queue_manager.unsubscribe(topic, callback)
        
        if success:
            if callback is None:
                if topic in self.callbacks:
                    del self.callbacks[topic]
                self.subscribed_topics.discard(topic)
                logger.info(f"Unsubscribed from topic: {topic}")
            else:
                if topic in self.callbacks and callback in self.callbacks[topic]:
                    self.callbacks[topic].remove(callback)
                    logger.info(f"Removed callback from topic: {topic}")
        else:
            logger.error(f"Failed to unsubscribe from topic: {topic}")
            
        return success
    
    def default_callback(self, topic: str, message: Dict[str, Any]) -> None:
        """Default callback for received messages.
        
        Args:
            topic (str): The topic the message was received on.
            message (Dict[str, Any]): The received message.
        """
        logger.info(f"Message received on topic '{topic}':")
        logger.info(json.dumps(message, indent=2))
    
    def close(self) -> None:
        """Close all subscriptions and connections."""
        self.running = False
        
        # Unsubscribe from all topics
        for topic in list(self.subscribed_topics):
            self.unsubscribe(topic)
        
        # Close the queue manager
        self.queue_manager.close()
        
        logger.info("Subscriber closed")
    
    def run_forever(self) -> None:
        """Run in a blocking loop to receive messages."""
        self.running = True
        logger.info("Subscriber running, press Ctrl+C to stop...")
        
        try:
            while self.running:
                # Just keep the process alive to receive messages asynchronously
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.close()