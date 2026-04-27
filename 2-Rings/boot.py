# This file is executed on every boot (including wake-boot from deepsleep)
# boot.py runs BEFORE main.py and BEFORE WiFi is connected.
import esp
esp.osdebug(None)  # suppress verbose ESP-IDF debug output on UART

# WebREPL: start() requires an active WiFi connection.
# Calling it here (before main.py connects WiFi) causes an OSError in
# webrepl.py line 73. Options:
#   A) Leave it commented out — use USB/mpremote for deployment (recommended).
#   B) Uncomment and call webrepl.start() from main.py AFTER wifi.connect().

# import webrepl
# webrepl.start()
