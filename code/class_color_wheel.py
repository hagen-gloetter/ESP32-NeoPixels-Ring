import time
import sys
import random
import os

import machine
import neopixel

class color_wheel:
    def __init__(self, pixel_count=12, pin=11):
        self.pixel_count = pixel_count
        self.pin = pin
        self.np = neopixel.NeoPixel(machine.Pin(self.pin), self.pixel_count)
        self.brightness=16
        self.Rarray = self.pixel_count  * [0]
        self.Garray = self.pixel_count  * [0]
        self.Barray = self.pixel_count  * [0]

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

    def show_wifi(self):
        for i in range(2):
            for j in range(self.np.n):
                self.np[j] = (0, 0, self.brightness)
                self.np.write()
            
            time.sleep(0.5)
            
            for j in range(self.np.n):
                self.np[j] = (0, 0, 0)
                self.np.write()
            
            time.sleep(0.5)
            
    def set_single_color(self, cnt, color):
        if cnt > self.pixel_count:
            cnt = self.pixel_count
        array=self.pixel_count  * [0]
        for i in range(cnt):
            array[i] = self.brightness  
        if "R" == color or "r" == color :
            self.Rarray=array
        if "G" == color or "g" == color :
            self.Garray=array
        if "B" == color or "b" == color :
            self.Barray=array

        for i in range(self.pixel_count):
            time.sleep(0.1)
            self.np[i] = (self.Rarray[i], self.Garray[i], self.Barray[i])
            self.np.write()
        
        
        

    def display_percentage1(self, percent):
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
                #print (f"R={R}% G={G}% B={B}%")
                R = round(R/100*self.brightness)
                G = round(G/100*self.brightness)
                self.np[i] = (R, G, B)
                self.np.write()
            
            for i in range(self.np.n-1, num_leds-1, -1):
                time.sleep(0.25)
                self.np[i] = (0, 0, 0)
                self.np.write()

    def display_percentage2(self, percent):
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
                R = i*(100/(self.pixel_count-1))
                G = 100-R
                #print (f"R={R}% G={G}% B={B}%")
                R = round(R/100*self.brightness)
                G = round(G/100*self.brightness)
                self.np[i] = (R, G, B)
                self.np.write()
            
            for i in range(self.np.n-1, num_leds-1, -1):
                time.sleep(0.25)
                self.np[i] = (0, 0, 0)
                self.np.write()


    def show_all(self,cnt=24):
        R = self.brightness
        G = 0 #self.brightness
        B = 0 #self.brightness
        for i in range(cnt):
            self.np[i] = (R, G, B)
            self.np.write()
            time.sleep(0.25)
        
                
def main():
    led_ring = color_wheel(12, 27)
    led_ring2 = color_wheel(12, 25)
    
    led_ring.set_single_color(12,"r")
    led_ring.set_single_color(5,"g")
    led_ring.set_single_color(3,"b")
    
#    led_ring.show_wifi()
#    led_ring.show_all(12)
#    led_ring.display_percentage1(100)
#    led_ring.display_percentage1(50)
    
#    led_ring2.show_all(12)
#    led_ring2.show_wifi()
#    led_ring2.display_percentage2(100)
#    led_ring2.display_percentage2(50)
    


if __name__ == "__main__":
    sys.exit(main())

