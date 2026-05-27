import io


class FakeWLAN:
    def __init__(self, scan_results=None, connected=False, ip="192.168.1.22"):
        self.scan_results = scan_results or []
        self.connected = connected
        self.ip = ip
        self.active_calls = []
        self.disconnect_calls = 0
        self.connect_calls = []

    def active(self, value):
        self.active_calls.append(value)

    def disconnect(self):
        self.disconnect_calls += 1
        self.connected = False

    def scan(self):
        return self.scan_results

    def connect(self, ssid, pwd):
        self.connect_calls.append((ssid, pwd))

    def isconnected(self):
        return self.connected

    def ifconfig(self):
        return (self.ip, "255.255.255.0", "192.168.1.1", "8.8.8.8")


def load_wifi_module(module_loader, monkeypatch, wlan, secrets=None):
    module = module_loader(
        "class_wifi_connection",
        extra_modules={
            "network": type("FakeNetwork", (), {"STA_IF": 0, "WLAN": lambda *_args, **_kwargs: wlan})(),
        },
    )
    if secrets is not None:
        monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: io.StringIO("{}"), raising=False)
        monkeypatch.setattr(module.ujson, "load", lambda _handle: secrets)
    return module


def test_connect_returns_offline_when_secrets_missing(module_loader, monkeypatch):
    wlan = FakeWLAN()
    module = module_loader(
        "class_wifi_connection",
        extra_modules={
            "network": type("FakeNetwork", (), {"STA_IF": 0, "WLAN": lambda *_args, **_kwargs: wlan})(),
        },
    )
    monkeypatch.setattr(module, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("missing")), raising=False)

    wifi = module.WifiConnect()

    assert wifi.connect() == ("offline", "offline", "offline")


def test_connect_ignores_undecodable_scan_entries_and_uses_matching_ssid(module_loader, monkeypatch):
    wlan = FakeWLAN(scan_results=[(b"\xff\xfe",), (b"HomeWiFi",)])
    module = load_wifi_module(module_loader, monkeypatch, wlan, {"HomeWiFi": "secret", "Nope": "other"})
    wifi = module.WifiConnect()
    monkeypatch.setattr(wifi, "try_wifi_connect", lambda ssid, pwd: ["online", ssid, "192.168.1.20"])

    result = wifi.connect()

    assert result == ["online", "HomeWiFi", "192.168.1.20"]


def test_try_wifi_connect_times_out_and_cleans_up(module_loader, monkeypatch):
    wlan = FakeWLAN(connected=False)
    module = load_wifi_module(module_loader, monkeypatch, wlan)
    wifi = module.WifiConnect()
    wifi.wifi = wlan

    ticks = iter([0, 3000, 8001])
    monkeypatch.setattr(module.utime, "ticks_ms", lambda: next(ticks))

    result = wifi.try_wifi_connect("HomeWiFi", "secret")

    assert result == ["offline", "offline", "offline"]
    assert wlan.connect_calls == [("HomeWiFi", "secret")]
    assert wlan.disconnect_calls == 1
    assert module._test_doubles["machine"].idle_calls == 2


def test_check_connection_retries_known_network(module_loader, monkeypatch):
    wlan = FakeWLAN(connected=False)
    module = load_wifi_module(module_loader, monkeypatch, wlan)
    wifi = module.WifiConnect()
    wifi.wifi = wlan
    wifi.wifi_status = "offline"
    wifi.wifi_ssid = "HomeWiFi"
    wifi.wifi_pw = "secret"
    monkeypatch.setattr(wifi, "try_wifi_connect", lambda ssid, pwd: ["online", ssid, "192.168.1.44"])

    result = wifi.check_connection()

    assert result == ["online", "HomeWiFi", "192.168.1.44"]


def test_disconnect_resets_state(module_loader, monkeypatch):
    wlan = FakeWLAN(connected=True)
    module = load_wifi_module(module_loader, monkeypatch, wlan)
    wifi = module.WifiConnect()
    wifi.wifi = wlan
    wifi.wifi_status = "online"
    wifi.wifi_ssid = "HomeWiFi"
    wifi.wifi_ip = "192.168.1.44"

    wifi.disconnect()

    assert wlan.disconnect_calls == 1
    assert wifi.get_wifi_status() == ["offline", "offline", "offline"]