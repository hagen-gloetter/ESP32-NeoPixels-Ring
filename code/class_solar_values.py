# NTP Klasse

import utime
import machine


class solarvalues:
    def __init__(self):
        self.SOC1 = 0
        self.SOC2 = 0
        self.acoutw = 0
        self.totalsolarw = 0

    def set_values(self, SOC1, SOC2, acoutw, totalsolarw):
        """ set solar values """
        self.SOC1 = SOC1
        self.SOC2 = SOC2
        self.acoutw = acoutw
        self.totalsolarw = totalsolarw
        return 0

    def get_values(self):
        """ get solar values """
        year, month, day, hour, minute, second, weekday, yearday = utime.localtime()
        is_dst = self.is_dst()
        # Convert to CET time zone
        hour = (hour + 2) % 24 if is_dst else (hour + 1) % 24
        # Set RTC time
        self.rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
        self.mydate = (
            f"{year}, {month}, {day}, {weekday}, {hour}, {minute}, {second}")
        list = [self.SOC1, self.SOC2, self.acoutw,
                self.totalsolarw, self.mydate]
        return list

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
