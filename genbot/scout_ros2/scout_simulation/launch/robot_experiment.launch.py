import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command

# Retrieve robot type from environment variable or use default
MY_ROBOT = os.environ.get('ROBOT', "scout_mini")

def generate_launch_description():
    # Paths to the xacro file and RViz configuration
    xacro_path = os.path.join(
        get_package_share_directory('scout_simulation'),
        'robots',
        MY_ROBOT,
        'scout_mini_real.urdf.xacro'
    )
    
    rviz_config_file = os.path.join(
        get_package_share_directory('scout_simulation'),
        'rviz',
        'scout_real.rviz'
    )
    
    # Robot description using xacro
    robot_description = Command(['xacro ', xacro_path])  # Fixed closing parenthesis

    # Robot State Publisher Node
    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'robot_description': robot_description
        }]
    )

    # RViz Node
    start_rviz_cmd = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    # Launch Description
    ld = LaunchDescription()

    # Add nodes to the LaunchDescription
    ld.add_action(start_robot_state_publisher_cmd)
    ld.add_action(start_rviz_cmd)

    return ld

