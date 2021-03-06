############################################################################
#    CoderBot, a didactical programmable robot.
#    Copyright (C) 2014, 2015 Roberto Previtera <info@coderbot.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
############################################################################

import os
import time
import logging

# GPIO
class GPIO_CODERBOT_V_4():
    # motors
    PIN_MOTOR_ENABLE = 22
    PIN_LEFT_FORWARD = 25
    PIN_LEFT_BACKWARD = 24
    PIN_RIGHT_FORWARD = 4
    PIN_RIGHT_BACKWARD = 17

    PIN_PUSHBUTTON = 11
    # servo
    PIN_SERVO_1 = 9
    PIN_SERVO_2 = 10
    # sonar
    PIN_SONAR_1_TRIGGER = 18
    PIN_SONAR_1_ECHO = 7
    PIN_SONAR_2_TRIGGER = 18
    PIN_SONAR_2_ECHO = 8
    PIN_SONAR_3_TRIGGER = 18
    PIN_SONAR_3_ECHO = 23
    PIN_SONAR_4_TRIGGER = 18
    PIN_SONAR_4_ECHO = None

    # encoder
    PIN_ENCODER_LEFT_A = 14
    PIN_ENCODER_LEFT_B = 6
    PIN_ENCODER_RIGHT_A = 15
    PIN_ENCODER_RIGHT_B = 12

class GPIO_CODERBOT_V_5():
    # motors
    PIN_MOTOR_ENABLE = None #22
    PIN_LEFT_FORWARD = 17 #25
    PIN_LEFT_BACKWARD = 18 # 24
    PIN_RIGHT_FORWARD = 22 # 4
    PIN_RIGHT_BACKWARD = 23 #17

    PIN_PUSHBUTTON = 16 #11
    # servo
    PIN_SERVO_1 = 19 #9
    PIN_SERVO_2 = 26 #10
    # sonar
    PIN_SONAR_1_TRIGGER = 5 #18
    PIN_SONAR_1_ECHO = 27 #7
    PIN_SONAR_2_TRIGGER = 5 #18
    PIN_SONAR_2_ECHO = 6 #8
    PIN_SONAR_3_TRIGGER = 5 #18
    PIN_SONAR_3_ECHO = 12 #23
    PIN_SONAR_4_TRIGGER = 5 #18
    PIN_SONAR_4_ECHO = 13 #23

    # encoder
    PIN_ENCODER_LEFT_A = 14
    PIN_ENCODER_LEFT_B = 15 #6
    PIN_ENCODER_RIGHT_A = 24 #15
    PIN_ENCODER_RIGHT_B = 25 #12

# PWM
PWM_FREQUENCY = 100 #Hz
PWM_RANGE = 100 #0-100

class CoderBot(object):

    # pylint: disable=too-many-instance-attributes

    def __init__(self, motor_trim_factor=1.0, encoder=True):
        try:
            self._mpu = mpu.AccelGyroMag()
            self.GPIOS = GPIO_CODERBOT_V_5()
            logging.info("MPU available")
        except:
            logging.info("MPU not available")
            self.GPIOS = GPIO_CODERBOT_V_4()

        self._pin_out = [self.GPIOS.PIN_LEFT_FORWARD, self.GPIOS.PIN_RIGHT_FORWARD, self.GPIOS.PIN_LEFT_BACKWARD, self.GPIOS.PIN_RIGHT_BACKWARD, self.GPIOS.PIN_SERVO_1, self.GPIOS.PIN_SERVO_2]
        self._cb = dict()
        self._cb_last_tick = dict()
        self._cb_elapse = dict()
        self._encoder = encoder
        self._motor_trim_factor = motor_trim_factor
        self.motor_control = self._dc_enc_motor

        #self.stop()
        self._is_moving = False

    the_bot = None

    def exit(self):
        pass

    @classmethod
    def get_instance(cls, motor_trim_factor=1.0, encoder=True, servo=False):
        if not cls.the_bot:
            cls.the_bot = CoderBot(motor_trim_factor=motor_trim_factor, encoder=encoder)
        return cls.the_bot

    def move(self, speed=100, elapse=0, distance=0):
        self._motor_trim_factor = 1.0
        speed_left = min(100, max(-100, speed * self._motor_trim_factor))
        speed_right = min(100, max(-100, speed / self._motor_trim_factor))
        self.motor_control(speed_left=speed_left, speed_right=speed_right, time_elapse=elapse, target_distance=distance)

    def turn(self, speed=100, elapse=0):
        speed_left = min(100, max(-100, speed * self._motor_trim_factor))
        speed_right = -min(100, max(-100, speed / self._motor_trim_factor))
        self.motor_control(speed_left=speed_left, speed_right=speed_right, time_elapse=elapse)

    def turn_angle(self, speed=100, angle=0):
        z = self._mpu.get_gyro()[2]
        self.turn(speed, elapse=0)
        while abs(z - self._mpu.get_gyro()[2]) < angle:
            time.sleep(0.05)
            logging.info(self._mpu.get_gyro()[2])
        self.stop()

    def forward(self, speed=100, elapse=0, distance=0):
        self.move(speed=speed, elapse=elapse, distance=distance)

    def backward(self, speed=100, elapse=0, distance=0):
        self.move(speed=-speed, elapse=elapse, distance=distance)

    def left(self, speed=100, elapse=0):
        self.turn(speed=-speed, elapse=elapse)

    def right(self, speed=100, elapse=0):
        self.turn(speed=speed, elapse=elapse)

    def servo(self, servo, angle):
        self._servo_control(self._servos[servo], angle)

    def get_sonar_distance(self, sonar_id=0):
        return self.sonar[sonar_id].get_distance()

    def get_mpu_accel(self, axis=None):
        acc = self._mpu.get_acc()
        if axis is None:
            return acc
        else:
            return int(acc[axis]*100.0)/100.0

    def get_mpu_gyro(self, axis=None):
        gyro = self._mpu.get_gyro()
        if axis is None:
            return gyro
        else:
            return int(gyro[axis]*100.0)/200.0

    def get_mpu_heading(self):
        hdg = self._mpu.get_hdg()
        return int(hdg)

    def get_mpu_temp(self):
        temp = self._mpu.get_temp()
        return int(temp*100.0)/100.0

    def _servo_control(self, pin, angle):
        duty = ((angle + 90) * 100 / 180) + 25

        self.pi.set_PWM_range(pin, 1000)
        self.pi.set_PWM_frequency(pin, 50)
        self.pi.set_PWM_dutycycle(pin, duty)

    def stop(self):
        if self._encoder:
            self._twin_motors_enc.stop()
        else:
            for pin in self._pin_out:
                self.pi.write(pin, 0)
        self._is_moving = False

    def is_moving(self):
        return self._is_moving

    # Distance travelled getter
    def distance(self):
        return self._twin_motors_enc.distance()

    # CoderBot velocity getter
    def speed(self):
        return self._twin_motors_enc.speed()

    # CoderBot direction getter
    def direction(self):
        return self._twin_motors_enc.speed()

    def set_callback(self, gpio, callback, elapse):
        self._cb_elapse[gpio] = elapse * 1000
        self._cb[gpio] = callback
        self._cb_last_tick[gpio] = 0

    def sleep(self, elapse):
        logging.debug("sleep: %s", str(elapse))
        time.sleep(elapse)

    def _cb_button(self, gpio, level, tick):
        cb = self._cb.get(gpio)
        if cb:
            elapse = self._cb_elapse.get(gpio)
            if level == 0:
                self._cb_last_tick[gpio] = tick
            elif tick - self._cb_last_tick[gpio] > elapse:
                self._cb_last_tick[gpio] = tick
                logging.info("pushed: %d, %d", level, tick)
                cb()

    def halt(self):
        os.system('sudo halt')

    def restart(self):
        os.system('sudo /etc/init.d/coderbot restart')

    def reboot(self):
        os.system('sudo reboot')

    def _dc_enc_motor(self, speed_left=100, speed_right=100, time_elapse=0, target_distance=0):
        self._twin_motors_enc.control(power_left=speed_left,
                                      power_right=speed_right,
                                      time_elapse=time_elapse,
                                      target_distance=target_distance)
