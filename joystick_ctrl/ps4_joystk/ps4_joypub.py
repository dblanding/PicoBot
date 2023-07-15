#!/usr/bin/env python3
# coding: utf-8

"""
Use PS4 joystick
with Piborg Gamepad library (asynchronous mode)
to send speed & steering values to picobot webserver
"""

import Gamepad
import time
import urllib.request

base_url = "http://192.168.1.64/%s/%s"

# Gamepad settings
gamepadType = Gamepad.PS4
joystickSpeed = 'RIGHT-Y'
joystickSteering = 'RIGHT-X'

if __name__ == "__main__":

    # Wait for gamepad to be connected
    if not Gamepad.available():
        print('Please connect your gamepad...')
        while not Gamepad.available():
            time.sleep(1.0)
    gamepad = gamepadType()
    print('%s connected' % gamepad)

    # Set some initial state
    speed = 0.0
    steer = 0.0

    # Start the background updating
    gamepad.startBackgroundUpdates()

    while True:
        if gamepad.isConnected():
            speed = -gamepad.axis(joystickSpeed)
            steer = -gamepad.axis(joystickSteering)
            with urllib.request.urlopen(base_url % (speed, steer)) as response:
                html = response.read()
        time.sleep(0.2)

    gamepad.disconnect()
    print("node stopped")
