"""
class_color_wheel.py — WS2812B NeoPixel ring driver for ESP32 (MicroPython).

Provides non-blocking LED render methods for three 12-LED NeoPixel rings:

  Ring 1 (Power consumption — full ring, red)
    All 12 LEDs show AC load in Watts.
    Scale: 200 W per full LED, max 2400 W (12 × 200 W).
    Overflow (> 2400 W): all 12 LEDs pulse with a breathing effect.

  Ring 2 (Solar production — full ring, green)
    All 12 LEDs show solar power in Watts.
    Scale: 200 W per full LED, max 2400 W (12 × 200 W).
    Overflow (> 2400 W): all 12 LEDs pulse with a breathing effect.

  Ring 3 (State of Charge + status indicators)
    Index 0–9  (LED  1–10): SoC gradient red→green, 10 %/LED with
                            partial-LED dimming.
    Index 10   (LED 11):    WiFi status — blue 50 % when online, off when lost.
    Index 11   (LED 12):    MQTT status — magenta 50 % when connected, off when lost.

Hardware notes:
  WS2812B LEDs require bpp=3 (RGB) and timing=1 (800 kHz).
  Keep BRIGHTNESS ≤ 32 when powered from the ESP32 USB supply to avoid
  overloading the 5 V rail.

Typical usage::

    from class_color_wheel import color_wheel

    ring1 = color_wheel(pixel_count=12, pin=25, brightness=16)
    ring2 = color_wheel(pixel_count=12, pin=27, brightness=16)
    ring3 = color_wheel(pixel_count=12, pin=26, brightness=16)

    ring1.set_ring_watts_full(1600, tick=loop_count, color='r')
    ring2.set_ring_watts_full(2200, tick=loop_count, color='g')
    ring3.set_ring3_soc(75.0, wifi_ok=True, mqtt_ok=True)
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

    def set_ring_watts_full(self, watts, tick, color='r'):
        """Full-ring watt display: all 12 LEDs, 200 W/LED, max 2400 W.

        Scale  : 12 LEDs = 2400 W; each full LED = 200 W.
                 The next LED is lit proportionally for the remainder
                 (e.g. 500 W → 2 full LEDs + LED 3 at 50 % brightness).
        Overflow (> 2400 W): all 12 LEDs pulse with a symmetric triangle-wave
                 breathing effect (~2 s period, 0.3→1.0→0.3 brightness).
        color  : ``'r'`` → red (load ring), ``'g'`` → green (solar ring).
        tick   : current loop counter — used for pulse phase calculation.
        Single write().

        Args:
            watts (int):  Power value in Watts.
            tick (int):   Main-loop iteration counter for pulse phase.
            color (str):  ``'r'`` for red, ``'g'`` for green. Default: ``'r'``.
        """
        WATTS_PER_LED = 200
        MAX_W    = 2400   # 12 LEDs × 200 W/LED
        MAX_LEDS = 12
        brt = self.brightness

        # Pulse brightness: symmetric triangle wave 0.3→1.0→0.3, period = 20 ticks (~2 s)
        phase = tick % 20
        t = phase / 10.0 if phase <= 10 else (20 - phase) / 10.0
        pulse = int(brt * (0.3 + 0.7 * t))

        is_red = (color.lower() != 'g')

        if watts > MAX_W:
            # Overflow: all LEDs breathing
            c = (pulse, 0, 0) if is_red else (0, pulse, 0)
            for i in range(MAX_LEDS):
                self.np[i] = c
        else:
            full    = min(watts // WATTS_PER_LED, MAX_LEDS)
            partial = (watts % WATTS_PER_LED) / WATTS_PER_LED
            full_c  = (brt, 0, 0) if is_red else (0, brt, 0)
            for i in range(full):
                self.np[i] = full_c
            if full < MAX_LEDS and partial > 0:
                dim = int(brt * partial)
                self.np[full] = (dim, 0, 0) if is_red else (0, dim, 0)
            for i in range(full + (1 if partial > 0 else 0), MAX_LEDS):
                self.np[i] = (0, 0, 0)

        self.np.write()

    def set_ring3_soc(self, percent, wifi_ok=True, mqtt_ok=True):
        """Ring 3: SoC on indices 0-9 + WiFi on index 10 + MQTT on index 11.

        Scale  : 10 LEDs = 100 %; each full LED = 10 %.
                 The next LED is lit proportionally for the remainder.
                 Example: 75 % → LEDs 0-6 full + LED 7 at 50 % brightness.
        Gradient: red (index 0, low SoC) → green (index 9, full SoC),
                 remapped across the precomputed 12-step gradient.
        Index 10 (LED 11): WiFi status  — blue 50 %    when online, off when lost.
        Index 11 (LED 12): MQTT status  — magenta 50 % when connected, off when lost.
        Single write().

        Args:
            percent (float):  Average SoC 0–100 %.
            wifi_ok (bool):   True if WiFi is currently connected.
            mqtt_ok (bool):   True if MQTT broker is currently connected.
        """
        SOC_LEDS = 10
        percent   = max(0.0, min(100.0, float(percent)))
        full_leds = min(int(percent) // 10, SOC_LEDS)
        partial   = (percent % 10) / 10.0   # fractional brightness of next LED (0.0–0.99)
        n         = self.pixel_count        # 12 — length of precomputed gradient
        brt       = self.brightness

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

        # LED 11 (index 10): WiFi — blue 50 %
        self.np[10] = (0, 0, brt // 2) if wifi_ok else (0, 0, 0)
        # LED 12 (index 11): MQTT — magenta 50 % = (R/2, 0, B/2)
        self.np[11] = (brt // 2, 0, brt // 2) if mqtt_ok else (0, 0, 0)
        self.np.write()

    def set_ring1_percent(self, percent, wifi_ok=True):
        """Ring 1 (2-ring version): SoC on indices 0-9 with partial-LED dimming.

        Retained for backward compatibility with 2-ring deployments.
        New code should use ``set_ring3_soc()`` instead.

        Index 10 (LED 11): unused — always off.
        Index 11 (LED 12): WiFi status — blue 50 % when online, off when lost.
        """
        SOC_LEDS = 10
        percent   = max(0.0, min(100.0, float(percent)))
        full_leds = min(int(percent) // 10, SOC_LEDS)
        partial   = (percent % 10) / 10.0
        n         = self.pixel_count

        for i in range(SOC_LEDS):
            g_idx = i * (n - 1) // (SOC_LEDS - 1)
            if i < full_leds:
                self.np[i] = self._gradient[g_idx]
            elif i == full_leds and partial > 0:
                r, g, b = self._gradient[g_idx]
                self.np[i] = (int(r * partial), int(g * partial), 0)
            else:
                self.np[i] = (0, 0, 0)

        self.np[10] = (0, 0, 0)
        self.np[11] = (0, 0, self.brightness // 2) if wifi_ok else (0, 0, 0)
        self.np.write()

    def set_ring2_channels(self, num_r, num_g):
        """Ring 2 (legacy): overlay red and green LED counts on the same ring.

        Both colours start from index 0 and count upward; where they overlap
        the LED shows yellow (R+G).  Prefer ``set_ring_watts_full()`` for the
        current full-ring watt display.

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
        """Ring 2 (2-ring version): split ring — Load (red) + Solar (green).

        Retained for backward compatibility with 2-ring deployments.
        New code should use ``set_ring_watts_full()`` on separate ring objects.
        """
        WATTS_PER_LED = 1000
        MAX_W    = 6000
        MAX_LEDS = 6
        brt = self.brightness

        for i in range(12):
            self.np[i] = (0, 0, 0)

        phase = tick % 20
        t = phase / 10.0 if phase <= 10 else (20 - phase) / 10.0
        pulse = int(brt * (0.3 + 0.7 * t))

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
        """Legacy wrapper: set *cnt* LEDs of one colour, preserve the other channel.

        Args:
            cnt (int):   Number of LEDs to light.
            color (str): ``'r'`` (red), ``'g'`` (green), or ``'b'`` (blue).
        """
        cnt = max(0, min(self.pixel_count, cnt))
        color = color.lower()
        if color == "r":
            self.set_ring2_channels(cnt, self._ch_g)
        elif color == "g":
            self.set_ring2_channels(self._ch_r, cnt)
        elif color == "b":
            brt = self.brightness
            for i in range(self.pixel_count):
                self.np[i] = (0, 0, brt if i < cnt else 0)
            self.np.write()
