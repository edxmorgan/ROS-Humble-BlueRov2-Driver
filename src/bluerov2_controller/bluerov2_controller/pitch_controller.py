#!/usr/bin/env python3
import rclpy
import numpy as np
from rclpy.node import Node

from bluerov2_interfaces.msg import Attitude
from bluerov2_interfaces.msg import SetPitch

from std_msgs.msg import UInt16, Float64

class Controller(Node):

    def __init__(self):
        super().__init__("pitch_controller")

        # Setup default parameters
        self.declare_parameter("pitch_desired", 0) 
        self.declare_parameter("pwm_max", 1900)
        self.declare_parameter("pwm_neutral", 1500)            
        self.declare_parameter("kp", 600)    #35
        self.declare_parameter("kd", 50)    #25  
        self.declare_parameter("enable", True)  

        self.attitude           = [0, 0, 0, 0, 0, 0]                            # [ROLL, PITCH, YAW, ROLLSPEED, PITCHSPEED, YAWSPEED]
        self.pwm_max            = self.get_parameter("pwm_max").value           # Maximum PWM value
        self.pwm_neutral        = self.get_parameter("pwm_neutral").value       # Neutral PWM value
        self.pitch_desired      = self.get_parameter("pitch_desired").value     # Desired pitch setpoint
        self.KP                 = self.get_parameter("kp").value                # Proportional gain constant        
        self.KD                 = self.get_parameter("kd").value                # Derivative gain constant
        
        self.enable             = self.get_parameter("enable").value   

        # Create subscriber
        self.attitude_sub       = self.create_subscription(Attitude, "/bluerov2/attitude", self.callback_att, 10) 
        self.setPitch_sub       = self.create_subscription(SetPitch, "/settings/pitch/set_pitch", self.callback_set_pitch, 10)
        self.setTarget_sub      = self.create_subscription(Float64, "/settings/pitch/set_target", self.callback_set_target, 10) 

        # Create publisher
        self.pitch_pub           = self.create_publisher(UInt16, "/bluerov2/rc/pitch", 10)

        # Start update loop
        self.create_timer(0.04, self.calculate_pwm)    

    def callback_att(self, msg):       
        self.attitude = [msg.roll,
                         msg.pitch,
                         msg.yaw,
                         msg.rollspeed,
                         msg.pitchspeed,
                         msg.yawspeed]

    def callback_set_pitch(self, msg):       
        if msg.pwm_max < 1500:
            self.pwm_max = 1500
        else:
            self.pwm_max = msg.pwm_max
        self.KP = msg.kp 
        self.KD = msg.kd

        self.enable = msg.enable_pitch_ctrl           

    def callback_set_target(self, msg):       
        self.pitch_desired = self.deg2rad(msg.data)

    def deg2rad(self,deg):       
        if deg in range(0,181):
            return (deg * np.pi) / 180 
        if deg in range(181,361):
            return ((deg - 360) * np.pi) / 180

    def control(self, pitch, pitchspeed):        
        return self.KP*self.sawtooth(pitch-self.pitch_desired) + self.KD*pitchspeed
    
    def saturation(self, pwm):        
        pwm_min = self.pwm_neutral - (self.pwm_max - self.pwm_neutral)
        if pwm > self.pwm_max :
            pwm = self.pwm_max
        if pwm < pwm_min:
            pwm = pwm_min
        return int(pwm)
    
    def sawtooth (self, x):
        """Deal with 2*PI modulo
        
        Input:
        ------
        x: rad 
        """
        return (x+np.pi)%(2*np.pi)-np.pi      
    
    def calculate_pwm(self): 
        msg = UInt16()

        if self.enable:
            pitch = self.attitude[1]
            pitchspeed = self.attitude[4]
            u = self.control(pitch, pitchspeed)
            pwm = self.pwm_neutral - u
            pwm = self.saturation(pwm)
            
            msg.data = pwm
        else:
            msg.data = self.pwm_neutral

        msg.data = 1750
        self.pitch_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)    
    node = Controller()
    rclpy.spin(node)        
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()