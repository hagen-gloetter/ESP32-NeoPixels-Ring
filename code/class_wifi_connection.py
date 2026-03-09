"""
class_wifi_connection.py — WiFi connection manager for ESP32 (MicroPython).

Reads a dict of known SSIDs and passwords from a JSON credentials file,
scans for available networks, and connects to the first match.
Provides reconnection logic suitable for a watchdog-style main loop.

Credentials file format (``secrets_wifi.json``)::

    {
        "MyHomeSSID":   "wifipassword1",
        "BackupSSID":   "wifipassword2"
    }

Multiple networks are supported; the first one found during a scan is used.

Typical usage::

    import class_wifi_connection

    wifi = class_wifi_connection.WifiConnect()
    status, ssid, ip = wifi.connect()

    # In the main loop watchdog:
    if not wifi.isconnected():
        wifi.check_connection()
"""

import ujson
import network
import machine
import utime


class WifiConnect:
    """WiFi connection manager for ESP32.

    Loads credentials from ``secrets_wifi.json`` and attempts to connect
    to the strongest known network found during a scan.  Provides
    ``check_connection()`` for use as a periodic watchdog in the main loop.

    Typical flow::

        wifi = WifiConnect()
        status, ssid, ip = wifi.connect()      # initial connect at boot

        while True:
            if not wifi.isconnected():         # watchdog check
                wifi.check_connection()        # reconnect if needed
    """

    def __init__(self):
        self.wifi_ssid = "offline"
        self.wifi_pw = "hidden"
        self.wifi_ip = "offline"
        self.wifi_status = "offline"
        self.wifi = None

    def connect(self):
        """Read credentials, scan for known networks, and connect to the first match.

        Returns:
            list: ``[status, ssid, ip]`` where *status* is ``"online"`` or
                  ``"offline"``.
        """
        fn_secrets = "secrets_wifi.json"
        try:
            wlan_json = ujson.load(open(fn_secrets))
        except:
            print(f"!!!!!!!!!!!!!!!! ERROR !!!!!!!!!!!!!!!! File not found {fn_secrets}")
            return ("offline", "offline", "offline")
        else:
            print(f"connect wifi called with {fn_secrets}")
            self.wifi = network.WLAN(network.STA_IF)
            self.wifi.active(True)
            self.wifi.disconnect()  # ensure clean state before scanning
            nets = self.wifi.scan()
            for ssid in wlan_json.keys():
                if ssid in str(nets):
                    print("Network found:", ssid)
                    pwd = wlan_json[ssid]
                    print("Connecting to SSID:", ssid)
                    (
                        self.wifi_status,
                        self.wifi_ssid,
                        self.wifi_ip,
                    ) = self.try_wifi_connect(ssid, pwd)
                    if self.wifi_status == "online":
                        break
            list = [self.wifi_status, self.wifi_ssid, self.wifi_ip]
            return list
            
            

    def try_wifi_connect(self, ssid=None, pwd=None):
        """Attempt to associate with *ssid* using *pwd*.

        Blocks for up to 7 seconds (below the 8 s WDT window) while waiting
        for the association handshake.  Updates ``self.wifi_status``,
        ``self.wifi_ssid``, and ``self.wifi_ip`` on success.

        Args:
            ssid (str): Network name.  Defaults to the last known SSID.
            pwd (str):  Password.  Defaults to the last known password.

        Returns:
            list: ``[status, ssid, ip]``.
        """
        if ssid is None:
            ssid = self.wifi_ssid
            pwd = self.wifi_pw
        try:
            self.wifi.connect(ssid, pwd)
            timeout = 7000  # 7 seconds timeout (must stay below 8 s WDT window)
            start_time = utime.ticks_ms()
            while not self.wifi.isconnected():
                if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout:
                    print("Connection timeout reached")
                    break
                machine.idle()  # save power while waiting

            if self.wifi.isconnected():
                self.wifi_status = "online"
                self.wifi_ssid = ssid
                self.wifi_pw = pwd
                self.wifi_ip = self.wifi.ifconfig()[0]
                print("Connected to " + self.wifi_ssid)
                print(" with IP address: " + self.wifi_ip)
            else:
                raise Exception("Connection failed")

        except Exception as e:
            print(f"Failed to connect to any known network: {e}")
            self.wifi_status = "offline"
            self.wifi_ssid = "offline"
            self.wifi_ip = "offline"
            self.wifi.disconnect()  # ensure clean disconnect
        return [self.wifi_status, self.wifi_ssid, self.wifi_ip]

    def get_wifi_status(self):
        """Return ``[status, ssid, ip]`` reflecting the last known connection state."""
        return [self.wifi_status, self.wifi_ssid, self.wifi_ip]

    def isconnected(self):
        """Return True if the WLAN interface reports an active association."""
        return self.wifi.isconnected()

    def check_connection(self):
        """Watchdog helper: reconnect if the connection has been lost.

        Call this periodically from the main loop.  If the WLAN interface
        reports disconnected, ``try_wifi_connect()`` is called with the last
        known credentials.  If no credentials are known, a full ``connect()``
        scan is triggered.

        Returns:
            list: ``[status, ssid, ip]``.
        """
        print("check_connection called")
        if self.wifi_ssid == "offline":
            print("Attempting to connect to SSID:", self.wifi_ssid)
            self.connect()  # not connected at all
        elif not self.wifi.isconnected() or self.wifi_status == "offline":
            self.wifi_status = "offline"
            print("Connection lost, trying to reconnect to SSID: ", self.wifi_ssid)
            (self.wifi_status, self.wifi_ssid, self.wifi_ip) = self.try_wifi_connect(
                self.wifi_ssid, self.wifi_pw
            )
        return [self.wifi_status, self.wifi_ssid, self.wifi_ip]

    def disconnect(self):
        """Disconnect from WiFi and reset the connection state to offline."""
        print("disconnect called")
        self.wifi.disconnect()
        self.wifi_status = "offline"
        self.wifi_ssid = "offline"
        self.wifi_ip = "offline"

    def stop_all(self):
        """Alias for disconnect(). Kept for backward compatibility."""
        self.disconnect()


