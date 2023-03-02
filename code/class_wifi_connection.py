import ujson
import network
from network import WLAN
import machine
import sys
import time


class WifiConnect:
    """Class to connect your ESP32 to local Wifi
    SSID and WiFi PW are read from file: secrets_wifi.json
    Usage:
    # Setup Wifi
    import class_wifi_connection
    global wifi
    wifi = class_wifi_connection.WifiConnect()
    (wifi_status, wifi_ssid, wifi_ip) = wifi.connect()
    # in a loop or timer
    list = wifi.check_connection()
    for item in list:
        print(item)
    # stop
        wifi.disconnect()
    """

    def __init__(self):
        self.wifi_ssid = "offline"
        self.wifi_pw = "hidden"
        self.wifi_ip = "offline"
        self.wifi_status = "offline"
        self.wifi = None

    def connect(self):
        print("connect wifi called")
        wlan_json = ujson.load(open("secrets_wifi.json"))
        # print (wlan_json)
        # print (type (wlan_json))
        # for key in wlan_json.keys():
        #    print (key)
        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)
        self.wifi.disconnect()  # be sure to be disconnected
        nets = self.wifi.scan()
        # print ("NETS: ",nets)
        # print (type (nets))
        for ssid in wlan_json.keys():
            if ssid in str(nets):
                print(f"++++++++ Network {ssid} found!")
                pwd = wlan_json[ssid]
                print("tying to connect ssid:", ssid)
                (
                    self.wifi_status,
                    self.wifi_ssid,
                    self.wifi_ip,
                ) = self.try_wifi_connect(ssid, pwd)
                if self.wifi_status == "online":
                    break
        list = [self.wifi_status, self.wifi_ssid, self.wifi_ip]
        return list

    def get_wifi_status():
        list = [self.wifi_status, self.wifi_ssid, self.wifi_ip]
        return list

    def try_wifi_connect(self, ssid, pwd):
        try:
            self.wifi.connect(ssid, pwd)
            while not self.wifi.isconnected():
                machine.idle()  # save power while waiting
            self.wifi_status = "online"
            self.wifi_ssid = ssid
            self.wifi_pw = pwd
            self.wifi_ip = self.wifi.ifconfig()[0]
            print("Connected to " + self.wifi_ssid)
            print(" with IP address:" + self.wifi_ip)
        except Exception as e:
            print("Failed to connect to any known network")
            self.wifi_status = "offline"
            self.wifi_ssid = "offline"
            self.wifi_ip = "offline"
            self.wifi.disconnect()  # do a clean disconnected
        list = [self.wifi_status, self.wifi_ssid, self.wifi_ip]
        return list

    def check_connection(self):
        print("check_connection called")
        if self.wifi_ssid == "offline":
            print("tying to connect ssid:", self.wifi_ssid)
            self.connect()  # we are not connected at all
        elif not self.wifi.isconnected() or self.wifi_status == "offline":
            # no more  more connected
            self.wifi_status = "offline"
            print("tying to connect ssid:", self.wifi_ssid)
            (self.wifi_status, self.wifi_ssid, self.wifi_ip) = self.try_wifi_connect(
                self.wifi_ssid, self.wifi_pw
            )
        list = [self.wifi_status, self.wifi_ssid, self.wifi_ip]
        return list

    def disconnect(self):
        print("disconnect called")
        self.wifi.disconnect()


def main():
    wifi = WifiConnect()
    (wifi_status, wifi_ssid, wifi_ip) = wifi.connect()
    (wifi_status, wifi_ssid, wifi_ip) = wifi.check_connection()
    wifi.disconnect()


if __name__ == "__main__":
    sys.exit(main())

