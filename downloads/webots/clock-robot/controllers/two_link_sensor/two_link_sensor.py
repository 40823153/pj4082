# two_link.py
#
# Sample Webots controller file for driving the two-link arm
# with two driven joints.  This example uses the end sensor
# to search for objects in the vicinity.

# No copyright, 2020, Garth Zeglin.  This file is
# explicitly placed in the public domain.

print("two_link_sensor.py waking up.")

# Import the Webots simulator API.
from controller import Robot

# Import the standard Python math library.
import math

# Define the time step in milliseconds between controller updates.
EVENT_LOOP_DT = 200

# Request a proxy object representing the robot to control.
robot = Robot()
robot_name = robot.getName()
print("%s: controller connected." % (robot_name))

# Fetch handle for the 'base' and 'elbow' joint motors.
motor1 = robot.getMotor('motor1')
motor2 = robot.getMotor('motor2')

# Adjust the low-level controller gains.
print("%s: setting PID gains." % (robot_name))
motor1.setControlPID(2.0, 0.0, 0.1)
motor2.setControlPID(2.0, 0.0, 0.1)

# Fetch handles for the joint sensors.
joint1 = robot.getPositionSensor('joint1')
joint2 = robot.getPositionSensor('joint2')

# Specify the sampling rate for the joint sensors.
joint1.enable(EVENT_LOOP_DT)
joint2.enable(EVENT_LOOP_DT)

# Connect to the end sensor.
sensor = robot.getDistanceSensor("endRangeSensor")
sensor.enable(EVENT_LOOP_DT) # set sampling period in milliseconds

# The controller two modes: hunting versus tracking, governed by this flag.
tracking = False
tracking_start = None

# Keep track of recent sensor values to estimate the local gradient.
last_distance = None
last_j2_angle = None
last_j2_vel   = 0.0

# Run loop to execute a periodic script until the simulation quits.
# If the controller returns -1, the simulator is quitting.
while robot.step(EVENT_LOOP_DT) != -1:
    # Read simulator clock time.
    t = robot.getTime()

    # If hunting, then watch for a range signal.
    if tracking is False:
        motor1.setPosition(math.inf)  # rotate shoulder at constant rate
        motor1.setVelocity(0.5)       # radians/sec
        motor2.setPosition(math.pi/2) # move elbow to bent position

        # read the sensor
        distance = sensor.getValue()
        if distance < 0.9:
            print("%s: range sensor triggered: %f" % (robot_name, distance))
            tracking = True
            last_distance = distance
            last_j2_angle = joint2.getValue()
            tracking_start = t
            j2_vel = 0.25

    else:
        # If tracking, try to keep j2 pointed at the target.  This assumes a
        # convex shape in which the tracking distance is minimized when aligned.
        # This uses a crude local estimator of the gradient and a switching
        # function to hunt around it.
        motor1.setVelocity(0.0)

        # if too much time passes, quit tracking
        if (t - tracking_start) > 4.0:
            print("%s: tracking timeout, resuming hunt." % (robot_name))
            tracking = False

        else:
            # read the distance sensor
            distance = sensor.getValue()
            if distance > 0.89:
                print("%s: range sensor at maximum: %f, resuming hunt." % (robot_name, distance))
                tracking = False

            else:
                # read the elbow joint sensor
                j2_angle = joint2.getValue()

                # estimate the local gradient
                delta_distance = distance - last_distance
                delta_j2       = j2_angle - last_j2_angle
                last_distance  = distance
                last_j2_angle  = j2_angle

                if abs(delta_j2) < 0.002 or abs(delta_distance) < 0.002:
                    # If either the sensor isn't moving or the range distance
                    # isn't changing, just keep moving at the same rate.
                    pass

                else:
                    # If the signals have enough magnitude to meaningfully
                    # estimate the gradient of the range function, apply a
                    # switching function to hunt around the minimum distance.
                    # dx_dtheta is the derivative of the range with respect to
                    # the elbow angle, and should always have the opposite sign
                    # from the joint velocity to ensure motion toward the
                    # minimum.
                    dx_dtheta = delta_distance / delta_j2
                    if dx_dtheta > 0.0:
                        if last_j2_vel > 0.0: print("%s: changing direction at range sensor: %f range delta: %f" % (robot_name, distance, delta_distance))
                        j2_vel = -0.25
                    else:
                        if last_j2_vel < 0.0: print("%s: changing direction at range sensor: %f range delta: %f" % (robot_name, distance, delta_distance))
                        j2_vel = 0.25

                # issue motor command
                motor2.setPosition(math.inf)
                motor2.setVelocity(j2_vel)
                last_j2_vel = j2_vel
