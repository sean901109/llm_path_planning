import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, EmitEvent, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PythonExpression

MY_ROBOT = os.environ.get('ROBOT', "scout_mini")
ENV = "small_house"
MY_ENVIRONMENT = os.environ.get('ENV', ENV)


def generate_launch_description():
  xacro_path = os.path.join(get_package_share_directory('scout_simulation'), 'robots/'+MY_ROBOT+'/', 'scout_mini.urdf.xacro')
  rviz_config_file = os.path.join(get_package_share_directory('scout_simulation'),'rviz','scout_simulation.rviz')

  world = os.path.join(get_package_share_directory('scout_simulation'), 'worlds', MY_ENVIRONMENT + '.world')

  declare_gpu_cmd = DeclareLaunchArgument(
    'gpu',
    default_value='False',
    description='Whether to use Gazebo gpu_ray or ray')
  declare_organize_cloud_cmd = DeclareLaunchArgument(
    'organize_cloud',
    default_value='False',
    description='Organize PointCloud2 into 2D array with NaN placeholders, otherwise 1D array and leave out invlaid points')
  gpu = LaunchConfiguration('gpu')
  organize_cloud = LaunchConfiguration('organize_cloud')
  robot_description = Command(['xacro',' ', xacro_path, ' gpu:=', gpu, ' organize_cloud:=', organize_cloud])

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


  spawn_example_cmd = Node(
    package='gazebo_ros', 
    executable='spawn_entity.py',
    arguments=[
      '-entity', MY_ROBOT,
      '-topic', 'robot_description',
      "-x", "6.0", "-y", "-1.0", "-z", "0.11","-R","0.0","-P","0.0","-Y","0.0"
    ],
    output='screen',
  )


  start_rviz_cmd = Node(
    package='rviz2',
    executable='rviz2',
    arguments=['-d', rviz_config_file],
    output='screen'
  )

  exit_event_handler = RegisterEventHandler(
    event_handler=OnProcessExit(
      target_action=start_rviz_cmd,
      on_exit=EmitEvent(event=Shutdown(reason='rviz exited'))
    )
  )

  declare_gui_cmd = DeclareLaunchArgument(
    'gui',
    default_value='True',
    description='Whether to launch the Gazebo GUI or not (headless)')
  gui = LaunchConfiguration('gui')
  start_gazebo = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(os.path.join(
      get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')),
    launch_arguments={'world' : world, 'gui' : gui}.items()
  )

  ld = LaunchDescription()

  # Add the actions
  ld.add_action(declare_gpu_cmd)
  ld.add_action(declare_organize_cloud_cmd)
  ld.add_action(declare_gui_cmd)
  ld.add_action(start_gazebo)
  ld.add_action(start_robot_state_publisher_cmd)
  ld.add_action(spawn_example_cmd)
  ld.add_action(start_rviz_cmd)
  ld.add_action(exit_event_handler)


  return ld
