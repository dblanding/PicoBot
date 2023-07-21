# car geometry
TRACK_WIDTH = 0.1778  # meters (7 inches)
WHEEL_CIRC = 0.214  # meters

# encoder / gearbox
TICKS_PER_REV = 2464
METERS_PER_TICK = WHEEL_CIRC / TICKS_PER_REV
TICKS_PER_METER = TICKS_PER_REV / WHEEL_CIRC

# motor PWM values when driving straight
FULL_SPD = 50_000
LOW_SPD  = 30_000

# motor PWM value turning in place
TURN_SPD = 20_000

# distance zones for detrmining proximity to goal
APPROACH_DIST = 0.15  # meters (6 inches)
STOP_DIST = 0.025  # meters (1 inch)

# half width of "good enough" zone when turning to angle
ANGLE_TOL = 0.035  # radians (2 degrees)
