# class_color_wheel.py
# WS2812B NeoPixel ring driver for ESP32 (MicroPython)
# FIX: removed time.sleep() from render path, single write() per frame,
#      precomputed gradient, explicit bpp=3 + timing=1, no heap alloc in hot-loop.

import time
import machine
import neopixel


class color_wheel:
    def __init__(self, pixel_count=12, pin=11, brightness=16):
        self.pixel_count = pixel_count
        self.brightness = brightness
        # FIX: explicit bpp=3 (RGB, WS2812B) and timing=1 (800 kHz)
        self.np = neopixel.NeoPixel(machine.Pin(pin), pixel_count, bpp=3, timing=1)

        # Precompute red→green gradient (index 0=red/low, n-1=green/full).
        # Avoids repeated float math in the render hot-path.
        n = pixel_count
        self._gradient = []
        for i in range(n):
            g_pct = i * 100 // max(n - 1, 1)
            r_pct = 100 - g_pct
            self._gradient.append(
                (r_pct * brightness // 100, g_pct * brightness // 100, 0)
            )

        # Ring-2 channel state (number of lit LEDs per colour)
        self._ch_r = 0
        self._ch_g = 0

    # ── Blocking startup animations (only called during init, not in main loop) ──

    def show_error(self):
        """Flash red 2×. Blocking — use at startup/init only."""
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
        """Flash blue 2×. Blocking — use at startup/init only."""
        for _ in range(2):
            for j in range(self.pixel_count):
                self.np[j] = (0, 0, self.brightness)
            self.np.write()
            time.sleep_ms(500)
            for j in range(self.pixel_count):
                self.np[j] = (0, 0, 0)
            self.np.write()
            time.sleep_ms(500)

    # ── Non-blocking render methods (safe to call from main loop) ──────────────

    def set_ring1_percent(self, percent):
        """Ring 1: show SoC percentage as red→green gradient. Single write()."""
        percent = max(0.0, min(100.0, float(percent)))
        num_leds = round(percent * self.pixel_count / 100)
        num_leds = max(0, min(self.pixel_count, num_leds))
        for i in range(self.pixel_count):
            self.np[i] = self._gradient[i] if i < num_leds else (0, 0, 0)
        self.np.write()

    def set_ring2_channels(self, num_r, num_g):
        """Ring 2: overlay red (load) and green (solar) channels. Single write()."""
        self._ch_r = max(0, min(self.pixel_count, num_r))
        self._ch_g = max(0, min(self.pixel_count, num_g))
        brt = self.brightness
        for i in range(self.pixel_count):
            r = brt if i < self._ch_r else 0
            g = brt if i < self._ch_g else 0
            self.np[i] = (r, g, 0)
        self.np.write()

    def all_off(self):
        """Turn off all LEDs."""
        for i in range(self.pixel_count):
            self.np[i] = (0, 0, 0)
        self.np.write()

    # ── Legacy compatibility wrappers ──────────────────────────────────────────
    # Kept so existing call-sites in test scripts continue to work.
    # FIX: no more time.sleep() in render path, single write().

    def display_percentage1(self, percent):
        """Legacy: Ring 1, red→green gradient. No animation delay."""
        if percent < 0 or percent > 100:
            print("Error: Percentage not correct", percent)
            self.show_error()
        else:
            self.set_ring1_percent(percent)

    def display_percentage2(self, percent):
        """Legacy: Ring 2, green→red gradient (single channel). No animation delay."""
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
        """Legacy: set N LEDs of one colour channel on ring2, preserving other channels."""
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

