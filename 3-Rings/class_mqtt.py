"""
class_mqtt.py — MQTT client factory for ESP32 (MicroPython).

Wraps ``umqtt.robust.MQTTClient`` with JSON-based credential loading.
The returned client object is used directly by the caller for
``subscribe`` / ``check_msg`` / ``set_callback`` operations so that
reconnect and error handling remain the caller's responsibility.

Credentials file format (``secrets_mqtt.json``)::

    {
        "secretHost": "192.168.1.10",
        "secretPort": "1883",
        "secretUser": "mqttuser",
        "secretPass": "mqttpass"
    }

Typical usage::

    from class_mqtt import MQTT

    mqtt   = MQTT("secrets_mqtt.json")
    client = mqtt.connect(b"esp32-monitor", keepalive=60)
    client.set_callback(on_message)
    client.subscribe(b"sensors/#")
"""

import ujson
from umqtt.robust import MQTTClient


class MQTT:
    """MQTT client factory that loads broker credentials from a JSON file.

    Args:
        mqtt_json_file (str): Path to the credentials JSON file on the
                              device filesystem. Default: ``secrets_mqtt.json``.

    Raises:
        OSError:   If the credentials file cannot be opened.
        KeyError:  If a required key is missing from the JSON.
    """

    def __init__(self, mqtt_json_file="secrets_mqtt.json"):
        with open(mqtt_json_file) as f:
            cfg = ujson.load(f)
        self.broker   = cfg["secretHost"]
        self.port     = int(cfg["secretPort"])   # ensure int
        self.username = cfg["secretUser"]
        self.password = cfg["secretPass"]
        self.client   = None
        print("MQTT broker:", self.broker, "port:", self.port, "user:", self.username)

    def connect(self, client_id, keepalive=60):
        """Connect to the broker and return the active ``MQTTClient`` object.

        The caller is responsible for setting a callback, subscribing to
        topics, and calling ``check_msg()`` in the main loop.

        Args:
            client_id (bytes): Unique MQTT client identifier.
            keepalive (int):   Keep-alive interval in seconds. The broker
                               will send a PINGREQ if no traffic is seen
                               within this window. Default: 60.

        Returns:
            MQTTClient: Connected client instance.

        Raises:
            OSError: If the TCP connection to the broker fails.
        """
        self.client = MQTTClient(
            client_id,
            self.broker,
            self.port,
            self.username,
            self.password,
            keepalive=keepalive,
        )
        self.client.connect()
        print("MQTT connected to", self.broker)
        return self.client

    def publish(self, topic, value, retain=False):
        """Publish *value* to *topic*.

        Args:
            topic (bytes or str): MQTT topic string.
            value:                Value to publish; converted to ``str`` automatically.
            retain (bool):        Set the MQTT retain flag. Default: False.

        Returns:
            bool: ``True`` on success, ``False`` if no client is connected.
        """
        if self.client is None:
            return False
        try:
            self.client.publish(topic, str(value), retain=retain)
            return True
        except Exception as e:
            print("MQTT publish failed:", e)
            return False
