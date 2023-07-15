"""
Pico Asynchronous Webserver LED Control example at
https://gist.github.com/aallan/3d45a062f26bc425b22a17ec9c81e3b6
adapted to accept /X/Y coordinates from web client
"""

import network
import time
import secrets

from machine import Pin
import uasyncio as asyncio

led = Pin(15, Pin.OUT)
onboard = Pin("LED", Pin.OUT, value=0)

ssid = secrets.secrets['ssid']
password = secrets.secrets['wifi_password']

html = """<!DOCTYPE html>
<html>
    <head> <title>Pico W</title> </head>
    <body> <h1>Pico W</h1>
        <p>%s</p>
    </body>
</html>
"""

wlan = network.WLAN(network.STA_IF)

def connect_to_network():
    wlan.active(True)
    wlan.config(pm = 0xa11140)  # Disable power-save mode
    wlan.connect(ssid, password)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print('ip = ' + status[0])

async def serve_client(reader, writer):
    # print("Client connected")
    request_line = await reader.readline()
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    req_parts = request_line.split()
    req_str = req_parts[1].decode('utf-8')[1:]
    print(req_str)

    stateis = ""
    if req_str == 'light/on':
        print("turning led on")
        led.value(1)
        stateis = "LED is ON"
    
    elif  req_str == 'light/off':
        print("turning led off")
        led.value(0)
        stateis = "LED is OFF"

    else:
        try:
            x, y = req_str.split('/')
            # print("x = %s, y = %s" % (x, y))
            stateis = "OK"
        except Exception as e:
            stateis = str(e)

    response = html % stateis
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    # print("Client disconnected")

async def main():
    print('Connecting to Network...')
    connect_to_network()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:
        onboard.on()
        # print("heartbeat")
        await asyncio.sleep(0.25)
        onboard.off()
        await asyncio.sleep(5)
        
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
