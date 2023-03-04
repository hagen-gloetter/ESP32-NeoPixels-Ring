# Written by ramona@gloetter.de & hagen@gloetter.de 2023-03-01

import time
import machine
import class_wifi_connection
from class_mqtt import MQTT
from class_color_wheel import color_wheel

led_ring1 = color_wheel(12, 25)
led_ring2 = color_wheel(12, 27)
led_ring1.display_percentage(100)
led_ring2.display_percentage(100)

print ("Setup Wifi")
global wifi
wifi = class_wifi_connection.WifiConnect()
(wifi_status, wifi_ssid, wifi_ip) = wifi.connect()

client_id = "led-ring01"
mqtt = MQTT()
mqttclient = mqtt.connect(client_id)
topicSoC1 = b"mqtt.0.Seplos.BatteryPack1.soc"
topicSoC2 = b"mqtt.0.Seplos.BatteryPack2.soc"
SOC1=0
SOC2=0

def on_message(topic, msg):
    global led_ring1
    global SOC1
    global SOC2
    print("Received message `{0}` under topic {1}".format(msg, topic))
    SOC2 = SOC1
    SOC1 = float(msg)
    if SOC2 == 0:
        SOC2 = SOC1 # fix 1st run
#    if topic in topicSoC1:
#        SOC1=int(msg)
#    if topic in topicSoC2:
#        SOC2=int(msg)
    p=(SOC1+SOC2+0.01)/2 # no div/0
    print (f"SOC1 {SOC1} SOC2 {SOC2} p={p}%")
    led_ring1.display_percentage(p)
    led_ring2.display_percentage(p)

led_ring1.display_percentage(0)
mqttclient.set_callback(on_message)
mqttclient.subscribe(topicSoC1)
mqttclient.subscribe(topicSoC2)

test=0

if __name__ == "__main__":
    try:
        while True:
            time.sleep(5)
            mqttclient.check_msg()
            (wifi_status, wifi_ssid, wifi_ip) = wifi.check_connection()
            # TODO Restore MQTT after WLAN Reconnect
    except KeyboardInterrupt:
        print("exiting")
        
    if test==1:
        led_ring1 = color_wheel(12, 10)
        led_ring1.display_percentage(30)
        time.sleep(2)
        led_ring1.display_percentage(-10)
        time.sleep(2)
        led_ring1.display_percentage(100)
        time.sleep(2)
        led_ring1.display_percentage(50)
        time.sleep(2)
        led_ring1.display_percentage(120)

