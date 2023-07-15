# PicoBot2: Taking picobot to the next level

* The Picobot is now configured to listen on its asynchronous webserver for GET requests
    * coming from `ps4_joypub.py` (running on my laptop)
        * which takes x, y position of a USB connected PS4 Joystick and packages the values into the get request as `http://192.168.1.64/x/y`
    * The pico bot interprets the x, y values as linear_spd, turning_spd and uses them to drive the picobot motors.

* Driving the picobot around, it seems to drive quite straight in both FWD & REV, and also does a pretty good job of turning in place. So there doesn't seem to be a need for the  PID(C) feedback to regulate motor speed (provided by the motrs class)

## Ideas about what to do next with Picobot

* Could use the joystick control to drive the PiocBot to various waypoints,
using a button at each WP to append the current pose onto a list of WPs.
* Another button could be used to terminate the list and store it
* The joystick could then be used to drive the PicoBot back to its *Home* pose.
* Another button could be used to *re-zero* its pose.
* Another button could be used to start the PicoBot along on a journey through
the chain of stored waypoints..
