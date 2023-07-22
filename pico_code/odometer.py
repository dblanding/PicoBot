import encoder_rp2 as encoder
from machine import Pin
import math
from parameters import TRACK_WIDTH, METERS_PER_TICK


class Odometer():
    """
    Calculate and return current pose based on incremental changes in
    encoder values (a & b)
    length dimensions are in meters
    angle dimensions are in radians (+) CCW from X axis.
    """

    def __init__(self):
        # Set up encoders
        self.enc_a = encoder.Encoder(1, Pin(12))
        self.enc_b = encoder.Encoder(0, Pin(14))
        
        # Set some initial values
        self.prev_enc_a_val = 0
        self.prev_enc_b_val = 0
        self.x = 0.0
        self.y = 0.0
        self.ang = 0.0
        

    def get_curr_pose(self):
        return (self.x, self.y, self.ang)

    def update(self):
        """
        Update current pose incrementally w/r/t previous pose
        using the latest encoder values.
        Return new pose coordinates (x, y, theta(radians))
        """

        # find change in encoder values
        curr_enc_a_val = self.enc_a.value()
        curr_enc_b_val = self.enc_b.value()
        delta_enc_a = curr_enc_a_val - self.prev_enc_a_val
        delta_enc_b = curr_enc_b_val - self.prev_enc_b_val
        self.prev_enc_a_val = curr_enc_a_val
        self.prev_enc_b_val = curr_enc_b_val

        # incremental distance traveled
        delta_dist_fwd = ((delta_enc_a + delta_enc_b) / 2) * METERS_PER_TICK

        # incremental angle change of car
        delta_ang = (delta_enc_b - delta_enc_a) * METERS_PER_TICK / TRACK_WIDTH

        # convert incremental motion from polar to rect coords
        delta_x, delta_y = self.p2r(delta_dist_fwd, self.ang)

        # update x, y coords of pose
        self.x += delta_x
        self.y += delta_y

        # update pose angle
        self.ang += delta_ang

        return (self.x, self.y, self.ang)

    # geometry helper functions
    def p2r(self, r, theta):
        """Convert polar coords to rectangular"""
        x = math.cos(theta) * r
        y = math.sin(theta) * r
        return (x, y)

    def r2p(self, x, y):
        """Convert rectangular coords to polar"""
        r = math.sqrt(x*x + y*y)
        theta = math.atan2(y, x)
        return (r, theta)
