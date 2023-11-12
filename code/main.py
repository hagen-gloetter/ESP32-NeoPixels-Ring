# Written by ramona@gloetter.de & hagen@gloetter.de 2023-03-01

import time
import machine
import class_wifi_connection
from class_mqtt import MQTT
from class_color_wheel import color_wheel
import class_webserver
from time import localtime
import class_ntp


led_ring1 = color_wheel(12, 25)
led_ring2 = color_wheel(12, 27)
led_ring1.show_wifi()
led_ring2.display_percentage2(100)

print("Setup Wifi")
global wifi
wifi = class_wifi_connection.WifiConnect()
(wifi_status, wifi_ssid, wifi_ip) = wifi.connect()

print("Get Time")
ntp = class_ntp.NTPClock()
ntp.sync_time(wifi)

client_id = "led-ring01"
mqttclient = None

SOC1 = 0
SOC2 = 0
acoutw = 0
totalsolarw = 0


def connect_mqtt():
    global mqttclient
    mqtt = MQTT()
    mqttclient = mqtt.connect(client_id)
    mqttclient.set_callback(on_message)
    mqttclient.subscribe(b"mqtt.0.Seplos.BatteryPack1.soc")
    mqttclient.subscribe(b"mqtt.0.Seplos.BatteryPack2.soc")
    mqttclient.subscribe(b"mqtt.0.solaranlage.pip.acoutw")
    mqttclient.subscribe(b"mqtt.0.solaranlage.pip.totalsolarw")


def on_message(topic, msg):
    global led_ring1
    global SOC1
    global SOC2
    global acoutw
    global totalsolarw
    print("Received message `{0}` under topic {1}".format(msg, topic))
    if "totalsolarw" in topic:
        p = (int(msg)+1) * 100 / 2500
        if p < 0:
            p = 0
        if p > 100:
            p = 100

        # 12 leds = 100% -> 1 led = 8.3%
        num_leds = round(p/8.3)
        led_ring2.set_single_color(num_leds, "g")

    elif "acoutw" in topic:
        # gives values from 0 (not poosible) to 4200w (2500w) is normal max therefore 100%
        p = (int(msg)+1) * 100 / 2500
        if p < 0:
            p = 0
        if p > 100:
            p = 100

        # 12 leds = 100% -> 1 led = 8.3%
        num_leds = round(p/8.3)
        led_ring2.set_single_color(num_leds, "r")

    else:
        SOC2 = SOC1
        SOC1 = float(msg)
        if SOC2 == 0:
            SOC2 = SOC1  # fix 1st run
        #    if topic in topicSoC1:
        #        SOC1=int(msg)
        #    if topic in topicSoC2:
        #        SOC2=int(msg)
        p = (SOC1+SOC2+0.01)/2  # no div/0
        print(f"SOC1 {SOC1} SOC2 {SOC2} p={p}%")
        led_ring1.display_percentage1(p)


connect_mqtt()
led_ring1.display_percentage1(0)

# Webserver
apache = class_webserver.Webserver()


def stop_all():
    global apache
    global mqttclient
    apache.stop_webserver()
    mqttclient.disconnect()
    wifi.disconnect()


def kill():
    stop_all()


test = 0
timesync = 0
reconnect_needed = "no"

if __name__ == "__main__":
    try:
        while True:
            time.sleep(10)
            (wifi_status, wifi_ssid, wifi_ip) = wifi.check_connection()
            if wifi_status == "offline":
                reconnect_needed = "yes"
            if wifi_status == "online" and reconnect_needed == "yes":
                reconnect_needed = "no"
                connect_mqtt()
            if timesync < 6:
                timesync += 1
            elif timesync >= 6:
                timesync = 0
                ntp.sync_time(wifi)
                t = ntp.get_time()
                print(f"time: {str(t)}")

            mqttclient.check_msg()

            # TODO Restore MQTT after WLAN Reconnect

    except KeyboardInterrupt:
        print("exiting")

    if test == 1:
        led_ring1 = color_wheel(12, 10)
        led_ring1.display_percentage1(30)
        time.sleep(2)
        led_ring1.display_percentage1(-10)
        time.sleep(2)
        led_ring1.display_percentage1(100)
        time.sleep(2)
        led_ring1.display_percentage1(50)
        time.sleep(2)
        led_ring1.display_percentage1(120)

