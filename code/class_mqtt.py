# class_mqtt.py
# MQTT wrapper for ESP32 (MicroPython, umqtt.robust)
# FIX: errorcount scope (was UnboundLocalError), added keepalive param,
#      removed unused imports, clean exception handling.

import ujson
from umqtt.robust import MQTTClient


class MQTT:
    """Connect ESP32 to a MQTT broker. Credentials loaded from JSON file."""

    def __init__(self, mqtt_json_file="secrets_mqtt.json"):
        cfg = ujson.load(open(mqtt_json_file))
        self.broker   = cfg["secretHost"]
        self.port     = int(cfg["secretPort"])   # ensure int
        self.username = cfg["secretUser"]
        self.password = cfg["secretPass"]
        self.client   = None
        print("MQTT broker:", self.broker, "port:", self.port, "user:", self.username)

    def connect(self, client_id, keepalive=60):
        """
        Create MQTTClient, connect, and return the client object.
        keepalive=60s ensures the broker sends PINGREQ if no traffic.
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
        """
        Publish value to topic. Returns True on success.
        FIX: errorcount was an unbound local variable — removed the counter,
             let the caller handle reconnect logic.
        """
        if self.client is None:
            return False
        try:
            self.client.publish(topic, str(value), retain=retain)
            return True
        except Exception as e:
            print("MQTT publish failed:", e)
            return False
