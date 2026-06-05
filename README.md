# LLM-PP: Large Langue Model for Path Planning

These packages were developed by [Thanh](https://sites.google.com/view/vuthanhcdt/home) from the [Networked Robotic Systems Laboratory](https://sites.google.com/site/yenchenliuncku). If you use any packages from this repository, please cite this repository and our team.

---

## Overview

This project is built on the Agilex Scout Mini Omni platform. The directory structure is as follows:
```bash
llm_planning/
├── genbot                          // Original packages
│   ├──  scout_ros2                 // Genbot-specific ROS2 packages
|   |   ├── scout_base              // Core functions for Genbot
|   |   ├── scout_msgs              // Message definitions for Genbot
|   |   ├── scout_simulation        // Simulation environment for Genbot
|   |   ├── ugv_sdk                 // Data transmission protocol for Genbot
|   |   ├── velodyne_simulator      // Velodyne sensor simulation
|   ├──velodyne                     // Velodyne-related packages
├── llm_path_planning               // llm path planning 
├── navgiation                      // navigation packages
├── README.md

```

## Install Dependent ROS Packages

The project has been thoroughly tested on **Ubuntu 22.04** with **ROS Humble**. It is strongly recommended to use the same configuration for optimal compatibility. Install the required ROS packages by running the following command:

```bash
sudo apt-get install ros-humble-joy ros-humble-teleop-twist-joy \
  ros-humble-teleop-twist-keyboard ros-humble-laser-proc \
  ros-humble-urdf ros-humble-xacro \
  ros-humble-compressed-image-transport ros-humble-rqt\
  ros-humble-interactive-markers \
  ros-humble-slam-toolbox\
  ros-humble-rqt ros-humble-rqt-common-plugins\
  ros-humble-gazebo-ros\
  ros-humble-sophus\
  ros-humble-robot-localization\
  ros-humble-realsense2-camera\
  ros-humble-realsense2-description\
  build-essential git cmake libasio-dev\
  ros-humble-tf2-geometry-msgs\
  ros-humble-eigen-stl-containers\
  ros-humble-ament-cmake-clang-format\
  ros-humble-nmea-msgs\
  ros-humble-mavros\
  ros-humble-navigation2\
  ros-humble-nav2-bringup\
  ros-humble-gazebo-ros-pkgs\
  ros-humble-bondcpp\
  ros-humble-ompl\
  ros-humble-turtlebot3-gazebo\
  ros-humble-pcl-ros\
  ros-humble-sensor-msgs-py\
  ros-humble-tf2-tools\
  ros-humble-robot-state-publisher\
  gazebo\
  ros-humble-velodyne-simulator\
  ros-humble-gazebo-ros-pkgs\
  ros-humble-ros-core\
  ros-humble-geometry2\
  ros-humble-tf2-sensor-msgs\
  ros-humble-spatio-temporal-voxel-layer\
  ros-humble-tf-transformations\
  libompl-dev\
  xterm
```

## Install Genbot Packages

Run the following commands to set up the workspace and install the required packages:
```bash
mkdir -p ~/llm_planning_ws/src
cd ~/llm_planning_ws/src/
git clone https://github.com/sean901109/llm_path_planning.git
cd ~/llm_ws/src/llm_path_planning/genbot/scout_ros2
git clone git@github.com:vuthanhcdt/velodyne_gazebo_plugins.git # only for host computer
cd ~/llm_planning_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
echo "source ~/llm_planning_ws/install/setup.bash" >> ~/.bashrc
```

## Simulation with Gazebo

```bash
ros2 launch scout_simulation small_house.launch.py #Launch Simulation Environment
ros2 launch velodyne_laserscan velodyne_laserscan_node-launch.py #Convert Velodyne PointCloud to LaserScan
ros2 launch navigation slam_navigation.launch.py  #SLAM Navigation (Mapping)
ros2 launch navigation localization_navigation.launch.py  # Localization Navigation (Using Existing Map)
cd ~/llm_path_planning/llm_path_planning/scripts
python3 yoloe.py
python3 llm_path_planning.py
```

## Experiment

```bash
ros2 launch bunker_simulation robot_experiment.launch.py #Launch RViz 
ros2 launch bunker_base bunker_base.launch.py publish_tf:=false #Bring Up Robot Base
ros2 launch velodyne velodyne-all-nodes-VLP16-composed-launch.py #Launch Velodyne VLP-16 Sensor Nodes
ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedx publish_map_tf:=false publish_tf:=false #Launch Zed X Nodes
ros2 launch navigation navigation.launch.py  #Launch Navigation

```


