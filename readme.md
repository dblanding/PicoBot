# PicoBot2: Taking PicoBot to the next level

* The PicoBot is now configured to listen for control instuctions on its asynchronous webserver
    * The instructions arrive as GET requests coming from `ps3_joypub.py` (running on my laptop)
    * This script uses the **PiBorg Gamepad** library to receive joystick position and button push events from a Sony PS3 Gamepad controller.
    * The data are encoded in the `path` part of the GET request like so:
        * `http://192.168.1.64/x/y/b1/b2/b3/...` where `x` and `y` are the joystick values and `bn` encode various button push events.
    * The pico bot interprets the x, y values as linear_spd, turning_spd and uses them to drive the picobot motors.

* Driving the PicoBot around, it seems to drive quite straight in both FWD & REV directions, and also does a pretty good job of turning in place. So there doesn't seem to be a need for the  PID(C) feedback to regulate motor speed (provided by the motors class)

![PS3 gamepad controller](imgs/sony_ps3.jpg)

## The buttons used:

Button | Name  | Function
-------|-------|---------
![CIRCLE](imgs/circle.jpg) | CIRCLE | Add current position to waypoint file
![TRIANGLE](imgs/triangle.jpg) | TRIANGLE | Read waypoint file -> list `waypoints`
![SQUARE](imgs/square.jpg) | SQUARE | Drive to waypoints sequentially
![CROSS](imgs/cross.jpg) | CROSS | Reset odometer: current pose = (x=0, y=0, theta=0)
![PS](imgs/ps.jpg) | PS | Erase waypoint file

## Operating the PicoBot

### Coordinate systems

* The starting pose (x, y location and orientation angle) of the PicoBot defines its *world coordinate system*.
    * Origin is at the centerline of the PicoBot, half way between the 2 wheels
    * Positive X axis is straight ahead
    * Y axis is along the common axis of the wheels, positive to the left
    * Orientation starts at theta=0 along the X axis, Turning left causes value of orientation to increase.
* The PicoBot has its own *local coordinate system* initially alilgned with the world coordinate system.
    * Once the PicoBot moves, its local coordinate system moves with it, wheras the world coordinate system stays put. By counting the pulses from its encoders, the PicoBot keeps track of its position in the world coorinate system.
    
### Joystick operation

* One option for driving the PicoBot is to use the joystick control.
    * The left joystick controls speed
    * The right joystick cocntrols turning

### Automatically drive to a series of waypoints.

* Another option is to save a series of waypoints in a file called `waypoints.txt`
    * Then, by first pressing the **TRIANGLE** button, the saved waypoints will be read into a list of waypoints.
    * Next, by pressing the **SQUARE** button, the PicoBot will drive to each waypoint in sequence, stopping on arrival at the final waypoint.
```
1, 0
1, 1
0, 1
0, 0
```
* Click on the image below to see a video of the PicoBot following the waypoints in the `waypoints.txt` file above. The waypoints are the corners of a square, 1 meter on each side.

![waypoint driving](https://github.com/dblanding/PicoBot/assets/53412304/bc06bb61-378a-43b9-a90a-03d8c30c323c)


### Entering the waypoints while driving under joystick control

* In the demo above, the waypoints were entered manually into the `waypoints.txt` file.
* It is also posible to enter the waypoints interactively while driving under joystick control.
    1. Start the PicoBot in its *Home* position.
    2. Press the **PS** button to *erase the contents of the `waypoints.txt` file.
    3. Use the joystick ccontrols to navigate to the first waypoint.
    4. Press the **CIRCLE** button to save the PicBot's currrent location as the first waypoint in the file.
    5. Repeat steps 3 & 4 to save all desired waypoints to the file.
        * The `waypoints.txt` file is now finished.
    6. Once the last waypoint has been saved, return the PicoBot to its *Home* position.
    7. Press the **CROSS** button to reset the odometer to (0, 0, 0).
    9. Press the **TRIANGLE** button to read the waypoint file into a list of waypoints.
    10. Press the **SQUARE** button, starting the PicoBot driving to each waypoint in sequence, stopping on arrival at the final waypoint.
