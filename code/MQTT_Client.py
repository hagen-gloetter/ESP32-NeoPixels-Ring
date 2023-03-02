import paho.mqtt.client as mqttClient
import time

import ujson
mqtt_json_file="code/secrets_mqtt.json"
mqtt_json = ujson.load(open(mqtt_json_file))
broker = mqtt_json["secretHost"]
mport = mqtt_json["secretPort"]
username = mqtt_json["secretUser"]
mpassword = mqtt_json["secretPass"]

def on_connect(client, userdata, flags, rc):

    if rc == 0:
        print("Connected to broker")
        global Connected  # Use global variable
        Connected = True  # Signal connection
    else:
        print("Connection failed")


def on_message(client, userdata, message):
    print("Message received: " + str(message.payload))


Connected = False  # global variable for the state of the connection

broker_address = broker  # Broker address
port = int(mport)  # Broker port
user = username  # Connection username
password = mpassword  # Connection password

client = mqttClient.Client("Python")  # create new instance
client.username_pw_set(user, password=password)  # set username and password
client.on_connect = on_connect  # attach function to callback
client.on_message = on_message  # attach function to callback

client.connect(broker_address, port=port)  # connect to broker

client.loop_start()  # start the loop

while Connected != True:  # Wait for connection
    time.sleep(0.1)

client.subscribe("mqtt.0.Seplos.BatteryPack1.soc")
client.subscribe("mqtt.0.Seplos.BatteryPack2.soc")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("exiting")
    client.disconnect()
    client.loop_stop()
