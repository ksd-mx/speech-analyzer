"""
Message Queue Strategy Pattern implementation.
Provides interfaces and concrete implementations for different queue services.
"""
import json
import logging
import abc
import threading
from typing import Dict, Any, Optional, Callable, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class QueueStrategy(abc.ABC):
    """Abstract base class for queue publishing strategies."""
    
    @abc.abstractmethod
    def connect(self) -> bool:
        """Establish connection to the queue service.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def publish(self, topic: str, data: Dict[str, Any]) -> bool:
        """Publish data to a specific topic.
        
        Args:
            topic (str): The topic/channel to publish to.
            data (Dict[str, Any]): The data to publish.
            
        Returns:
            bool: True if publishing was successful, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """Subscribe to a specific topic.
        
        Args:
            topic (str): The topic/channel to subscribe to.
            callback (Callable): Function to call when a message is received.
                The callback should accept topic and message as arguments.
            
        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a specific topic.
        
        Args:
            topic (str): The topic/channel to unsubscribe from.
            
        Returns:
            bool: True if unsubscribe was successful, False otherwise.
        """
        pass
    
    @abc.abstractmethod
    def close(self) -> None:
        """Close the connection to the queue service."""
        pass
    
    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check if the connection is active.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        pass
    
    @property
    @abc.abstractmethod
    def status(self) -> str:
        """Get the current status of the queue connection.
        
        Returns:
            str: Status description (e.g., "connected", "disconnected", "error").
        """
        pass


class RedisQueueStrategy(QueueStrategy):
    """Redis implementation of the QueueStrategy."""
    
    def __init__(self, url: str):
        """Initialize the Redis queue strategy.
        
        Args:
            url (str): Redis connection URL (e.g., "redis://localhost:6379/0").
        """
        self.redis_url = url
        self.redis_client = None
        self.pubsub = None
        self.subscription_threads = {}  # Keep track of subscription threads
        self.callbacks = {}  # Map of topic -> callback
        self._status = "initialized"
    
    def connect(self) -> bool:
        """Establish connection to Redis.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        if self.redis_client is not None:
            return True
            
        try:
            import redis
            self.redis_client = redis.from_url(self.redis_url)
            self.redis_client.ping()  # Test connection
            self.pubsub = self.redis_client.pubsub()
            self._status = "connected"
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            self._status = f"error: {str(e)}"
            logger.error(f"Redis connection error: {str(e)}")
            self.redis_client = None
            return False
    
    def publish(self, topic: str, data: Dict[str, Any]) -> bool:
        """Publish data to a Redis topic and store in history.
        
        Args:
            topic (str): The Redis channel to publish to.
            data (Dict[str, Any]): The data to publish.
            
        Returns:
            bool: True if publishing was successful, False otherwise.
        """
        if self.redis_client is None and not self.connect():
            return False
            
        try:
            message = json.dumps(data)
            self.redis_client.publish(topic, message)
            logger.info(f"Published message to Redis topic '{topic}'")
            
            # Also store in a Redis list for persistence
            list_key = f"history:{topic}"
            self.redis_client.lpush(list_key, message)
            # Trim the list to keep only last 100 messages
            self.redis_client.ltrim(list_key, 0, 99)
            
            return True
        except Exception as e:
            logger.error(f"Failed to publish to Redis queue: {str(e)}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """Subscribe to a Redis topic.
        
        Args:
            topic (str): The Redis channel to subscribe to.
            callback (Callable): Function to call when a message is received.
            
        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        if self.redis_client is None and not self.connect():
            return False
            
        try:
            # Store the callback
            self.callbacks[topic] = callback
            
            # Subscribe to the topic
            self.pubsub.subscribe(**{topic: self._message_handler})
            
            # Start a thread to listen for messages
            if topic not in self.subscription_threads:
                thread = threading.Thread(
                    target=self._listen_for_messages,
                    args=(topic,),
                    daemon=True
                )
                thread.start()
                self.subscription_threads[topic] = thread
                
            logger.info(f"Subscribed to Redis topic '{topic}'")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis topic '{topic}': {str(e)}")
            return False
    
    def _message_handler(self, message):
        """Handle incoming Redis messages."""
        if message['type'] == 'message':
            topic = message['channel'].decode('utf-8')
            data = message['data'].decode('utf-8')
            
            if topic in self.callbacks:
                try:
                    # Parse the JSON data
                    data_dict = json.loads(data)
                    # Call the callback with topic and data
                    self.callbacks[topic](topic, data_dict)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message from Redis topic '{topic}': {data}")
                except Exception as e:
                    logger.error(f"Error in Redis callback for topic '{topic}': {str(e)}")
    
    def _listen_for_messages(self, topic: str):
        """Listen for messages on a specific topic."""
        try:
            logger.info(f"Starting Redis subscription listener for topic '{topic}'")
            self.pubsub.run_in_thread(sleep_time=0.01)
        except Exception as e:
            logger.error(f"Redis subscription listener failed for topic '{topic}': {str(e)}")
    
    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a Redis topic.
        
        Args:
            topic (str): The Redis channel to unsubscribe from.
            
        Returns:
            bool: True if unsubscribe was successful, False otherwise.
        """
        if self.pubsub is None:
            return False
            
        try:
            self.pubsub.unsubscribe(topic)
            
            # Remove the callback
            if topic in self.callbacks:
                del self.callbacks[topic]
                
            # Thread will terminate on its own
            if topic in self.subscription_threads:
                del self.subscription_threads[topic]
                
            logger.info(f"Unsubscribed from Redis topic '{topic}'")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from Redis topic '{topic}': {str(e)}")
            return False
    
    def close(self) -> None:
        """Close the Redis connection."""
        if self.pubsub is not None:
            try:
                # Unsubscribe from all topics
                for topic in list(self.callbacks.keys()):
                    self.unsubscribe(topic)
                
                self.pubsub.close()
                self.pubsub = None
            except Exception as e:
                logger.error(f"Error closing Redis PubSub: {str(e)}")
                
        if self.redis_client is not None:
            # Redis connections are automatically pooled, so there's no explicit
            # close method we need to call, but we'll reset our client reference
            if hasattr(self.redis_client, 'close'):
                self.redis_client.close()
            self.redis_client = None
            self._status = "disconnected"
            logger.info("Redis connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        if self.redis_client is None:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    @property
    def status(self) -> str:
        """Get Redis connection status.
        
        Returns:
            str: Status description.
        """
        if self.is_connected:
            return "connected"
        return self._status


class MQTTQueueStrategy(QueueStrategy):
    """MQTT implementation of the QueueStrategy."""
    
    def __init__(self, broker_url: str, port: int = 1883, client_id: Optional[str] = None,
                 username: Optional[str] = None, password: Optional[str] = None,
                 qos: int = 0, retain: bool = False):
        """Initialize the MQTT queue strategy.
        
        Args:
            broker_url (str): MQTT broker URL/hostname.
            port (int, optional): MQTT broker port. Defaults to 1883.
            client_id (str, optional): Client identifier. Defaults to None (auto-generated).
            username (str, optional): Username for authentication. Defaults to None.
            password (str, optional): Password for authentication. Defaults to None.
            qos (int, optional): Quality of Service level (0, 1, or 2). Defaults to 0.
            retain (bool, optional): Whether to retain messages. Defaults to False.
        """
        import uuid
        self.broker_url = broker_url
        self.port = port
        self.client_id = client_id or f"mosque-audio-{uuid.uuid4().hex[:8]}"
        self.username = username
        self.password = password
        self.qos = qos
        self.retain = retain
        self.client = None
        self._status = "initialized"
        self._connected = False
        self.callbacks = {}  # Map of topic -> callback
        self.subscribed_topics = set()  # Keep track of subscribed topics
    
    def connect(self) -> bool:
        """Establish connection to MQTT broker.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        if self.client is not None and self.is_connected:
            return True
            
        try:
            import paho.mqtt.client as mqtt
            
            # Callback for successful connection
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    self._status = "connected"
                    self._connected = True
                    logger.info(f"Connected to MQTT broker at {self.broker_url}:{self.port}")
                    
                    # Resubscribe to topics if any
                    for topic in self.subscribed_topics:
                        client.subscribe(topic, self.qos)
                else:
                    self._status = f"error: connection failed (code {rc})"
                    logger.error(f"MQTT connection failed with code {rc}")
            
            # Callback for message reception
            def on_message(client, userdata, msg):
                try:
                    topic = msg.topic
                    payload = msg.payload.decode('utf-8')
                    
                    if topic in self.callbacks:
                        try:
                            # Parse the JSON data
                            data = json.loads(payload)
                            # Call the callback
                            self.callbacks[topic](topic, data)
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse message from MQTT topic '{topic}': {payload}")
                        except Exception as e:
                            logger.error(f"Error in MQTT callback for topic '{topic}': {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing MQTT message: {str(e)}")
            
            # Create client and set callbacks
            self.client = mqtt.Client(client_id=self.client_id)
            self.client.on_connect = on_connect
            self.client.on_message = on_message
            
            # Set username and password if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Connect to broker
            self.client.connect(self.broker_url, self.port)
            
            # Start the loop in a non-blocking way
            self.client.loop_start()
            
            # Give some time for the connection to establish
            import time
            timeout = time.time() + 5.0  # 5 seconds timeout
            while time.time() < timeout:
                if self._status == "connected":
                    return True
                time.sleep(0.1)
            
            # If we reach here, connection wasn't established within timeout
            self.close()
            self._status = "error: connection timeout"
            logger.error("MQTT connection timeout")
            return False
            
        except ImportError:
            self._status = "error: paho-mqtt not installed"
            logger.error("paho-mqtt library not installed. Install with: pip install paho-mqtt")
            return False
        except Exception as e:
            self._status = f"error: {str(e)}"
            logger.error(f"MQTT connection error: {str(e)}")
            return False
    
    def publish(self, topic: str, data: Dict[str, Any]) -> bool:
        """Publish data to an MQTT topic.
        
        Args:
            topic (str): The MQTT topic to publish to.
            data (Dict[str, Any]): The data to publish.
            
        Returns:
            bool: True if publishing was successful, False otherwise.
        """
        if not self.is_connected and not self.connect():
            return False
            
        try:
            message = json.dumps(data)
            result = self.client.publish(topic, message, qos=self.qos, retain=self.retain)
            
            if result.rc == 0:
                logger.info(f"Published message to MQTT topic '{topic}'")
                return True
            else:
                logger.error(f"Failed to publish to MQTT topic '{topic}' (code {result.rc})")
                return False
        except Exception as e:
            logger.error(f"Failed to publish to MQTT queue: {str(e)}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """Subscribe to an MQTT topic.
        
        Args:
            topic (str): The MQTT topic to subscribe to.
            callback (Callable): Function to call when a message is received.
            
        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        if not self.is_connected and not self.connect():
            return False
            
        try:
            # Store the callback
            self.callbacks[topic] = callback
            self.subscribed_topics.add(topic)
            
            # Subscribe to the topic
            result, _ = self.client.subscribe(topic, self.qos)
            
            if result == 0:
                logger.info(f"Subscribed to MQTT topic '{topic}'")
                return True
            else:
                logger.error(f"Failed to subscribe to MQTT topic '{topic}' (code {result})")
                return False
        except Exception as e:
            logger.error(f"Failed to subscribe to MQTT topic '{topic}': {str(e)}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from an MQTT topic.
        
        Args:
            topic (str): The MQTT topic to unsubscribe from.
            
        Returns:
            bool: True if unsubscribe was successful, False otherwise.
        """
        if not self.is_connected:
            return False
            
        try:
            # Unsubscribe from the topic
            result, _ = self.client.unsubscribe(topic)
            
            # Remove from our tracking
            if topic in self.callbacks:
                del self.callbacks[topic]
            self.subscribed_topics.discard(topic)
            
            if result == 0:
                logger.info(f"Unsubscribed from MQTT topic '{topic}'")
                return True
            else:
                logger.error(f"Failed to unsubscribe from MQTT topic '{topic}' (code {result})")
                return False
        except Exception as e:
            logger.error(f"Failed to unsubscribe from MQTT topic '{topic}': {str(e)}")
            return False
    
    def close(self) -> None:
        """Disconnect and close the MQTT client."""
        if self.client is not None:
            try:
                # Unsubscribe from all topics
                for topic in list(self.callbacks.keys()):
                    self.unsubscribe(topic)
                
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass  # Ignore errors during disconnection
            finally:
                self.client = None
                self._connected = False
                self._status = "disconnected"
                logger.info("MQTT connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MQTT broker.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self.client is not None and self._connected
    
    @property
    def status(self) -> str:
        """Get MQTT connection status.
        
        Returns:
            str: Status description.
        """
        return self._status


class LoggingQueueStrategy(QueueStrategy):
    """Fallback strategy that just logs messages without sending to any queue.
    Useful for testing or when no queue service is available.
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """Initialize the logging queue strategy.
        
        Args:
            log_level (int, optional): Logging level. Defaults to logging.INFO.
        """
        self.log_level = log_level
        self._status = "connected"  # Always connected
        self.callbacks = {}  # Map of topic -> callback
    
    def connect(self) -> bool:
        """No actual connection needed for logging.
        
        Returns:
            bool: Always returns True.
        """
        return True
    
    def publish(self, topic: str, data: Dict[str, Any]) -> bool:
        """Log the message that would be published.
        
        Args:
            topic (str): The topic that would be published to.
            data (Dict[str, Any]): The data that would be published.
            
        Returns:
            bool: Always returns True.
        """
        message = json.dumps(data, indent=2)
        logger.info(f"[MOCK QUEUE] Would publish to topic '{topic}':\n{message}")
        return True
    
    def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]) -> bool:
        """Log the subscription that would be made.
        
        Args:
            topic (str): The topic that would be subscribed to.
            callback (Callable): Function that would be called for messages.
            
        Returns:
            bool: Always returns True.
        """
        self.callbacks[topic] = callback
        logger.info(f"[MOCK QUEUE] Would subscribe to topic '{topic}'")
        return True
    
    def unsubscribe(self, topic: str) -> bool:
        """Log the unsubscription that would be made.
        
        Args:
            topic (str): The topic that would be unsubscribed from.
            
        Returns:
            bool: Always returns True.
        """
        if topic in self.callbacks:
            del self.callbacks[topic]
        logger.info(f"[MOCK QUEUE] Would unsubscribe from topic '{topic}'")
        return True
    
    def close(self) -> None:
        """No actual connection to close for logging."""
        self.callbacks.clear()
        pass
    
    @property
    def is_connected(self) -> bool:
        """Always returns True for logging strategy.
        
        Returns:
            bool: Always True.
        """
        return True
    
    @property
    def status(self) -> str:
        """Get logging queue status.
        
        Returns:
            str: Always "connected".
        """
        return self._status


class QueueStrategyFactory:
    """Factory for creating QueueStrategy instances."""
    
    @staticmethod
    def create_strategy(queue_type: str, **kwargs) -> QueueStrategy:
        """Create a QueueStrategy instance based on the specified type.
        
        Args:
            queue_type (str): The type of queue strategy to create ("redis", "mqtt", "logging").
            **kwargs: Additional arguments to pass to the strategy constructor.
            
        Returns:
            QueueStrategy: A concrete QueueStrategy implementation.
            
        Raises:
            ValueError: If an unsupported queue_type is specified.
        """
        if queue_type.lower() == "redis":
            return RedisQueueStrategy(**kwargs)
        elif queue_type.lower() == "mqtt":
            return MQTTQueueStrategy(**kwargs)
        elif queue_type.lower() == "logging":
            return LoggingQueueStrategy(**kwargs)
        else:
            # Instead of raising ValueError, return LoggingQueueStrategy as fallback
            logging.warning(f"Unsupported queue type: {queue_type}. Falling back to logging strategy.")
            return LoggingQueueStrategy(**kwargs)