
import network
import socket
from machine import Pin
import time
import _thread
import re


class Webserver:

    def __init__(self):
        print("Websocket init")
        self.websocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.websocket.bind(("", 80))
        self.websocket.listen(5)

        self.SOC = 0
        self.acoutw = 0 
        self.totalsolarw = 0
        self.mytime = 0

        time.sleep_ms(500)
        print("Websocket done")
        self.run_webserver = True
        _thread.start_new_thread(self.thread_webserver, (4, "webserver"))

    def set_variables(self, SOC, acoutw, totalsolarw, mytime):
        pass
        self.SOC = SOC
        self.acoutw = acoutw
        self.totalsolarw = totalsolarw
        self.mytime= mytime

    def thread_webserver(self, delay, name):
        print('Webserver gestartet.')
        while self.run_webserver == True:
            try:
                conn, addr = self.websocket.accept()
                print('Verbunden mit %s' % str(addr))
                print(f" SOC = {str(self.SOC)}  Watt {str(self.acoutw)} SolarWatt {str(self.totalsolarw)}")
                request = conn.recv(1024)

                request = str(request)
                #print('Anfrage: ', request)

                response = self.html_code()
                conn.send("HTTP/1.1 200 OK\n")
                conn.send("Content-Type: text/html\n")
                conn.send("Connection: close\n\n")
                conn.sendall(response)
                conn.close()
            except Exception as e:
                conn.send("HTTP/1.1 200 OK\n")
                conn.send("Content-Type: text/html\n")
                conn.send("Connection: close\n\n")
                response = "<h1>'Failed: </h1>" + str(e)
                conn.sendall(response)
                conn.close()

    def stop_webserver(self):
        self.run_webserver = False

    def html_code(self):
        html = '''
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta http-equiv="x-ua-compatible" content="ie=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">        
        <title>Solar reading</title>
        <!--<link rel="stylesheet" href="css/main.css" />
        <link rel="icon" href="images/favicon.png" />-->
    </head>
    <body>
        <h1>SolarData</h1>
        <div>
            <p> Time = '''+str(self.mytime)+''' </p>
            <p> SOC = '''+str(self.SOC)+''' </p>
            <p> Watt '''+str(self.acoutw)+'''  </p>
            <p> SolarWatt '''+str(self.totalsolarw)+''' </p>
        </div>

        <!--<p><a href="/?LED=ON"><button>Einschalten</button></a></p>
        <p><a href="/?LED=OFF"><button>Ausschalten</button></a></p>-->
    </body>
</html>

'''
        return html

