"""
MicroPython code for Pico car project using:
* Raspberry Pi Pico mounted on differential drive car
* 56:1 gear motors with encoders
* Asynchrounous webserver accepts GET requests with
  format: http://base_URL/speed/steer/<buttons>/...
  encoding joystick and button presses of PS3 gamepad controller
* Odometer keeps track of pose (x, y, angle)
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

# navigation parameters
wp_flag = 0
wp_file = "waypoints.txt"
waypoints = []
joy_active = False
joy_vals = (0, 0)
KS = 5  # steering proportionality constant (units: 1/sec)

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

    # ensure angle is between -pi/2 and +pi/2
    if rel_angle < -math.pi:
        rel_angle += 2 * math.pi
    elif rel_angle > math.pi:
        rel_angle -= 2 * math.pi

    return (r, rel_angle)

def drive_and_steer(spd, steer):
    """Drive forward at spd (range: -1 to +1) while making
    subtle steering corrections in proportion to steer (rad),
    relative angle to goal.
    """
    ang_spd = KS * steer
    
    # drive motors
    drive_motors(spd, ang_spd)
    
def do_buttons(buttons):
    """
    Callback for dispatching button-push events
    to desired actions
    """
    global wp_flag, waypoints
    one, two, three, home, p3 = buttons
    if one:
        # save current position to waypoints file
        x, y, angle = odom.get_curr_pose()
        line = "%f, %f\n" % (x, y)
        with open(wp_file, "a") as f:
            f.write(line)
    
    if two:
        # read wp_file
        print("Reading wp_file")
        with open(wp_file) as f:
            lines = f.readlines()
            for line in lines:
                str_x, str_y = line.split(',')
                wp = float(str_x), float(str_y)
                waypoints.append(wp)
        
    if three:
        # drive waypoints
        wp_flag = 1
    
    if home:
        # reset odometer to pose (0, 0, 0)
        reset_odometer()
    
    if p3:
        # erase wp_file
        print("Erasing wp_file")
        with open(wp_file, "w") as f:
            f.write('')

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
    global joy_vals, joy_active
    request_line = await reader.readline()
    while await reader.readline() != b"\r\n":
        pass

    req_parts = request_line.split()
    req_str = req_parts[1].decode('utf-8')[1:]
    # print(req_str)

    stateis = ""
    try:
        speed, steer, b1, b2, b3, b4, p3 = req_str.split('/')
        joy_vals = (float(speed), float(steer))
        if any(joy_vals):
            joy_active = True
        buttons = (int(b1), int(b2), int(b3), int(b4), int(p3))
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
    global joy_active, wp_flag
    print('Connecting to Network...')
    connect()

    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:

        # Flash LED
        led.toggle()

        # Update odometer
        pose = odom.update()

        # drive with joystick
        if joy_active:
            if any(joy_vals):
                count = 5
                drive_motors(*joy_vals)
            elif count:  # keep doing this a few more cycles
                count -= 1
                drive_motors(*joy_vals)
                joy_active = False

        # drive sequentially to waypoints
        if wp_flag:
            if wp_flag == 1:
                # get next wp
                if len(waypoints):
                    wp = waypoints.pop(0)
                    wp_flag = 2  # turn toward wp
                else:
                    wp_flag = 0  # finished

            elif wp_flag == 2:  # turn to aim at wp
                dist, rel_angle = rel_polar_coords_to_pt(pose, wp)
                if rel_angle > ANGLE_TOL:
                    # turn CCW
                    drive_motors(0, 1)
                elif rel_angle < -ANGLE_TOL:
                    # turn CW
                    drive_motors(0, -1)
                else:
                    move_stop()
                    wp_flag = 3  # drive to wp
                    print(pose)
            
            elif wp_flag == 3:
                # Drive along a straight line to waypoint"""
                dist, rel_angle = rel_polar_coords_to_pt(pose, wp)
                spd = 1
                if dist > APPROACH_DIST:
                    drive_and_steer(spd, rel_angle)
                else:
                    move_stop()
                    wp_flag = 1  # get next wp
                    print(pose)

        await asyncio.sleep(0.1)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
