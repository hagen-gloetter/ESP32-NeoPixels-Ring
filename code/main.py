# main.py  —  Solar/Battery NeoPixel Monitor
# Board  : ESP32 (MicroPython)
# LEDs   : 2× WS2812B NeoPixel ring, 12 LEDs each, bpp=3 (RGB)
# Ring 1 (GPIO 25): SoC average of both battery packs, red→green gradient
# Ring 2 (GPIO 27): Solar watts (green) + AC-load watts (red), overlaid
# Written by ramona@gloetter.de & hagen@gloetter.de 2023-03-01
# Refactored 2026: bug fixes, non-blocking renderer, MQTT error handling

import utime
import class_wifi_connection
from class_mqtt import MQTT
from class_color_wheel import color_wheel
import class_webserver
import class_ntp

# ── Configuration ──────────────────────────────────────────────────────────────
RING1_PIN       = 25           # GPIO for Ring 1 (SoC)
RING2_PIN       = 27           # GPIO for Ring 2 (solar/load)
LED_COUNT       = 12           # LEDs per ring
BRIGHTNESS      = 16           # Max PWM brightness (0–255; keep low for 5 V USB)

CLIENT_ID       = b"led-ring01"
MQTT_JSON       = "secrets_mqtt.json"

# MQTT topics as bytes (FIX: was str — caused TypeError with umqtt bytes topic)
TOPIC_SOC1      = b"mqtt.0.Seplos.BatteryPack1.soc"
TOPIC_SOC2      = b"mqtt.0.Seplos.BatteryPack2.soc"
TOPIC_ACOUTW    = b"mqtt.0.solaranlage.pip.acoutw"
TOPIC_SOLARW    = b"mqtt.0.solaranlage.pip.totalsolarw"
_TOPICS         = (TOPIC_SOC1, TOPIC_SOC2, TOPIC_ACOUTW, TOPIC_SOLARW)

# TODO: adjust SOLAR_MAX_W to match your inverter's rated output capacity
SOLAR_MAX_W     = 2500         # watts = 100 % = all 12 LEDs lit

LOOP_MS         = 100          # main-loop tick in ms (10 Hz)
NTP_INTERVAL_S  = 600          # NTP re-sync every 10 minutes
MQTT_BACKOFF_MAX = 60          # max reconnect delay in seconds

# ── Shared state ───────────────────────────────────────────────────────────────
# Single source of truth; MQTT callback only writes here.
# Webserver thread reads this dict (MicroPython GIL protects individual ops).
state = {
    "SOC1":        0.0,
    "SOC2":        0.0,
    "acoutw":      0,
    "totalsolarw": 0,
    "dirty":       True,   # True → LEDs need a redraw
}

# ── Hardware init ──────────────────────────────────────────────────────────────
led_ring1 = color_wheel(LED_COUNT, RING1_PIN, BRIGHTNESS)
led_ring2 = color_wheel(LED_COUNT, RING2_PIN, BRIGHTNESS)
led_ring1.show_wifi()           # blue flash: "setup in progress"

# ── WiFi ───────────────────────────────────────────────────────────────────────
print("Setup WiFi")
wifi = class_wifi_connection.WifiConnect()
wifi_status, _, _ = wifi.connect()

if wifi_status == "online":
    # Success: right ring (Ring 2) blinks blue 3×
    led_ring2.blink_blue(3)
    # Start WebREPL now that WiFi is up (password set via webrepl_cfg.py or
    # first-time setup via REPL: import webrepl; webrepl.start(password="xxx"))
    try:
        import webrepl
        webrepl.start()
        print("WebREPL started")
    except Exception as e:
        print("WebREPL start failed:", e)
else:
    # Failure: left ring (Ring 1) blinks blue 3×
    led_ring1.blink_blue(3)

# ── NTP ────────────────────────────────────────────────────────────────────────
print("NTP sync")
ntp = class_ntp.NTPClock()
try:
    ntp.sync_time(wifi)
except OSError as e:
    print("NTP initial sync failed (will retry):", e)
_last_ntp_s = utime.time()

# ── MQTT ───────────────────────────────────────────────────────────────────────
_mqtt_obj    = MQTT(MQTT_JSON)
_mqttclient  = None
_mqtt_backoff = 1              # current backoff delay in seconds


def _watts_to_leds(watts):
    """Convert watt value to LED count (0..LED_COUNT), clamped."""
    p = (int(watts) + 1) * 100 // SOLAR_MAX_W
    return max(0, min(LED_COUNT, round(p * LED_COUNT / 100)))


def on_message(topic, msg):
    """
    MQTT callback — runs in the main loop context.
    FAST: only updates state dict, zero LED writes, zero sleeps.
    FIX: topic comparison as bytes (was str → TypeError).
    FIX: SOC1/SOC2 now differentiated by topic (was both in same else-branch).
    """
    try:
        if topic == TOPIC_SOC1:
            state["SOC1"] = float(msg)
        elif topic == TOPIC_SOC2:
            state["SOC2"] = float(msg)
        elif topic == TOPIC_SOLARW:
            state["totalsolarw"] = int(msg)
        elif topic == TOPIC_ACOUTW:
            state["acoutw"] = int(msg)
        else:
            print("MQTT rx (unmatched topic):", topic, "=", msg)
            return
        state["dirty"] = True
        print("MQTT rx:", topic, "=", msg)
    except (ValueError, UnicodeError) as e:
        print("MQTT parse error:", e, "| topic:", topic, "| msg:", msg)


def _mqtt_connect():
    """Connect to broker and re-subscribe. Returns True on success."""
    global _mqttclient
    try:
        _mqttclient = _mqtt_obj.connect(CLIENT_ID, keepalive=60)
        _mqttclient.set_callback(on_message)
        for t in _TOPICS:
            _mqttclient.subscribe(t)
        print("MQTT connected, subscribed to", len(_TOPICS), "topics")
        return True
    except OSError as e:
        print("MQTT connect failed:", e)
        _mqttclient = None
        return False


def _update_leds():
    """
    Render current state to both rings.
    Called only when state["dirty"] is True — never inside on_message().
    Two np.write() calls total (one per ring).
    """
    # Ring 1: average SoC, red→green gradient
    avg_soc = (state["SOC1"] + state["SOC2"]) / 2.0
    led_ring1.set_ring1_percent(avg_soc)

    # Ring 2: solar power (green) and AC load (red) overlaid
    led_ring2.set_ring2_channels(
        num_r=_watts_to_leds(state["acoutw"]),
        num_g=_watts_to_leds(state["totalsolarw"]),
    )


# ── Webserver (background thread) ─────────────────────────────────────────────
# FIX: Webserver now receives state dict reference instead of reading stale
#      module-level globals that were never updated from main.py.
apache = class_webserver.Webserver(state)

# ── Initial MQTT connect + LED state ──────────────────────────────────────────
_mqtt_connect()
_update_leds()   # show "all off / 0 %" until first MQTT message arrives

# ── Main loop ─────────────────────────────────────────────────────────────────
print("Entering main loop (tick:", LOOP_MS, "ms)")
try:
    while True:
        # 1) WiFi watchdog ─────────────────────────────────────────────────────
        if not wifi.isconnected():
            print("WiFi offline, reconnecting…")
            wifi.check_connection()
            if wifi.isconnected():
                print("WiFi restored, reconnecting MQTT…")
                _mqtt_connect()
                _mqtt_backoff = 1

        # 2) MQTT message pump with per-iteration error handling ───────────────
        # FIX: check_msg() is now inside try/except — an OSError no longer
        #      crashes the main loop. Exponential backoff on repeated failures.
        if _mqttclient is not None:
            try:
                _mqttclient.check_msg()
                _mqtt_backoff = 1   # reset backoff after a successful call
            except OSError as e:
                print("MQTT error:", e, "— reconnect in", _mqtt_backoff, "s")
                _mqttclient = None
                utime.sleep(_mqtt_backoff)
                _mqtt_backoff = min(_mqtt_backoff * 2, MQTT_BACKOFF_MAX)
                _mqtt_connect()
        else:
            # No client yet (or lost): try reconnect with backoff
            if wifi.isconnected():
                if _mqtt_connect():
                    _mqtt_backoff = 1
                else:
                    utime.sleep(_mqtt_backoff)
                    _mqtt_backoff = min(_mqtt_backoff * 2, MQTT_BACKOFF_MAX)

        # 3) LED render (only when new data arrived) ───────────────────────────
        if state["dirty"]:
            state["dirty"] = False
            _update_leds()

        # 4) Periodic debug: print current state every 30 s
        #    Remove or comment out once topics are confirmed correct.
        if utime.time() % 30 == 0:
            print("STATE:", state)

        # 5) NTP periodic re-sync ──────────────────────────────────────────────
        if utime.time() - _last_ntp_s >= NTP_INTERVAL_S:
            _last_ntp_s = utime.time()
            try:
                ntp.sync_time(wifi)
                print("NTP:", ntp.get_time())
            except OSError as e:
                print("NTP sync failed:", e)

        utime.sleep_ms(LOOP_MS)

except KeyboardInterrupt:
    print("Stopped by user — cleaning up")
    if _mqttclient is not None:
        try:
            _mqttclient.disconnect()
        except Exception:
            pass
    apache.stop_webserver()
    led_ring1.all_off()
    led_ring2.all_off()
    wifi.disconnect()

