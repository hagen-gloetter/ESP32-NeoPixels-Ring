# class_wifi_connection.py
# WiFi connection manager for ESP32 (MicroPython)
# FIX: is_connected() called check_connection() on WLAN object (AttributeError),
#      SSID scan used fragile str(nets) substring match (now: bytes equality),
#      removed broken is_connected() method.

import ujson
import network
import machine
import utime


class WifiConnect:
    """
    Manages WiFi connection. SSID/password loaded from secrets_wifi.json.

    Usage:
        wifi = WifiConnect()
        status, ssid, ip = wifi.connect()
        # in loop:
        status, ssid, ip = wifi.check_connection()
        wifi.disconnect()
    """

    def __init__(self):
        self.wifi_ssid   = "offline"
        self.wifi_pw     = "hidden"
        self.wifi_ip     = "offline"
        self.wifi_status = "offline"
        self.wifi        = None

    def connect(self):
        """Scan for known networks and connect to the first one found."""
        fn = "secrets_wifi.json"
        try:
            wlan_json = ujson.load(open(fn))
        except Exception as e:
            print("ERROR: cannot open", fn, e)
            return ("offline", "offline", "offline")

        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)
        self.wifi.disconnect()
        nets = self.wifi.scan()   # list of (ssid_bytes, bssid, ch, rssi, sec, hidden)

        # FIX: compare SSID as bytes, not via str(nets) substring search
        scanned_ssids = set(net[0] for net in nets)
        for ssid_str, pwd in wlan_json.items():
            if ssid_str.encode() in scanned_ssids:
                print("Network found:", ssid_str)
                status, ssid, ip = self.try_wifi_connect(ssid_str, pwd)
                if status == "online":
                    break

        return (self.wifi_status, self.wifi_ssid, self.wifi_ip)

    def try_wifi_connect(self, ssid=None, pwd=None):
        if ssid is None:
            ssid = self.wifi_ssid
            pwd  = self.wifi_pw
        try:
            self.wifi.connect(ssid, pwd)
            timeout_ms = 10000
            t0 = utime.ticks_ms()
            while not self.wifi.isconnected():
                if utime.ticks_diff(utime.ticks_ms(), t0) > timeout_ms:
                    raise OSError("Connection timeout")
                machine.idle()
            self.wifi_status = "online"
            self.wifi_ssid   = ssid
            self.wifi_pw     = pwd
            self.wifi_ip     = self.wifi.ifconfig()[0]
            print("WiFi connected to", ssid, "IP:", self.wifi_ip)
        except Exception as e:
            print("WiFi connect failed:", e)
            self.wifi_status = "offline"
            self.wifi_ssid   = "offline"
            self.wifi_ip     = "offline"
            try:
                self.wifi.disconnect()
            except Exception:
                pass
        return (self.wifi_status, self.wifi_ssid, self.wifi_ip)

    def isconnected(self):
        """Return True if the underlying WLAN object is connected."""
        if self.wifi is None:
            return False
        return self.wifi.isconnected()

    def check_connection(self):
        """If connection is lost, attempt reconnect. Returns (status, ssid, ip)."""
        if self.wifi is None or not self.wifi.isconnected():
            self.wifi_status = "offline"
            print("WiFi offline, reconnecting to:", self.wifi_ssid)
            if self.wifi_ssid == "offline":
                # Never connected: do a full scan
                return self.connect()
            return self.try_wifi_connect(self.wifi_ssid, self.wifi_pw)
        return (self.wifi_status, self.wifi_ssid, self.wifi_ip)

    def disconnect(self):
        if self.wifi is not None:
            self.wifi.disconnect()
        self.wifi_status = "offline"
        self.wifi_ssid   = "offline"
        self.wifi_ip     = "offline"

