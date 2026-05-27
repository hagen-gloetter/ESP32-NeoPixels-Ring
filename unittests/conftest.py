import importlib.util
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RINGS_DIR = ROOT / "3-Rings"


class FakeNeoPixel:
    def __init__(self, pin, pixel_count, bpp=3, timing=1):
        self.pin = pin
        self.pixel_count = pixel_count
        self.bpp = bpp
        self.timing = timing
        self.values = [(0, 0, 0)] * pixel_count
        self.write_calls = 0

    def __setitem__(self, index, value):
        self.values[index] = value

    def __getitem__(self, index):
        return self.values[index]

    def write(self):
        self.write_calls += 1


class FakePin:
    def __init__(self, pin):
        self.pin = pin


class FakeRTC:
    def __init__(self):
        self._datetime = (2026, 1, 1, 3, 0, 0, 0, 0)

    def datetime(self, value=None):
        if value is not None:
            self._datetime = value
        return self._datetime


class FakeMachineModule:
    def __init__(self):
        self.idle_calls = 0
        self._rtc = FakeRTC()

    Pin = FakePin

    def RTC(self):
        return self._rtc

    def idle(self):
        self.idle_calls += 1


class FakeTimeModule:
    def __init__(self):
        self.sleep_ms_calls = []

    def sleep_ms(self, value):
        self.sleep_ms_calls.append(value)


class FakeUTimeModule:
    def __init__(self):
        self.now = 0
        self.sleep_ms_calls = []
        self.localtime_value = (2026, 1, 15, 12, 34, 56, 3, 15)

    def time(self):
        return self.now

    def sleep_ms(self, value):
        self.sleep_ms_calls.append(value)
        self.now += value // 1000

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, current, start):
        return current - start

    def localtime(self):
        return self.localtime_value


class FakeMQTTClient:
    def __init__(self, client_id, broker, port, username, password, keepalive=60):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self.connect_calls = 0
        self.publish_calls = []
        self.raise_on_publish = None

    def connect(self):
        self.connect_calls += 1

    def publish(self, topic, value, retain=False):
        if self.raise_on_publish is not None:
            raise self.raise_on_publish
        self.publish_calls.append((topic, value, retain))


class FakeSocketInstance:
    def __init__(self):
        self.sockopts = []
        self.bound = None
        self.listen_backlog = None
        self.closed = False

    def setsockopt(self, level, option, value):
        self.sockopts.append((level, option, value))

    def bind(self, address):
        self.bound = address

    def listen(self, backlog):
        self.listen_backlog = backlog

    def accept(self):
        raise RuntimeError("no client")

    def close(self):
        self.closed = True


class FakeSocketModule:
    AF_INET = 1
    SOCK_STREAM = 2
    SOL_SOCKET = 3
    SO_REUSEADDR = 4

    def __init__(self):
        self.instances = []

    def socket(self, family, sock_type):
        instance = FakeSocketInstance()
        self.instances.append(instance)
        return instance


class FakeThreadModule:
    def __init__(self):
        self.calls = []

    def start_new_thread(self, target, args):
        self.calls.append((target, args))
        return len(self.calls)


@pytest.fixture
def module_loader(monkeypatch):
    loaded = []

    def load(module_name, extra_modules=None):
        fake_machine = FakeMachineModule()
        fake_time = FakeTimeModule()
        fake_utime = FakeUTimeModule()
        fake_neopixel = types.SimpleNamespace(NeoPixel=FakeNeoPixel)
        fake_ntptime = types.SimpleNamespace(settime=lambda: None)
        fake_ujson = types.SimpleNamespace(load=lambda handle: {})
        fake_socket = FakeSocketModule()
        fake_thread = FakeThreadModule()
        fake_network = types.SimpleNamespace(STA_IF=0, WLAN=lambda *_args, **_kwargs: None)
        fake_umqtt_pkg = types.ModuleType("umqtt")
        fake_umqtt_robust = types.ModuleType("umqtt.robust")
        fake_umqtt_robust.MQTTClient = FakeMQTTClient
        fake_umqtt_pkg.robust = fake_umqtt_robust

        modules = {
            "machine": fake_machine,
            "time": fake_time,
            "utime": fake_utime,
            "neopixel": fake_neopixel,
            "ntptime": fake_ntptime,
            "ujson": fake_ujson,
            "socket": fake_socket,
            "_thread": fake_thread,
            "network": fake_network,
            "umqtt": fake_umqtt_pkg,
            "umqtt.robust": fake_umqtt_robust,
        }
        if extra_modules:
            modules.update(extra_modules)

        for key, value in modules.items():
            monkeypatch.setitem(sys.modules, key, value)

        module_path = RINGS_DIR / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"test_{module_name}", module_path)
        module = importlib.util.module_from_spec(spec)
        loaded.append(module)
        spec.loader.exec_module(module)
        module._test_doubles = {
            "machine": fake_machine,
            "time": fake_time,
            "utime": fake_utime,
            "socket": fake_socket,
            "thread": fake_thread,
            "mqtt_client": FakeMQTTClient,
        }
        return module

    yield load

    for module in loaded:
        sys.modules.pop(module.__name__, None)