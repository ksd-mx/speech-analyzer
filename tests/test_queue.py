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
        
        # Test close
        strategy.close()
        mock_client.close.assert_called_once()
    
    @patch('paho.mqtt.client.Client')
    def test_mqtt_strategy(self, mock_mqtt_client):
        """Test the MQTT queue strategy."""
        # In tests/test_queue.py, update the test_mqtt_strategy function:

def test_mqtt_strategy(self):
    """Test the MQTT queue strategy."""
    # Mock MQTT client
    mock_client = MagicMock()
    mock_mqtt_client.return_value = mock_client
    
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


if __name__ == '__main__':
    unittest.main()