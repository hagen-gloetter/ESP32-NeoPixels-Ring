# Written by hagen@gloetter.de 024.002.2023
#

# Setup da stuff
# Micropython:

# Pins used
# NeoPixels Ring
#       Pin = 7


import time
import sys
import random
import os

import machine
import neopixel

# Configure the count of pixels:
PIXEL_COUNT = 12
PIN = 10
np = neopixel.NeoPixel(machine.Pin(PIN), PIXEL_COUNT)


def demo(np):
    n = np.n

    # cycle
    for i in range(4 * n):
        for j in range(n):
            np[j] = (0, 0, 0)
        np[i % n] = (255, 255, 255)
        np.write()
        time.sleep_ms(25)

    # bounce
    for i in range(4 * n):
        for j in range(n):
            np[j] = (0, 0, 128)
        if (i // n) % 2 == 0:
            np[i % n] = (0, 0, 0)
        else:
            np[n - 1 - (i % n)] = (0, 0, 0)
        np.write()
        time.sleep_ms(60)

    # fade in/out
    for i in range(0, 4 * 256, 8):
        for j in range(n):
            if (i // 256) % 2 == 0:
                val = i & 0xff
            else:
                val = 255 - (i & 0xff)
            np[j] = (val, 0, 0)
        np.write()

    # clear
    for i in range(n):
        np[i] = (0, 0, 0)
    np.write()



if __name__ == "__main__":
    np[0] = (127, 0, 0) # set to red, full brightness
    np[1] = (0, 128, 0) # set to green, half brightness
    np[2] = (0, 0, 64)  # set to blue, quarter brightness

    np.write()
    demo(np)


