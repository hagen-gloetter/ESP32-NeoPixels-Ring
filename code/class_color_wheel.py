import time
import sys
import random
import os

import machine
import neopixel

class color_wheel:
    def __init__(self, pixel_count=12, pin=10):
        self.pixel_count = pixel_count
        self.pin = pin
        self.np = neopixel.NeoPixel(machine.Pin(self.pin), self.pixel_count)
        self.brightness=8

    def show_error(self):
        for i in range(2):
            for j in range(self.np.n):
                self.np[j] = (self.brightness, 0, 0)
                self.np.write()
            
            time.sleep(0.5)
            
            for j in range(self.np.n):
                self.np[j] = (0, 0, 0)
                self.np.write()
            
            time.sleep(0.5)

    def display_percentage(self, percent):
        if (percent < 0 or percent > 100):
            print("Error: Percentage not correct " + str(percent))
            self.show_error()
            
        else:
            # 12 leds = 100% -> 1 led = 8.3%
            # tolerance: 12 leds = 96% -> 1 led = 8%
            #num_leds = round(percent/8.3)
            num_leds = round(percent/8.3)
            #print(num_leds)
            
            for i in range(num_leds):
                time.sleep(0.25)
                #self.np[i] = (round(self.brightness-(i*(100/self.pixel_count))), round(i*(100/self.pixel_count)), 0)
                B = 0
                G = i*(100/(self.pixel_count-1))
                R = 100-G
                print (f"R={R}% G={G}% B={B}%")
                R = round(R/100*self.brightness)
                G = round(G/100*self.brightness)
                self.np[i] = (R, G, B)
                self.np.write()
            
            for i in range(self.np.n-1, num_leds-1, -1):
                time.sleep(0.25)
                self.np[i] = (0, 0, 0)
                self.np.write()
                
def main():
    led_ring = color_wheel(12, 10)
    led_ring.display_percentage(100)
    led_ring.display_percentage(50)


if __name__ == "__main__":
    sys.exit(main())
