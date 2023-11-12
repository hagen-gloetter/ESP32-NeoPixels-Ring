# NTP Klasse

import ntptime
import utime
import machine


class NTPClock:
    def __init__(self):
        self.timeout = 5 * 60  # 5 minutes timeout in seconds
        self.rtc = machine.RTC()

    def sync_time(self, wlan):
        start_time = utime.time()
        while not wlan.isconnected():
            if utime.time() - start_time >= self.timeout:
                machine.reset()
            utime.sleep(1)
        ntptime.settime()
        year, month, day, hour, minute, second, weekday, yearday = utime.localtime()
        is_dst = self.is_dst()
        # Convert to CET time zone
        hour = (hour + 2) % 24 if is_dst else (hour + 1) % 24
        # Set RTC time
        self.rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
        print(f"{year}, {month}, {day}, {weekday}, {hour}, {minute}, {second}")

    def is_dst(self):
        # Determine if DST is in effect
        year, month, day, hour, minute, second, weekday, yearday = utime.localtime()
        if month < 3 or month > 10:
            return False
        if month > 3 and month < 10:
            return True
        previous_sunday = day - weekday + 1
        if month == 3:
            return previous_sunday >= 25
        if month == 10:
            return previous_sunday < 25

    def get_time(self):
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        return "{:02d}:{:02d}:{:02d}".format(hour, minute, second)

