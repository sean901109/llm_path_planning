import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    use_composition = LaunchConfiguration('use_composition', default='False')
    param_dir = LaunchConfiguration(
    'params_file',
    default=os.path.join(
        get_package_share_directory('navigation'),
        'config',
        'slam_navigation.yaml'))
        
    slam=IncludeLaunchDescription(
        launch_description_source=PythonLaunchDescriptionSource([
            get_package_share_directory('navigation'),
            '/launch/online_async_launch.py'
        ])
    )

    nav2_launch_file_dir = os.path.join(get_package_share_directory('nav2_bringup'), 'launch')


    return LaunchDescription([
    	slam,
    	DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'),
        
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([nav2_launch_file_dir, '/navigation_launch.py']),
            launch_arguments={
                'use_composition': use_composition,
                'params_file': param_dir}.items(),
        ),
    ])
