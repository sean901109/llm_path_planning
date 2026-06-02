#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from openai import OpenAI
from rclpy.qos import QoSProfile, ReliabilityPolicy
import os, time
from std_msgs.msg import String
import pandas as pd
from geometry_msgs.msg import PoseStamped
# from tf_transformations import quaternion_from_euler
import playsound
from pathlib import Path
from scipy.spatial.transform import Rotation
from nav_msgs.msg import Odometry
import threading 
import whisper
import sounddevice as sd
import os
import numpy as np
from action_msgs.msg import GoalStatusArray
class GoalPublisher(Node):
    def __init__(self):
        super().__init__('llm_path_planning')
        package_dir = os.path.dirname(os.path.dirname(__file__))
        prompt_path = os.path.join(package_dir, 'prompt', 'home_finding.txt')
        room_positions_path = os.path.join(package_dir, 'prompt', 'room_positions_sim.csv')
        self.task_prompt = self.read_prompt_from_file(prompt_path)
        df = pd.read_csv(room_positions_path)

        # 載入 Whisper 模型
        self.whisper_model = whisper.load_model("base")
        self.fs = 16000
        self.duration = 5  # 
        
        self.room_positions = {
            row["room name"]: (row["x"], row["y"], row["theta"])
            for _, row in df.iterrows()
        }
        # if self.task_prompt:
        #     print(f"Task prompt from file: {self.task_prompt}")
        # else:
        #     print("Failed to read task prompt from file.")

        # #===========================GPT===============================#
        self.client = OpenAI(api_key="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")
        
        # self.timer = self.create_timer(0.1, self.timer_callback)
        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 5)
        self.object_pub = self.create_publisher(String, '/target_object', 10)
        self.subscription = self.create_subscription(Odometry,'/odom',self.odom_callback,10)

        # Subscribe to action status
        self.status_sub = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
        )

        # Timer 定期聽語音
        self.triggered = False
        self.timer = self.create_timer(5.0, self.timer_callback)
        self.get_logger().info("GoalPublisher with Whisper started.")
        self.get_logger().info("Voice trigger node started. Listening for 'robot'...")

        self.room_x = self.room_y = 0.0
        self.object_name = None
        self.room_name = None
        self.sent_object_request = False
        
        self.check_arrive_timer = self.create_timer(0.1, self.check_arrival)

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
    
    def timer_callback(self):
        if self.triggered:
            return

        self.get_logger().info("Listening...")
        text = self.listen_and_transcribe()

        if text:
            self.get_logger().info(f"Recognized: {text}")
            if "robot" in text.lower():
                self.triggered = True
                self.respond_to_trigger()

    def listen_and_transcribe(self):
        audio = sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=1, dtype='float32')
        sd.wait()
        audio = np.squeeze(audio)
        result = self.whisper_model.transcribe(audio, fp16=False, language='en', task='transcribe')
        return result["text"].strip()

    def respond_to_trigger(self):
        response_text = "Hi, how can I help you?"

        speech_file_path = Path(__file__).parent / "speech.mp3"
        with self.client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=response_text,
            instructions="Speak with a helpful tone.",
        ) as response:
            response.stream_to_file(speech_file_path)

        playsound.playsound(str(speech_file_path))
        self.get_logger().info("Response spoken.")

        threading.Timer(1.0, self.ask_for_task).start()



    def ask_for_task(self):
        self.get_logger().info("Listening for task command...")
        user_text = self.listen_and_transcribe()
        print("test")

        if user_text:
            self.get_logger().info(f"User said: {user_text}")
            self.send_to_gpt(user_text)
        else:
            self.get_logger().warn("No task recognized.")

        self.triggered = False
        self.get_logger().info("Ready to listen for trigger word again.")

        
    
    def odom_callback(self, msg: Odometry):
        # 速度資訊
        self.linear = msg.twist.twist.linear
        pose = msg.pose.pose
        self.position_x = pose.position.x
        self.position_y = pose.position.y
        #angular = msg.twist.twist.angular

    def send_to_gpt(self, user_input):
        response = self.client.responses.create(
            model="o4-mini",
            instructions = self.task_prompt,
            input=user_input
        )
        response_text = response.output_text
        print("GPT:",response_text)
        self.room_name = None

        if '//' in response_text:
            extracted = response_text.split('//')[1].strip()
            parts = extracted.split(",", 2)  # Split into at most 3 parts
            self.room_name = parts[0].strip().lower()
            self.object_name = parts[1].strip()
            natural_response = parts[2].strip() if len(parts) > 2 else "I'll get that for you!"
        else:
            self.room_name = None
            self.object_name = None
            natural_response = response_text

        speech_file_path = Path(__file__).parent / "speech.mp3"
        with self.client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="nova",
            input=natural_response,
            instructions="You are a service robot. Speak in a cheerful and positive tone.",
        ) as response:
            response.stream_to_file(speech_file_path)

        playsound.playsound(str(speech_file_path))
        
        if self.room_name:
            if self.room_name in self.room_positions:
                self.room_x, self.room_y, theta = self.room_positions[self.room_name]
                self.publish_goal_pose(self.room_x, self.room_y, theta)
                print(f"Alright, I am going to the {self.room_name} to find what you're looking for.")
                self.sent_object_request = False
                
            else:
                print(f"Room '{self.room_name}' not found in the data.")
                print(f"Extracted location: {response_text}")
        else:
            print("No valid location found in GPT response.")
            print(f"Extracted location: {response_text}")

    def check_arrival(self):
        # self.get_logger().info(f"Check arrival timer triggered.")
        # print(f"room: {self.room_name}, object: {self.object_name}")
        # print(f"pos x: {self.position_x } , room x: {self.room_x }")
        # print(f"pos y: {self.position_y } , room y: {self.room_y }")
        if self.object_name and not self.sent_object_request:
                   
            if ( abs(self.position_x - self.room_x) < 0.5 ) and ( abs(self.position_y - self.room_y) < 0.5 ) and (self.status_str == "SUCCEEDED") :
            # if (self.status_str == "SUCCEEDED"):
                print(f"pos x: {self.position_x } , room x: {self.room_x }")
                print(f"pos y: {self.position_y } , room y: {self.room_y }") 
                msg = String()
                msg.data = self.object_name
                self.object_pub.publish(msg)

                print(f"[GoalPublisher] send YOLO-E：{msg}")
                self.sent_object_request = True
                # self.room_x = None
                # self.room_y = None
                # self.object_name = None # 確保物件名稱也被清除，直到新的指令


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



    def read_prompt_from_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return file.read().strip()  # Đọc và loại bỏ khoảng trắng thừa
        except Exception as e:
            self.get_logger().error(f"Error reading prompt from file: {e}")
            return None


def main(args=None):
    rclpy.init(args=args)
    node = GoalPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()