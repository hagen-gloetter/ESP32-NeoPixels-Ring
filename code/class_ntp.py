# class_ntp.py
# NTP time sync with CET/CEST correction for ESP32 (MicroPython)
# FIX: DST formula was wrong (day - weekday + 1 is off by days at month boundary).
#      Correct formula: day - (weekday + 1) % 7
#      Replaced machine.reset() on timeout with OSError so caller can decide.

import ntptime
import utime
import machine


class NTPClock:
    def __init__(self):
        self.rtc = machine.RTC()

    def sync_time(self, wlan, timeout_s=30):
        """Sync RTC from NTP (UTC) and apply CET/CEST offset.

        Raises OSError if WiFi is not connected within timeout_s.
        """
        t0 = utime.time()
        while not wlan.isconnected():
            if utime.time() - t0 >= timeout_s:
                raise OSError("NTP sync failed: WiFi not connected after {}s".format(timeout_s))
            utime.sleep_ms(500)

        ntptime.settime()   # sets utime to UTC
        year, month, day, hour, minute, second, weekday, _ = utime.localtime()
        offset = 2 if self._is_dst(month, day, weekday) else 1
        hour = (hour + offset) % 24
        # weekday in RTC datetime uses the same 0=Mon..6=Sun convention
        self.rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
        print("NTP synced: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d} CET{:+d}".format(
            year, month, day, hour, minute, second, offset))

    @staticmethod
    def _is_dst(month, day, weekday):
        """EU DST: active from last Sunday in March to last Sunday in October.

        weekday: 0=Monday ... 6=Sunday  (MicroPython utime convention)
        FIX: correct last-Sunday formula is day - (weekday + 1) % 7
             Old formula (day - weekday + 1) was wrong for all weekdays.
        """
        if month < 3 or month > 10:
            return False
        if 3 < month < 10:
            return True
        # Most recent Sunday on or before today
        last_sun = day - (weekday + 1) % 7
        if month == 3:
            return last_sun >= 25
        # month == 10: DST ends on last Sunday >= 25
        return last_sun < 25

    def get_time(self):
        """Return current RTC time as HH:MM:SS string."""
        _, _, _, _, h, m, s, _ = self.rtc.datetime()
        return "{:02d}:{:02d}:{:02d}".format(h, m, s)

