#!/usr/bin/env python3
# coding: utf-8

"""
Use PS3 joystick with Piborg Gamepad library (asynchronous mode)
to send speed & steering values to picobot webserver.
"""

import Gamepad
import time
import urllib.request

base_url = "http://192.168.1.64/%s/%s/%s/%s/%s/%s/%s"

# Gamepad settings
gamepadType = Gamepad.PS3
crs = 'CROSS'
cir = 'CIRCLE'
tri = 'TRIANGLE'
sqr = 'SQUARE'
ps3 = 'PS'
joystickSpeed = 'LEFT-Y'
joystickSteering = 'RIGHT-X'
pollInterval = 0.2

if __name__ == "__main__":

    # Wait for gamepad to be connected
    if not Gamepad.available():
        print('Please connect your gamepad...')
        while not Gamepad.available():
            time.sleep(1.0)
    gamepad = gamepadType()
    print('%s connected' % gamepad)

    # Set some initial states
    speed = 0.0
    steer = 0.0
    first = 0
    second = 0
    third = 0
    home = 0
    p3 = 0

    # Start the background updating
    gamepad.startBackgroundUpdates()

    while True:
        if gamepad.isConnected():
            # Check to see if any buttons pressed
            if gamepad.beenPressed(cir):
                first = 1
            else:
                first = 0

            if gamepad.beenPressed(tri):
                second = 1
            else:
                second = 0

            if gamepad.beenPressed(sqr):
                third = 1
            else:
                third = 0

            if gamepad.beenPressed(crs):
                home = 1
            else:
                home = 0

            if gamepad.beenPressed(ps3):
                p3 = 1
            else:
                p3 = 0

            # Check joystick coordinates
            speed = -gamepad.axis(joystickSpeed)
            steer = -gamepad.axis(joystickSteering)
            values = (speed, steer, first, second, third, home, p3)
            with urllib.request.urlopen(base_url % values) as response:
                html = response.read()

        time.sleep(pollInterval)

    gamepad.disconnect()
    print("node stopped")
