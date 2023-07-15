"""
Modified to accept speed/steer values sent by
webclient from joystick position.

MicroPython code for Pico car project using:
* Raspberry Pi Pico mounted on differential drive car
* 56:1 gear motors with encoders
* Asynchrounous webserver enabling remote control
* Odometer keeps track of pose (x, y, angle)
"""

import encoder_rp2 as encoder
import gc
import math
import network
import uasyncio as asyncio
import _thread
from machine import Pin, PWM
import time
from secrets import secrets
from odometer import Odometer
from parameters import (TICKS_PER_METER, TARGET_TICK_RATE,
                        TURN_SPD, ANGLE_TOL)

ssid = secrets['ssid']
password = secrets['wifi_password']

# Set drive_mode to one of: 'F', 'B', 'R', 'L', 'S'
drive_mode = 'S'  # stop
goal = None


html = """<!DOCTYPE html>
<html>
    <head> <title>Pico W</title> </head>
    <body> <h1>Pico W</h1>
        <p>%s</p>
    </body>
</html>
"""

# setup encoders
enc_b = encoder.Encoder(0, Pin(14))
enc_a = encoder.Encoder(1, Pin(12))

# setup onboard LED
led = Pin("LED", Pin.OUT, value=0)

# setup pins connected to L298N Motor Drive Controller Board
ena = PWM(Pin(21))
in1 = Pin(20, Pin.OUT, value=0)
in2 = Pin(19, Pin.OUT, value=0)
in3 = Pin(18, Pin.OUT, value=0)
in4 = Pin(17, Pin.OUT, value=0)
enb = PWM(Pin(16))

ena.freq(1_000)
enb.freq(1_000)

def set_mtr_dirs(a_mode, b_mode):
    """Set motor direction pins for both motors.
    options are: 'FWD', 'REV', 'OFF'."""

    if a_mode == 'FWD':
        in1.value(0)
        in2.value(1)
    elif a_mode == 'REV':
        in1.value(1)
        in2.value(0)
    else:  # Parked
        in1.value(0)
        in2.value(0)

    if b_mode == 'FWD':
        in3.value(0)
        in4.value(1)
    elif b_mode == 'REV':
        in3.value(1)
        in4.value(0)
    else:  # Parked
        in3.value(0)
        in4.value(0)

def set_mtr_spds(a_PWM_val, b_PWM_val):
    """set speeds for both a and b motors
    allowable values are u16 integers (< 65_536)"""
    a_val = int(a_PWM_val)
    if a_val > 65_530:
        a_val = 65_530
    b_val  = int(b_PWM_val)
    if b_val > 65_530:
        b_val = 65_530
    ena.duty_u16(a_val)
    enb.duty_u16(b_val)

def move_forward():
    set_mtr_dirs('FWD', 'FWD')

def move_backward():
    set_mtr_dirs('REV', 'REV')

def turn_left():
    set_mtr_dirs('REV', 'FWD')

def turn_right():
    set_mtr_dirs('FWD', 'REV')

def move_stop():
    set_mtr_dirs('OFF', 'OFF')
    set_mtr_spds(0, 0)

# Stop the robot NOW
move_stop()

def drive_motors(spd, str):
    """From input values for desired
    linear speed: spd (in range -1 to +1)
    angular speed: str (in range -1 to +1)
    Calculate motor speed and drive motors accordingly
    """
    
    # linear components
    a_lin_spd = int(TARGET_TICK_RATE * 11 * spd)
    b_lin_spd = int(TARGET_TICK_RATE * 11 * spd)
    
    # turning components
    a_ang_spd = int(TURN_SPD * str)
    b_ang_spd = int(TURN_SPD * str)
    
    # superimpose components
    a_spd = a_lin_spd - a_ang_spd
    b_spd = b_lin_spd + b_ang_spd
    
    # determine direction of each motor
    if a_spd > 0:
        a_dir = 'FWD'
    elif a_spd < 0:
        a_dir = 'REV'
    else:
        a_dir = 'OFF'

    if b_spd > 0:
        b_dir = 'FWD'
    elif b_spd < 0:
        b_dir = 'REV'
    else:
        b_dir = 'OFF'

    # set motor direction pins
    set_mtr_dirs(a_dir, b_dir)
    
    # set motor speeds
    set_mtr_spds(abs(a_spd), abs(b_spd))

wlan = network.WLAN(network.STA_IF)

def connect():
    wlan.active(True)
    wlan.config(pm = 0xa11140) # Disable power-save mode
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
        ip = status[0]
        print('ip = ' + status[0])
    return ip

async def serve_client(reader, writer):
    request_line = await reader.readline()
    while await reader.readline() != b"\r\n":
        pass

    req_parts = request_line.split()
    req_str = req_parts[1].decode('utf-8')[1:]
    # print(req_str)

    stateis = ""
    try:
        speed, steer = req_str.split('/')
        drive_motors(float(speed), float(steer))
        stateis = "OK"
    except Exception as e:
        stateis = str(e)

    response = html
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    # print("Client disconnected")

async def main():
    global drive_mode, goal
    print('Connecting to Network...')
    connect()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    start_time = time.ticks_ms()
    prev_time = time.ticks_ms()
    prev_mode = 'S'  # stop
    odom = Odometer()
    while True:

        # Flash LED
        led.toggle()

        # get latest encoder values
        enc_a_val = enc_a.value()
        enc_b_val = enc_b.value()

        # get current pose
        pose = odom.update(enc_a_val, enc_b_val)
        pose_x, pose_y, pose_angle = pose
        pose_ang_deg = pose_angle * 180 / math.pi
        pose_deg = (pose_x, pose_y, pose_ang_deg)  # for display


        await asyncio.sleep(0.1)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
