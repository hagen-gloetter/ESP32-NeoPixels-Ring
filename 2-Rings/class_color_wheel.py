"""
class_color_wheel.py — WS2812B NeoPixel ring driver for ESP32 (MicroPython).

Provides non-blocking LED render methods for two 12-LED NeoPixel rings:

  Ring 1 (SoC display)
    10 LEDs show the average battery State of Charge as a red→green gradient.
    Each LED represents 10 %; the next LED is dimmed proportionally for the
    fractional remainder (e.g. 75 % → 7 full LEDs + LED 8 at 50 % brightness).
    LED 11 (index 10) is reserved as an MQTT status indicator (magenta = connected).
    LED 12 (index 11) is reserved as a WiFi status indicator (blue = online).

  Ring 2 (Energy display — split ring)
    LEDs 1–6  (indices 0–5,  clockwise)         : AC load in Watts, red.
    LEDs 12–7 (indices 11–6, counter-clockwise)  : Solar power in Watts, green.
    Scale: 1000 W per full LED; the partial LED is dimmed proportionally.
    When either value exceeds 6000 W all 6 segment LEDs pulse (breathing effect).

Hardware notes:
  WS2812B LEDs require bpp=3 (RGB) and timing=1 (800 kHz).
  Keep BRIGHTNESS ≤ 32 when powered from the ESP32 USB supply to avoid
  overloading the 5 V rail.

Typical usage::

    from class_color_wheel import color_wheel

    ring1 = color_wheel(pixel_count=12, pin=25, brightness=16)
    ring2 = color_wheel(pixel_count=12, pin=27, brightness=16)

    ring1.set_ring1_percent(75.0, wifi_ok=True, mqtt_ok=True)
    ring2.set_ring2_watts(acoutw=1500, solarw=2300, tick=loop_count)
"""

import time
import machine
import neopixel


class color_wheel:
    """Non-blocking NeoPixel ring controller for a single 12-LED WS2812B ring.

    All render methods write the full pixel buffer in a single ``np.write()``
    call to avoid flicker and minimise SPI bus time.
    Blocking methods (``blink_blue``, ``show_error``) are only used during
    start-up and are clearly marked — never call them from the main loop.

    Args:
        pixel_count (int): Number of LEDs in the ring. Default: 12.
        pin (int):         ESP32 GPIO number connected to the data line.
        brightness (int):  Maximum pixel brightness (0–255).
                           Values above ~32 may overdraw USB power.
    """

    def __init__(self, pixel_count=12, pin=11, brightness=16):
        self.pixel_count = pixel_count
        self.brightness = brightness
        # bpp=3 → RGB (WS2812B); timing=1 → 800 kHz signal
        self.np = neopixel.NeoPixel(machine.Pin(pin), pixel_count, bpp=3, timing=1)

        # Precompute the red→green gradient once at init so the render methods
        # do no floating-point work.  Index 0 = full red (0 %), n-1 = full green (100 %).
        n = pixel_count
        self._gradient = []
        for i in range(n):
            g_pct = i * 100 // max(n - 1, 1)
            r_pct = 100 - g_pct
            self._gradient.append(
                (r_pct * brightness // 100, g_pct * brightness // 100, 0)
            )

        # Last known LED counts for Ring 2 legacy channel API
        self._ch_r = 0
        self._ch_g = 0

    # ─────────────────────────────────────────────────────────────────────────
    # Blocking startup animations
    # These methods use time.sleep_ms() and must only be called during boot,
    # never from inside the main loop.
    # ─────────────────────────────────────────────────────────────────────────

    def show_error(self):
        """Flash all LEDs red twice to signal a hardware/config error.

        Blocking (2 × 1 s). Call during boot/init only.
        """
        for _ in range(2):
            for j in range(self.pixel_count):
                self.np[j] = (self.brightness, 0, 0)
            self.np.write()
            time.sleep_ms(500)
            for j in range(self.pixel_count):
                self.np[j] = (0, 0, 0)
            self.np.write()
            time.sleep_ms(500)

    def show_wifi(self):
        """Flash all LEDs blue twice as a "connecting" indicator.

        Blocking (2 × 0.8 s). Call during boot/init only.
        """
        self.blink_blue(2)

    def blink_blue(self, n=3):
        """Flash all LEDs blue *n* times (400 ms on / 400 ms off).

        Args:
            n (int): Number of flashes. Default: 3.

        Blocking. Call during boot/init only.
        """
        for _ in range(n):
            for j in range(self.pixel_count):
                self.np[j] = (0, 0, self.brightness)
            self.np.write()
            time.sleep_ms(400)
            for j in range(self.pixel_count):
                self.np[j] = (0, 0, 0)
            self.np.write()
            time.sleep_ms(400)

    # ─────────────────────────────────────────────────────────────────────────
    # Non-blocking render methods — safe to call every main-loop tick
    # ─────────────────────────────────────────────────────────────────────────

    def set_ring1_percent(self, percent, wifi_ok=True, mqtt_ok=True):
        """Ring 1: SoC on indices 0-9 (10 LEDs, 10 %/LED) with partial-LED dimming.

        Scale  : 10 LEDs = 100 %; each full LED = 10 %.
                 The next LED is lit proportionally for the remainder.
                 Example: 75 % → LEDs 0-6 full + LED 7 at 50 % brightness.
        Gradient: red (index 0, low SoC) → green (index 9, full SoC),
                 remapped across the precomputed 12-step gradient.
        Index 10 (LED 11): MQTT status — magenta 50 % when connected, off when lost.
        Index 11 (LED 12): WiFi status  — blue 50 %    when online,    off when lost.
        Single write().

        Args:
            percent (float):  Average SoC 0–100 %.
            wifi_ok (bool):   True if WiFi is currently connected.
            mqtt_ok (bool):   True if MQTT broker is currently connected.
        """
        SOC_LEDS = 10
        percent   = max(0.0, min(100.0, float(percent)))
        full_leds = min(int(percent) // 10, SOC_LEDS)
        partial   = (percent % 10) / 10.0   # fractional brightness of next LED (0.0-0.99)
        n         = self.pixel_count        # 12 — length of precomputed gradient

        for i in range(SOC_LEDS):
            # Remap LED index 0-9 to gradient index 0-(n-1) for full red→green range
            g_idx = i * (n - 1) // (SOC_LEDS - 1)
            if i < full_leds:
                self.np[i] = self._gradient[g_idx]
            elif i == full_leds and partial > 0:
                r, g, b = self._gradient[g_idx]
                self.np[i] = (int(r * partial), int(g * partial), 0)
            else:
                self.np[i] = (0, 0, 0)

        brt = self.brightness
        self.np[10] = (brt // 2, 0, brt // 2) if mqtt_ok else (0, 0, 0)  # LED 11: MQTT magenta
        self.np[11] = (0, 0, brt // 2)         if wifi_ok else (0, 0, 0)  # LED 12: WiFi blue
        self.np.write()

    def set_ring2_channels(self, num_r, num_g):
        """Ring 2 (legacy): overlay red and green LED counts on the same ring.

        Both colours start from index 0 and count upward; where they overlap
        the LED shows yellow (R+G).  Prefer ``set_ring2_watts()`` for the
        current split-ring display.

        Args:
            num_r (int): Number of red LEDs (load channel).
            num_g (int): Number of green LEDs (solar channel).
        """
        self._ch_r = max(0, min(self.pixel_count, num_r))
        self._ch_g = max(0, min(self.pixel_count, num_g))
        brt = self.brightness
        for i in range(self.pixel_count):
            r = brt if i < self._ch_r else 0
            g = brt if i < self._ch_g else 0
            self.np[i] = (r, g, 0)
        self.np.write()

    def set_ring2_watts(self, acoutw, solarw, tick):
        """
        Ring 2: split ring — Load (red, LEDs 0-5) + Solar (green, LEDs 11-6).

        Scale  : 1000 W per full LED; partial LED dimmed proportionally
                 (e.g. 1500 W → 1 full LED + 1 at 50 %).  Max display: 6000 W.
        Layout : Load  → indices 0-5  (LED  1→6,  clockwise)
                 Solar → indices 11-6 (LED 12→7,  counter-clockwise)
        Overflow (> 6000 W per segment): all 6 segment LEDs pulse with a
                 breathing effect (~2 s period).
        tick   : current loop counter — used for pulse phase calculation.
        """
        WATTS_PER_LED = 1000
        MAX_W    = 6000   # 6 LEDs × 1000 W/LED
        MAX_LEDS = 6
        brt = self.brightness

        # Clear all LEDs
        for i in range(12):
            self.np[i] = (0, 0, 0)

        # Pulse brightness: symmetric triangle wave 0.3→1.0→0.3, period = 20 ticks (~2 s)
        phase = tick % 20
        t = phase / 10.0 if phase <= 10 else (20 - phase) / 10.0
        pulse = int(brt * (0.3 + 0.7 * t))

        # ── Load (red): indices 0-5 (LED 1→6, clockwise) ────────────────────
        if acoutw > MAX_W:
            for i in range(MAX_LEDS):
                self.np[i] = (pulse, 0, 0)
        else:
            full    = min(acoutw // WATTS_PER_LED, MAX_LEDS)
            partial = (acoutw % WATTS_PER_LED) / WATTS_PER_LED
            for i in range(full):
                self.np[i] = (brt, 0, 0)
            if full < MAX_LEDS and partial > 0:
                self.np[full] = (int(brt * partial), 0, 0)

        # ── Solar (green): indices 11-6 (LED 12→7, counter-clockwise) ───────
        if solarw > MAX_W:
            for i in range(MAX_LEDS):
                self.np[11 - i] = (0, pulse, 0)
        else:
            full    = min(solarw // WATTS_PER_LED, MAX_LEDS)
            partial = (solarw % WATTS_PER_LED) / WATTS_PER_LED
            for i in range(full):
                self.np[11 - i] = (0, brt, 0)
            if full < MAX_LEDS and partial > 0:
                self.np[11 - full] = (0, int(brt * partial), 0)

        self.np.write()

    def all_off(self):
        """Turn off all LEDs immediately. Safe to call from the main loop."""
        for i in range(self.pixel_count):
            self.np[i] = (0, 0, 0)
        self.np.write()

    # ─────────────────────────────────────────────────────────────────────────
    # Legacy compatibility wrappers
    # Retained so existing test scripts continue to work without modification.
    # New code should call set_ring1_percent() / set_ring2_watts() directly.
    # ─────────────────────────────────────────────────────────────────────────

    def display_percentage1(self, percent):
        """Legacy wrapper: Ring 1 red→green gradient. Delegates to set_ring1_percent()."""
        if percent < 0 or percent > 100:
            print("Error: Percentage not correct", percent)
            self.show_error()
        else:
            self.set_ring1_percent(percent)

    def display_percentage2(self, percent):
        """Legacy wrapper: Ring 2 single-channel gradient. Not used by main loop."""
        if percent < 0 or percent > 100:
            print("Error: Percentage not correct", percent)
            self.show_error()
        else:
            num_leds = round(percent * self.pixel_count / 100)
            num_leds = max(0, min(self.pixel_count, num_leds))
            n = self.pixel_count
            brt = self.brightness
            for i in range(n):
                if i < num_leds:
                    r_pct = i * 100 // max(n - 1, 1)
                    g_pct = 100 - r_pct
                    self.np[i] = (r_pct * brt // 100, g_pct * brt // 100, 0)
                else:
                    self.np[i] = (0, 0, 0)
            self.np.write()

    def set_single_color(self, cnt, color):
        """Legacy wrapper: set *cnt* LEDs of one colour on Ring 2, preserve the other channel.

        Args:
            cnt (int):   Number of LEDs to light.
            color (str): ``'r'`` (red/load), ``'g'`` (green/solar), or ``'b'`` (blue).
        """
        cnt = max(0, min(self.pixel_count, cnt))
        color = color.lower()
        if color == "r":
            self.set_ring2_channels(cnt, self._ch_g)
        elif color == "g":
            self.set_ring2_channels(self._ch_r, cnt)
        elif color == "b":
            # Blue: override everything (no combined mode for blue)
            brt = self.brightness
            for i in range(self.pixel_count):
                self.np[i] = (0, 0, brt if i < cnt else 0)
            self.np.write()

