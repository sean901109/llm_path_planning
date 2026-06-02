
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from openai import OpenAI
from rclpy.qos import QoSProfile, ReliabilityPolicy
import os
from std_msgs.msg import String
from sensor_msgs.msg import Image, CameraInfo
from nav_msgs.msg import Odometry
import pandas as pd
from geometry_msgs.msg import PoseStamped
# from tf_transformations import quaternion_from_euler
import playsound
from pathlib import Path
from scipy.spatial.transform import Rotation
from ultralytics import YOLOE
import cv2
from PIL import Image as PILImage
import numpy as np
import time
import random
from cv_bridge import CvBridge
import math
from action_msgs.msg import GoalStatusArray


class YoloENode(Node):
    def __init__(self):
        super().__init__('yolo_e_node')

        self.bridge = CvBridge()
        self.model = YOLOE("yoloe-11l-seg.pt")
        self.depth_image = None
        self.rgb_image = None
        self.fx = self.fy = self.cx = self.cy = None

        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 5)

        # self.sub = self.create_subscription(String, '/target_object', self.target_callback, 10)
        # self.target_callback # for test
        # self.image_sub = self.create_subscription(Image, '/camera/image_raw', self.target_callback, 10)

        self.create_subscription(Image, '/camera/image_raw', self.rgb_callback, 10)
        self.create_subscription(Image, '/camera/depth/image_raw', self.depth_callback, 10)
        self.create_subscription(CameraInfo, '/camera/depth/camera_info', self.info_callback, 1)
        self.create_subscription(String, '/target_object', self.target_callback, 10)
        # self.create_subscription(Image, '/camera/image_raw', self.target_callback, 10)
        self.subscription = self.create_subscription(Odometry,'/odom',self.odom_callback,10)

        # Subscribe to action status
        self.status_sub = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
        )

        self.get_logger().info("YOLO-E Node started")


    
    def status_callback(self, msg):
        status_map = {
            0: "UNKNOWN",
            1: "ACCEPTED",
            2: "EXECUTING",
            3: "CANCELING",
            4: "SUCCEEDED",
            5: "CANCELED",
            6: "ABORTED"
        }

        for status in msg.status_list:
            self.status_str = status_map.get(status.status, "INVALID")

            # ---- NEW: extract UUID from goal_info ----
            uuid_bytes = status.goal_info.goal_id.uuid  # list of 16 uint8
            uuid_str = ''.join(f'{b:02x}' for b in uuid_bytes)

            # self.get_logger().info(
            #     f'📋 Goal Status: {self.status_str} (ID: {uuid_str})'
            # )


    def rgb_callback(self, msg):
        try:
            self.rgb_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"Failed to convert image: {e}")

        if self.rgb_image is None:
            self.get_logger().warn("No image received yet.")
            return
        
        self.pil_image = PILImage.fromarray(cv2.cvtColor(self.rgb_image, cv2.COLOR_BGR2RGB))

    def depth_callback(self, msg):
        self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')

    def info_callback(self, msg):
        self.fx = msg.k[0]
        self.fy = msg.k[4]
        self.cx = msg.k[2]
        self.cy = msg.k[5]
        # self.get_logger().info(f"Got camera intrinsics: fx={self.fx}, fy={self.fy}, cx={self.cx}, cy={self.cy}")
        self.destroy_subscription(self.info_callback)  # 拿一次就夠了  
    
    def odom_callback(self, msg: Odometry):
        pose = msg.pose.pose

        self.X1 = pose.position.x
        self.Y1 = pose.position.y
        self.angular = msg.twist.twist.angular
        qx = pose.orientation.x
        qy = pose.orientation.y
        qz = pose.orientation.z
        qw = pose.orientation.w

        # Convert quaternion to yaw (theta)
        rotation = Rotation.from_quat([qx, qy, qz, qw])
        self.theta_rad = rotation.as_euler('zyx')[0]  # yaw in radians
        self.Theta = math.degrees(self.theta_rad)

    def target_callback(self, msg):
        object_name = msg.data
        # object_name = "chair"
        
        self.get_logger().info(f"got the target name：{object_name}, start object dection ")

        if self.rgb_image is None or self.depth_image is None or self.fx is None:  # check info & image
            self.get_logger().warn("Missing image or intrinsics")
            return        

# object detection
        self.model.set_classes([object_name], self.model.get_text_pe([object_name])) # set object name as prompt to detect    
        results = self.model.predict(self.pil_image)
        turn_theta = self.Theta
        turn_theta = np.radians(turn_theta)

        for i in range(1,13):
            if (len(results[0].boxes) == 0) and (self.status_str == "SUCCEEDED"):
                self.get_logger().warn(f"no {object_name} was found")
                # action
                print(f"{i}: turn 30 degree")
                turn_theta += (np.pi)/6
                self.publish_goal_pose(self.X1, self.Y1, turn_theta)
                print(f"theta: {turn_theta}")
                time.sleep(3)
                results = self.model.predict(self.pil_image)
            else:
                print(f"I find {object_name}")    
                

            # return
        if (len(results[0].boxes) == 0):
            self.get_logger().warn(f"there are no {object_name} here")
        else :   
    # get object pixel(u,v)
            print(f"I'm at {self.X1},{self.Y1},{turn_theta} now")
            box = results[0].boxes[0].xyxy[0].tolist()
            x1, y1, x2, y2 = box
            u = int((x1 + x2) / 2)
            v = int((y1 + y2) / 2)    

            self.error =  (u - 320)/320
            for i in range(1,4):
                if (self.error >= 0):
                    self.theta_rad -= self.error*((np.pi)/12)
                    self.publish_goal_pose(self.X1, self.Y1, self.theta_rad)
                    print(f"theta: {self.theta_rad}")
                    time.sleep(3)
                else:
                    self.theta_rad += self.error*((np.pi)/12)
                    self.publish_goal_pose(self.X1, self.Y1, self.theta_rad)
                    print(f"theta: {self.theta_rad}")
                    time.sleep(3)
            print(f"u: {u}, v: {v}")
            

    # get depth info        
            Z = float(self.depth_image[v, u])
            if np.isnan(Z) or Z <= 0.0:
                self.get_logger().warn("Invalid depth at target")
                return
            
    # transfer to real_world coordinate        
            x = (u - self.cx) * Z / self.fx
            y = (v - self.cy) * Z / self.fy

            self.theta = np.radians(self.Theta) # Theta is to be defined (set as room position theta)
            X = self.X1 + Z * np.cos(self.theta) + x * np.sin(self.theta) # X1 is room position of X
            Y = self.Y1 + Z * np.sin(self.theta) + x * np.cos(self.theta) # Y1 is room position of Y
            print(f"I'm going to {X},{Y},{self.theta} now")
            print(f"Y1: {self.Y1}, Z: {Z}, x: {x} ")
            self.publish_goal_pose(X, Y, self.theta)

    def publish_goal_pose(self, x, y, theta):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()

        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        quaternion = Rotation.from_euler('z', theta).as_quat()
        qx, qy, qz, qw = quaternion  # Note: SciPy returns [x, y, z, w]

        # qx, qy, qz, qw = quaternion_from_euler(0.0, 0.0, theta)
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        self.goal_pub.publish(pose)

def main(args=None):
    rclpy.init(args=args)
    node = YoloENode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()