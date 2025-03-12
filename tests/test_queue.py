"""
Tests for the queue management components.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, call

# Import queue components
from queueing.queue_strategy import (
    QueueStrategy, LoggingQueueStrategy, 
    RedisQueueStrategy, MQTTQueueStrategy,
    QueueStrategyFactory
)
from queueing.queue_manager import QueueManager
from queueing.queue_subscriber import QueueSubscriber


class TestQueueStrategies(unittest.TestCase):
    """Test cases for the queue strategies."""
    
    def test_logging_strategy(self):
        """Test the logging queue strategy."""
        strategy = LoggingQueueStrategy()
        
        # Test connect
        self.assertTrue(strategy.connect())
        self.assertTrue(strategy.is_connected)
        
        # Test publish
        with patch('logging.Logger.info') as mock_info:
            data = {"key": "value"}
            result = strategy.publish("test_topic", data)
            self.assertTrue(result)
            mock_info.assert_called()
        
        # Test subscribe
        mock_callback = MagicMock()
        with patch('logging.Logger.info') as mock_info:
            result = strategy.subscribe("test_topic", mock_callback)
            self.assertTrue(result)
            mock_info.assert_called()
            self.assertEqual(strategy.callbacks["test_topic"], mock_callback)
        
        # Test unsubscribe
        with patch('logging.Logger.info') as mock_info:
            result = strategy.unsubscribe("test_topic")
            self.assertTrue(result)
            mock_info.assert_called()
            self.assertNotIn("test_topic", strategy.callbacks)
        
        # Test close
        strategy.close()
        # Logging strategy is always connected
        self.assertTrue(strategy.is_connected)
    
    @patch('redis.from_url')
    def test_redis_strategy(self, mock_redis):
        """Test the Redis queue strategy."""
        # Mock Redis client
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        # Test connect
        strategy = RedisQueueStrategy(url="redis://localhost:6379/0")
        self.assertTrue(strategy.connect())
        mock_redis.assert_called_with("redis://localhost:6379/0")
        
        # Test publish
        mock_client.publish.return_value = 1
        data = {"key": "value"}
        result = strategy.publish("test_topic", data)
        self.assertTrue(result)
        mock_client.publish.assert_called_once()
        
        # Test subscribe
        mock_callback = MagicMock()
        mock_thread = MagicMock()
        mock_pubsub = MagicMock()
        strategy.pubsub = mock_pubsub
        
        with patch('threading.Thread', return_value=mock_thread) as mock_thread_class:
            result = strategy.subscribe("test_topic", mock_callback)
            self.assertTrue(result)
            mock_pubsub.subscribe.assert_called_once()
            mock_thread_class.assert_called_once()
            mock_thread.start.assert_called_once()
            self.assertEqual(strategy.callbacks["test_topic"], mock_callback)
        
        # Test unsubscribe
        result = strategy.unsubscribe("test_topic")
        self.assertTrue(result)
        mock_pubsub.unsubscribe.assert_called_with("test_topic")
        self.assertNotIn("test_topic", strategy.callbacks)
        
        # Test close
        strategy.close()
        self.assertIsNone(strategy.redis_client)
    
    def test_mqtt_strategy(self):
        """Test the MQTT queue strategy."""
        # Mock MQTT client
        mock_client = MagicMock()
        
        # Prepare for on_connect callback
        def on_connect_effect(client, userdata, flags, rc):
            # Simulate a successful connection by setting _connected to True
            strategy._connected = True
            strategy._status = "connected"
        
        # Set up mock behavior
        mock_client.on_connect = MagicMock(side_effect=on_connect_effect)
        mock_client.connect = MagicMock(return_value=None)
        
        # Create strategy
        with patch('paho.mqtt.client.Client', return_value=mock_client):
            strategy = MQTTQueueStrategy(broker_url="localhost", port=1883)
            
            # Manually trigger the connect callback to simulate successful connection
            strategy.connect()
            
            # Since we're not actually connecting, manually set connected state
            strategy._connected = True
            strategy._status = "connected"
            
            # Test publish
            mock_result = MagicMock()
            mock_result.rc = 0
            mock_client.publish.return_value = mock_result
            
            data = {"key": "value"}
            result = strategy.publish("test_topic", data)
            self.assertTrue(result)
            mock_client.publish.assert_called_once()
            
            # Test subscribe
            mock_callback = MagicMock()
            mock_subscribe_result = (0, None)  # Success result
            mock_client.subscribe.return_value = mock_subscribe_result
            
            result = strategy.subscribe("test_topic", mock_callback)
            self.assertTrue(result)
            mock_client.subscribe.assert_called_once()
            self.assertEqual(strategy.callbacks["test_topic"], mock_callback)
            
            # Test unsubscribe
            mock_unsubscribe_result = (0, None)  # Success result
            mock_client.unsubscribe.return_value = mock_unsubscribe_result
            
            result = strategy.unsubscribe("test_topic")
            self.assertTrue(result)
            mock_client.unsubscribe.assert_called_once()
            self.assertNotIn("test_topic", strategy.callbacks)
            
            # Reset the mock before testing close
            mock_client.loop_stop.reset_mock()
            mock_client.disconnect.reset_mock()
            
            # Test close
            strategy.close()
            mock_client.loop_stop.assert_called_once()
            mock_client.disconnect.assert_called_once()


class TestQueueStrategyFactory(unittest.TestCase):
    """Test cases for the QueueStrategyFactory."""
    
    def test_create_logging_strategy(self):
        """Test creation of LoggingQueueStrategy."""
        strategy = QueueStrategyFactory.create_strategy("logging")
        self.assertIsInstance(strategy, LoggingQueueStrategy)
    
    @patch('queueing.queue_strategy.RedisQueueStrategy.__init__', return_value=None)
    def test_create_redis_strategy(self, mock_init):
        """Test creation of RedisQueueStrategy."""
        strategy = QueueStrategyFactory.create_strategy("redis", url="redis://localhost:6379/0")
        self.assertIsInstance(strategy, RedisQueueStrategy)
        mock_init.assert_called_with(url="redis://localhost:6379/0")
    
    @patch('queueing.queue_strategy.MQTTQueueStrategy.__init__', return_value=None)
    def test_create_mqtt_strategy(self, mock_init):
        """Test creation of MQTTQueueStrategy."""
        strategy = QueueStrategyFactory.create_strategy(
            "mqtt", 
            broker_url="localhost",
            port=1883
        )
        self.assertIsInstance(strategy, MQTTQueueStrategy)
        mock_init.assert_called_with(broker_url="localhost", port=1883)
    
    def test_create_invalid_strategy(self):
        """Test handling of invalid strategy type."""
        strategy = QueueStrategyFactory.create_strategy("invalid")
        self.assertIsInstance(strategy, LoggingQueueStrategy)


class TestQueueManager(unittest.TestCase):
    """Test cases for the QueueManager."""
    
    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_initialize_redis(self, mock_create_strategy):
        """Test initialization with Redis."""
        # Mock strategy
        mock_strategy = MagicMock()
        mock_strategy.connect.return_value = True
        mock_create_strategy.return_value = mock_strategy
        
        # Create QueueManager with Redis config
        config = {
            "queue_type": "redis",
            "enabled": True,
            "redis_url": "redis://localhost:6379/0"
        }
        manager = QueueManager(config)
        
        # Assert strategy was created properly
        mock_create_strategy.assert_called_with(
            "redis", url="redis://localhost:6379/0"
        )
        mock_strategy.connect.assert_called_once()
        self.assertEqual(manager.strategy, mock_strategy)
    
    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_initialize_mqtt(self, mock_create_strategy):
        """Test initialization with MQTT."""
        # Mock strategy
        mock_strategy = MagicMock()
        mock_strategy.connect.return_value = True
        mock_create_strategy.return_value = mock_strategy
        
        # Create QueueManager with MQTT config
        config = {
            "queue_type": "mqtt",
            "enabled": True,
            "broker_url": "localhost",
            "port": 1883,
            "client_id": "test_client",
            "username": None,
            "password": None,
            "qos": 0,
            "retain": False
        }
        manager = QueueManager(config)
        
        # Assert strategy was created properly
        mock_create_strategy.assert_called_with(
            "mqtt", 
            broker_url="localhost",
            port=1883,
            client_id="test_client",
            username=None,
            password=None,
            qos=0,
            retain=False
        )
        mock_strategy.connect.assert_called_once()
    
    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_publish(self, mock_create_strategy):
        """Test publishing messages."""
        # Mock strategy
        mock_strategy = MagicMock()
        mock_strategy.is_connected = True
        mock_strategy.connect.return_value = True
        mock_strategy.publish.return_value = True
        mock_create_strategy.return_value = mock_strategy
        
        # Create QueueManager
        config = {"queue_type": "logging", "enabled": True}
        manager = QueueManager(config)
        
        # Test publishing
        data = {"key": "value"}
        result = manager.publish("test_topic", data)
        self.assertTrue(result)
        mock_strategy.publish.assert_called_with("test_topic", data)

    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_subscribe(self, mock_create_strategy):
        """Test subscribing to topics."""
        # Mock strategy
        mock_strategy = MagicMock()
        mock_strategy.is_connected = True
        mock_strategy.connect.return_value = True
        mock_strategy.subscribe.return_value = True
        mock_create_strategy.return_value = mock_strategy
        
        # Create QueueManager
        config = {"queue_type": "logging", "enabled": True}
        manager = QueueManager(config)
        
        # Test subscribing
        mock_callback = MagicMock()
        result = manager.subscribe("test_topic", mock_callback)
        self.assertTrue(result)
        mock_strategy.subscribe.assert_called_with("test_topic", mock_callback)
        self.assertIn("test_topic", manager.subscribers)
        self.assertIn(mock_callback, manager.subscribers["test_topic"])

    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_unsubscribe(self, mock_create_strategy):
        """Test unsubscribing from topics."""
        # Mock strategy
        mock_strategy = MagicMock()
        mock_strategy.is_connected = True
        mock_strategy.connect.return_value = True
        mock_strategy.subscribe.return_value = True
        mock_strategy.unsubscribe.return_value = True
        mock_create_strategy.return_value = mock_strategy
        
        # Create QueueManager
        config = {"queue_type": "logging", "enabled": True}
        manager = QueueManager(config)
        
        # Add a subscription
        mock_callback = MagicMock()
        manager.subscribe("test_topic", mock_callback)
        
        # Test unsubscribing
        result = manager.unsubscribe("test_topic")
        self.assertTrue(result)
        mock_strategy.unsubscribe.assert_called_with("test_topic")
        self.assertNotIn("test_topic", manager.subscribers)
    
    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_publish_disabled(self, mock_create_strategy):
        """Test publishing when queue is disabled."""
        # Create QueueManager with queue disabled
        config = {"queue_type": "logging", "enabled": False}
        manager = QueueManager(config)
        
        # Test publishing
        data = {"key": "value"}
        result = manager.publish("test_topic", data)
        self.assertFalse(result)
        mock_create_strategy.assert_not_called()

    @patch('queueing.queue_manager.QueueStrategyFactory.create_strategy')
    def test_subscribe_disabled(self, mock_create_strategy):
        """Test subscribing when queue is disabled."""
        # Create QueueManager with queue disabled
        config = {"queue_type": "logging", "enabled": False}
        manager = QueueManager(config)
        
        # Test subscribing
        mock_callback = MagicMock()
        result = manager.subscribe("test_topic", mock_callback)
        self.assertFalse(result)
        mock_create_strategy.assert_not_called()


class TestQueueSubscriber(unittest.TestCase):
    """Test cases for the QueueSubscriber."""
    
    @patch('queueing.queue_subscriber.QueueManager')
    def test_subscribe(self, mock_queue_manager_class):
        """Test subscribing to a topic."""
        # Mock queue manager
        mock_queue_manager = MagicMock()
        mock_queue_manager.subscribe.return_value = True
        mock_queue_manager_class.return_value = mock_queue_manager
        
        # Create subscriber
        subscriber = QueueSubscriber()
        
        # Test subscribing with custom callback
        mock_callback = MagicMock()
        result = subscriber.subscribe("test_topic", mock_callback)
        self.assertTrue(result)
        mock_queue_manager.subscribe.assert_called_with("test_topic", mock_callback)
        self.assertIn("test_topic", subscriber.subscribed_topics)
        self.assertIn(mock_callback, subscriber.callbacks["test_topic"])
        
        # Test subscribing with default callback
        result = subscriber.subscribe("another_topic")
        self.assertTrue(result)
        # Second call to subscribe should use the default callback
        second_call_args = mock_queue_manager.subscribe.call_args_list[1]
        self.assertEqual(second_call_args[0][0], "another_topic")
        # The second argument should be a callable (the default callback)
        self.assertTrue(callable(second_call_args[0][1]))
    
    @patch('queueing.queue_subscriber.QueueManager')
    def test_unsubscribe(self, mock_queue_manager_class):
        """Test unsubscribing from a topic."""
        # Mock queue manager
        mock_queue_manager = MagicMock()
        mock_queue_manager.subscribe.return_value = True
        mock_queue_manager.unsubscribe.return_value = True
        mock_queue_manager_class.return_value = mock_queue_manager
        
        # Create subscriber
        subscriber = QueueSubscriber()
        
        # Add a subscription
        mock_callback = MagicMock()
        subscriber.subscribe("test_topic", mock_callback)
        
        # Test unsubscribing
        result = subscriber.unsubscribe("test_topic")
        self.assertTrue(result)
        mock_queue_manager.unsubscribe.assert_called_with("test_topic", None)
        self.assertNotIn("test_topic", subscriber.subscribed_topics)
    
    @patch('queueing.queue_subscriber.QueueManager')
    def test_close(self, mock_queue_manager_class):
        """Test closing the subscriber."""
        # Mock queue manager
        mock_queue_manager = MagicMock()
        mock_queue_manager.subscribe.return_value = True
        mock_queue_manager_class.return_value = mock_queue_manager
        
        # Create subscriber
        subscriber = QueueSubscriber()
        
        # Add some subscriptions
        subscriber.subscribe("topic1")
        subscriber.subscribe("topic2")
        
        # Test closing
        subscriber.close()
        self.assertFalse(subscriber.running)
        mock_queue_manager.close.assert_called_once()
        self.assertEqual(len(subscriber.subscribed_topics), 0)


if __name__ == '__main__':
    unittest.main()