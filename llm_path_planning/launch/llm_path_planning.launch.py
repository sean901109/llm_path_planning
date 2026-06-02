import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Load configuration file
    config = os.path.join(
        get_package_share_directory('llm_path_planning'),
        'config',
        'params.yaml'
    )
    

    # Node definition
    node = Node(
        package='llm_path_planning',
        executable='llm_path_planning.py',
        output='screen',
        emulate_tty=True,
        parameters=[
            config
        ]
    )
    
    return LaunchDescription([
        node,
    ])
