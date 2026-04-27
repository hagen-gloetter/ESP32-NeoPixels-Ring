"""
class_ntp.py — NTP time synchronisation with EU CET/CEST correction (MicroPython).

Syncs the ESP32 hardware RTC via ``ntptime`` (NTP pool server), then applies
the correct Central European Time offset (+1 h CET / +2 h CEST) using a
proper last-Sunday-of-month DST boundary formula.

Typical usage::

    from class_ntp import NTPClock

    ntp = NTPClock()
    ntp.sync_time(wifi)       # raises OSError if WiFi is unavailable
    print(ntp.get_time())     # → "14:32:07"

Re-sync periodically (every ~10 min) because the ESP32 crystal drifts.
"""

import ntptime
import utime
import machine


class NTPClock:
    """Hardware RTC wrapper with NTP sync and EU daylight saving time support.

    After ``sync_time()`` the RTC is set to local time (CET or CEST).
    ``get_time()`` reads the RTC directly so it keeps working even if the
    network is temporarily unavailable.
    """

    def __init__(self):
        self.rtc = machine.RTC()

    def sync_time(self, wlan, timeout_s=30):
        """Sync the RTC from NTP and apply the CET/CEST offset.

        Blocks until WiFi is available or *timeout_s* is reached.

        Args:
            wlan:          A ``WifiConnect`` (or any object with an
                           ``isconnected()`` method).
            timeout_s (int): Maximum seconds to wait for WiFi. Default: 30.

        Raises:
            OSError: If WiFi is not connected within *timeout_s* seconds.
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
        """Return True if the given date falls within EU summer time (CEST).

        DST is active from the last Sunday of March to the last Sunday of October.
        Last-Sunday formula: ``last_sun = day - (weekday + 1) % 7``

        Args:
            month (int):   Month number (1–12).
            day (int):     Day of month (1–31).
            weekday (int): 0 = Monday … 6 = Sunday (MicroPython ``utime`` convention).

        Returns:
            bool: ``True`` if CEST (+2 h) applies, ``False`` for CET (+1 h).
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
        """Return the current RTC time as a ``HH:MM:SS`` string."""
        _, _, _, _, h, m, s, _ = self.rtc.datetime()
        return "{:02d}:{:02d}:{:02d}".format(h, m, s)

