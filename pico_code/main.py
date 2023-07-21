"""
MicroPython code for Pico car project using:
* Raspberry Pi Pico mounted on differential drive car
* 56:1 gear motors with encoders
* Asynchrounous webserver enabling remote control
* Odometer keeps track of pose (x, y, angle)

Accept values (speed/steer/first/second/third/home)
from PS3 gamepad controller via http GET requests
"""

import gc
import math
import network
import uasyncio as asyncio
import _thread
from machine import Pin, PWM
import time
from secrets import secrets
from odometer import Odometer
from parameters import (TICKS_PER_METER, FULL_SPD,
                        LOW_SPD, APPROACH_DIST,
                        STOP_DIST, TURN_SPD, ANGLE_TOL)

ssid = secrets['ssid']
password = secrets['wifi_password']

html = """<!DOCTYPE html>
<html>
    <head> <title>Pico W</title> </head>
    <body> <h1>Pico W</h1>
        <p>%s</p>
    </body>
</html>
"""

# navigation parmeters
wp = (1, 0)
test_flag = False

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

# Instantiate odometer
odom = Odometer()

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

def move_stop():
    set_mtr_dirs('OFF', 'OFF')
    set_mtr_spds(0, 0)

# Stop the robot NOW
move_stop()

def reset_odometer():
    """Delete odom object and create new one at pose 0,0,0"""
    global odom
    del(odom)
    odom = Odometer()

def drive_motors(lin_spd, ang_spd):
    """
    Based on robot's desired motion in 2 DOF:
    linear speed: lin_spd (in range -1 to +1)
    angular speed: ang_spd (in range -1 to +1)
    Calculate both motor speeds and
    drive motors accordingly.
    """
    
    # linear components
    a_lin_spd = int(FULL_SPD * lin_spd)
    b_lin_spd = int(FULL_SPD * lin_spd)
    
    # turning components
    a_ang_spd = int(TURN_SPD * ang_spd)
    b_ang_spd = int(TURN_SPD * ang_spd)
    
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

def rel_polar_coords_to_pt(curr_pose, point):
    """Based on current pose, return relative
    polar coords dist (m), angle (rad) to goal point.
    """
    # current pose
    x0, y0, a0 = curr_pose

    # coords of goal point
    x1, y1 = point

    # Relative coords to goal point
    x = x1 - x0
    y = y1 - y0

    # Convert rectangular coords to polar
    r, theta = odom.r2p(x, y)

    # Relative angle to goal point
    rel_angle = theta - a0

    return (r, rel_angle)

def turn_to_angle(ang):
    """ Turn in place to angle (radians)."""
    pass

def drive_and_steer(spd, steer):
    """Drive forward at spd (range: -1 to +1) while making
    subtle steering corrections in proportion to
    relative angle to goal -> steer (radians).
    """
    # Guess at value of proportionality constant
    KS = 1.0  # units: 1/sec
    ang_spd = KS * steer
    
    # drive motors
    drive_motors(spd, ang_spd)
    

def do_buttons(buttons):
    """
    Callback for dispatching button-push events
    to desired action functions
    """
    global test_flag
    one, two, three, home = buttons
    if one:
        # print current pose (x, y, theta(degrees))
        pose_x, pose_y, pose_angle = odom.get_curr_pose()
        pose_ang_deg = pose_angle * 180 / math.pi
        pose_deg = (pose_x, pose_y, pose_ang_deg)
        print(pose_deg)
    
    if two:
        print("running test_drive()")
        test_flag = True
    
    if three:
        reset_odometer()

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
        speed, steer, b1, b2, b3, b4 = req_str.split('/')
        # following line is a vestige of earlier version
        # drive_motors(float(speed), float(steer))
        buttons = (int(b1), int(b2), int(b3), int(b4))
        if any(buttons):
            do_buttons(buttons)
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
    global test_flag
    print('Connecting to Network...')
    connect()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:

        # Flash LED
        led.toggle()

        # Update odometer
        pose = odom.update()

        # test drive if flag is set
        if test_flag:
            # Drive along a straight line to waypoint wp."""
            dist, rel_angle = rel_polar_coords_to_pt(pose, wp)
            # print(dist, rel_angle)
            # turn to aim at wp
            # turn_to_angle(rel_angle)
            
            # drive to wp
            spd = 1
            if dist > APPROACH_DIST:
                drive_and_steer(spd, rel_angle)
            else:
                move_stop()
                test_flag = False
                print(pose)

        await asyncio.sleep(0.1)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
