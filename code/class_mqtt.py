import time
import sys
import random
import os
import ujson
from umqtt.robust import MQTTClient
from machine import Pin
from machine import Timer


class MQTT():
    """Class to connect your ESP32 to a MQTT Server"""

    def __init__(self, mqtt_json_file="secrets_mqtt.json"):
        # Setup MQTT
        #        load_settings(self)
        #    def load_settings(self):
        self.mqtt_json = ujson.load(open(mqtt_json_file))
        self.broker = self.mqtt_json["secretHost"]
        self.port = self.mqtt_json["secretPort"]
        self.username = self.mqtt_json["secretUser"]
        self.password = self.mqtt_json["secretPass"]
        self.client = None
        self.errorcount = 0
        self.connection_running = True
        print("brokerHost:Port = " + self.broker + " " + str(self.port))
        print("user = " + self.username)

    def connect(self, client_id):
        print("start connect_mqtt", 1)
        self.client = MQTTClient(
            client_id, self.broker, self.port, self.username, self.password
        )
        self.client.connect()
        return self.client

    def publish(self, client, topic, value):
        print("start publishMqtt", 1)
        print(f"start publishMqtt topic={topic} value={value}", 1)

        try:
            result = client.publish(topic, str(value))
        except:
            print(f"Failed to send message {value} to topic {topic}")
            errorcount += 1
            if errorcount > 1500:  # 0,2s*5 * 5*60s
                # break the loop and reconnect
                self.connection_running = False
                return False
        else:
            print(f"Send `{value}` to topic `{topic}`")
            errorcount = 0
            return True

    def reconnect_on_error(self):
        pass
        # TODO: reuse init to get a new connection
        # __init__()

def main():
    mqtt = MQTT()
    mqttclient = mqtt.connect()
    topicHumidity = b"debugroom/humidity"
#    mqtt.publish(mqttclient, topicHumidity, 50)
    topicTemperature = b"debugroom/temperature"
#    mqtt.publish(mqttclient, topicTemperature, 20)
    topicWater = b"water"
#    mqtt.publish(mqttclient, topicWater, 100)


if __name__ == "__main__":
    sys.exit(main())
