"""
main.py — Solar/Battery NeoPixel Monitor (3-Ring version)
==========================================================
Board  : ESP32 (MicroPython ≥ 1.20)
Authors: ramona@gloetter.de & hagen@gloetter.de

Hardware
--------
Three 12-LED WS2812B NeoPixel rings (bpp=3, RGB, 800 kHz):

  Ring 1 — GPIO 25  (AC load, full red ring)
    All 12 LEDs show AC output load in Watts.
    Scale: 200 W/LED, max 2400 W (12 × 200 W).
    Partial-LED dimming for ~17 W resolution.
    Above 2400 W all 12 LEDs pulse (breathing effect, ~2 s cycle).

  Ring 2 — GPIO 27  (Solar production, full green ring)
    All 12 LEDs show total solar power in Watts.
    Same scale and overflow behaviour as Ring 1.

  Ring 3 — GPIO 26  (Battery SoC + status indicators)
    LEDs 1–10 (indices 0–9) : Average SoC of all 3 battery packs,
                              red→green gradient, 10 %/LED,
                              partial-LED dimming.
    LED 11    (index 10)    : WiFi status — blue 50 % = online, off = offline.
    LED 12    (index 11)    : MQTT status — magenta 50 % = connected, off = lost.

Architecture
------------
- ``state`` dict is the single source of truth; the MQTT callback only
  writes here (no LED calls inside the callback).
- LED rendering happens exclusively in ``_update_leds()``, called from the
  main loop when ``state["dirty"]`` is True or overflow pulsing is active.
- A hardware WDT (8 s) resets the device if the main loop ever stalls.
- A background thread serves a minimal HTTP status page on port 80.

Required files on the device filesystem
-----------------------------------------
  secrets_wifi.json   — WiFi credentials
  secrets_mqtt.json   — MQTT broker credentials
"""

import utime
import machine
import class_wifi_connection
from class_mqtt import MQTT
from class_color_wheel import color_wheel
import class_webserver
import class_ntp

# ── Configuration ──────────────────────────────────────────────────────────────
RING1_PIN        = 25          # GPIO for Ring 1 (AC load, red)
RING2_PIN        = 27          # GPIO for Ring 2 (solar, green)
RING3_PIN        = 26          # GPIO for Ring 3 (SoC + status)
LED_COUNT        = 12          # LEDs per ring
BRIGHTNESS       = 16          # Max PWM brightness (0–255; keep low for 5 V USB)

CLIENT_ID        = b"led-ring01"
MQTT_JSON        = "secrets_mqtt.json"

# MQTT topics as bytes — must match exactly what the broker publishes
TOPIC_SOC1       = b"Seplos/BatteryPack1/soc"
TOPIC_SOC2       = b"Seplos/BatteryPack2/soc"
TOPIC_SOC3       = b"Seplos/BatteryPack3/soc"
TOPIC_ACOUTW     = b"solaranlage/pip/acoutw"
TOPIC_SOLARW     = b"solaranlage/pip/totalsolarw"
_TOPICS          = (TOPIC_SOC1, TOPIC_SOC2, TOPIC_SOC3, TOPIC_ACOUTW, TOPIC_SOLARW)

LOOP_MS          = 100         # main-loop tick in ms (10 Hz)
NTP_INTERVAL_S   = 600         # NTP re-sync every 10 minutes
MQTT_BACKOFF_MAX = 6           # max reconnect delay in seconds (must be < WDT timeout 8 s)

# Watt scale for Ring 1 and Ring 2
WATTS_PER_LED    = 200         # W per full LED
MAX_RING_W       = 2400        # 12 LEDs × 200 W/LED — overflow above this

# ── Shared state ───────────────────────────────────────────────────────────────
# Single source of truth; MQTT callback only writes here.
# Webserver thread reads this dict (MicroPython GIL protects individual ops).
state = {
    "SOC1":        0.0,
    "SOC2":        0.0,
    "SOC3":        0.0,
    "acoutw":      0,
    "totalsolarw": 0,
    "mqtt_ok":     False,  # True while MQTT broker is connected
    "dirty":       True,   # True → LEDs need a redraw
}

# ── Hardware init ──────────────────────────────────────────────────────────────
led_ring1 = color_wheel(LED_COUNT, RING1_PIN, BRIGHTNESS)
led_ring2 = color_wheel(LED_COUNT, RING2_PIN, BRIGHTNESS)
led_ring3 = color_wheel(LED_COUNT, RING3_PIN, BRIGHTNESS)
led_ring3.show_wifi()           # blue flash: "setup in progress"

# ── WiFi ───────────────────────────────────────────────────────────────────────
print("Setup WiFi")
wifi = class_wifi_connection.WifiConnect()
wifi_status, _, _ = wifi.connect()

if wifi_status == "online":
    led_ring2.blink_blue(3)     # Ring 2 blinks blue 3× on success
    try:
        import webrepl
        webrepl.start()
        print("WebREPL started")
    except Exception as e:
        print("WebREPL start failed:", e)
else:
    led_ring1.blink_blue(3)     # Ring 1 blinks blue 3× on failure

# ── NTP ────────────────────────────────────────────────────────────────────────
print("NTP sync")
ntp = class_ntp.NTPClock()
try:
    ntp.sync_time(wifi)
except OSError as e:
    print("NTP initial sync failed (will retry):", e)
_last_ntp_s = utime.time()

# ── MQTT ───────────────────────────────────────────────────────────────────────
_mqtt_obj     = MQTT(MQTT_JSON)
_mqttclient   = None
_mqtt_backoff = 1              # current backoff delay in seconds

# Set True temporarily to log ALL broker messages — helps find correct topic names.
# Set back to False once topics are confirmed.
DEBUG_ALL_TOPICS = False


def on_message(topic, msg):
    """MQTT message callback — called by ``check_msg()`` in the main loop.

    Intentionally minimal: only updates the ``state`` dict and sets
    ``state["dirty"]`` to True.  No LED writes, no sleeps, no side-effects.
    LED rendering is deferred to ``_update_leds()`` in the main loop.

    Args:
        topic (bytes): MQTT topic of the incoming message.
        msg (bytes):   Message payload.
    """
    try:
        if topic == TOPIC_SOC1:
            state["SOC1"] = float(msg)
        elif topic == TOPIC_SOC2:
            state["SOC2"] = float(msg)
        elif topic == TOPIC_SOC3:
            state["SOC3"] = float(msg)
        elif topic == TOPIC_SOLARW:
            state["totalsolarw"] = int(msg)
        elif topic == TOPIC_ACOUTW:
            state["acoutw"] = int(msg)
        else:
            if DEBUG_ALL_TOPICS:
                print("ALL:", topic, "=", msg)
            return
        state["dirty"] = True
        print("MQTT rx:", topic, "=", msg)
    except Exception as e:
        print("MQTT parse error:", type(e).__name__, e, "| topic:", topic, "| msg:", msg)


def _mqtt_connect():
    """Connect to the MQTT broker, configure the socket timeout, and subscribe.

    Sets a 0.5 s socket timeout on the underlying socket so that
    ``check_msg()`` never blocks indefinitely.  On failure the global
    ``_mqttclient`` is set to ``None`` so the main loop triggers a retry.
    Updates ``state["mqtt_ok"]`` to reflect the connection result.

    Returns:
        bool: ``True`` if the connection and subscriptions succeeded.
    """
    global _mqttclient
    try:
        _mqttclient = _mqtt_obj.connect(CLIENT_ID, keepalive=60)
        if hasattr(_mqttclient, 'sock') and _mqttclient.sock is not None:
            _mqttclient.sock.settimeout(0.5)
        _mqttclient.set_callback(on_message)
        for t in _TOPICS:
            _mqttclient.subscribe(t)
        if DEBUG_ALL_TOPICS:
            _mqttclient.subscribe(b"#")
            print("DEBUG: wildcard subscription active — all topics will be logged")
        state["mqtt_ok"] = True
        state["dirty"]   = True   # trigger LED redraw for MQTT indicator
        print("MQTT connected, subscribed to", len(_TOPICS), "topics")
        return True
    except OSError as e:
        print("MQTT connect failed:", e)
        _mqttclient      = None
        state["mqtt_ok"] = False
        state["dirty"]   = True
        return False


def _update_leds():
    """Render the current ``state`` to all three NeoPixel rings.

    Ring 1: AC load in Watts, red, 200 W/LED, 12 LEDs, max 2400 W.
    Ring 2: Solar power in Watts, green, 200 W/LED, 12 LEDs, max 2400 W.
    Ring 3: Average SoC (red→green gradient) + WiFi indicator + MQTT indicator.

    Called when ``state["dirty"]`` is True or ``_overflow_mode`` is active.
    Produces exactly three ``np.write()`` calls per invocation (one per ring).
    Never call this from inside ``on_message()``.
    """
    global _overflow_mode

    # Ring 1: AC load — red, 200 W/LED, overflow breathing above 2400 W
    led_ring1.set_ring_watts_full(state["acoutw"], _loop_count, color='r')

    # Ring 2: Solar production — green, 200 W/LED, overflow breathing above 2400 W
    led_ring2.set_ring_watts_full(state["totalsolarw"], _loop_count, color='g')

    # Ring 3: average SoC + WiFi (blue) + MQTT (magenta)
    avg_soc = (state["SOC1"] + state["SOC2"] + state["SOC3"]) / 3.0
    led_ring3.set_ring3_soc(avg_soc, wifi.isconnected(), state["mqtt_ok"])

    # Overflow mode drives continuous per-tick rendering for the breathing effect
    _overflow_mode = (state["acoutw"] > MAX_RING_W or state["totalsolarw"] > MAX_RING_W)


# ── Webserver (background thread) ─────────────────────────────────────────────
apache = class_webserver.Webserver(state)

# ── Loop state ────────────────────────────────────────────────────────────────
_loop_count    = 0      # counter for periodic debug output / pulse phase
_overflow_mode = False  # True while overflow breathing is active

# ── Initial MQTT connect + LED state ──────────────────────────────────────────
_mqtt_connect()
_update_leds()   # show "all off / 0 %" until first MQTT message arrives

# ── Main loop ─────────────────────────────────────────────────────────────────
print("Entering main loop (tick:", LOOP_MS, "ms)")

# ── Hardware Watchdog ─────────────────────────────────────────────────────────
# Resets the ESP32 if the main loop is not reached within 8 s.
# All blocking operations (WiFi reconnect, MQTT backoff) are capped below 8 s.
wdt = machine.WDT(timeout=8000)
print("WDT started (8 s timeout)")

try:
    while True:
        # 0) Feed hardware watchdog ────────────────────────────────────────────
        wdt.feed()

        # 1) WiFi watchdog ─────────────────────────────────────────────────────
        if not wifi.isconnected():
            print("WiFi offline, reconnecting…")
            wifi.check_connection()
            if wifi.isconnected():
                print("WiFi restored, reconnecting MQTT…")
                _mqtt_connect()
                _mqtt_backoff = 1

        # 2) MQTT message pump with per-iteration error handling ───────────────
        if _mqttclient is not None:
            try:
                _mqttclient.check_msg()
                _mqtt_backoff = 1   # reset backoff after a successful call
            except OSError as e:
                print("MQTT error:", e, "— reconnect in", _mqtt_backoff, "s")
                _mqttclient      = None
                state["mqtt_ok"] = False
                state["dirty"]   = True
                wdt.feed()   # feed before intentional sleep — stay within 8 s WDT window
                utime.sleep(_mqtt_backoff)
                _mqtt_backoff = min(_mqtt_backoff * 2, MQTT_BACKOFF_MAX)
                _mqtt_connect()
        else:
            # No client yet (or lost): try reconnect with backoff
            if wifi.isconnected():
                if _mqtt_connect():
                    _mqtt_backoff = 1
                else:
                    wdt.feed()   # feed before intentional sleep — stay within 8 s WDT window
                    utime.sleep(_mqtt_backoff)
                    _mqtt_backoff = min(_mqtt_backoff * 2, MQTT_BACKOFF_MAX)

        # 3) LED render — on new data or while overflow pulsing is active ──────
        if state["dirty"] or _overflow_mode:
            if state["dirty"]:
                state["dirty"] = False
            _update_leds()

        # 4) Heartbeat + state debug every 100 ticks (~10 s) ──────────────────
        _loop_count += 1
        if _loop_count >= 100:
            _loop_count = 0
            print("HEARTBEAT | STATE:", state)

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
    led_ring3.all_off()
    wifi.disconnect()
