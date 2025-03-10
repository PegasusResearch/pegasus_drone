#!/usr/bin/env python3
import os
import sys
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    
    # --------------------------------
    # Define the vehicle ID
    # --------------------------------
    
    # Set the default vehicle id (note: this is a trick due to the parameter reading limitation in ROS2)
    default_vehicle_id = 1
    vehicle_id = default_vehicle_id
    for arg in sys.argv:
        if arg.startswith('vehicle_id:='):
            vehicle_id = int(arg.split(':=')[1])
    
    # ----------------------------------------
    # ---- DECLARE THE LAUNCH ARGUMENTS ------
    # ----------------------------------------

    # Namespace and ID of the vehicle as parameter received by the launch file
    id_arg = DeclareLaunchArgument('vehicle_id', default_value=str(vehicle_id), description='Drone ID in the network')
    namespace_arg = DeclareLaunchArgument('vehicle_ns', default_value='drone', description='Namespace to append to every topic and node name')

    drone_params_file_arg = DeclareLaunchArgument(
        'drone_params', 
        default_value=os.path.join(get_package_share_directory('pegasus_drone'), 'config', 'pegasus.yaml'),
        description='The directory where the drone parameters such as mass, thrust curve, etc. are defined')

    # ----------------------------------------
    # ---------- CONTROL PIPELINE ------------
    # ----------------------------------------

    # Define the standard mavlink port to forward mavlink data (so that it can also be viewed internally by qgroundcontrol)
    mavlink_forward_addresses = "['']"
    mavlink_forward_addresses = "['udp://192.168.1.232:15001']"

    # Define the drone MAVLINK IP and PORT
    mav_connection_arg = DeclareLaunchArgument('connection', default_value='serial:///dev/ttyTHS1:921600', description='The interface used to connect to the vehicle')

    # Define the drone MAVLINK forward ips and ports
    mavlink_forward_arg = DeclareLaunchArgument('mavlink_forward', default_value=mavlink_forward_addresses, description='A list of ips where to forward mavlink messages')
    
    # Call MAVLINK interface package launch file 
    mavlink_interface_launch_file = IncludeLaunchDescription(
        # Grab the launch file for the mavlink interface
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('mavlink_interface'), 'launch/mavlink_interface.launch.py')),
        # Define costume launch arguments/parameters used for the mavlink interface
        launch_arguments={
            'id': LaunchConfiguration('vehicle_id'), 
            'namespace': LaunchConfiguration('vehicle_ns'),
            'drone_params': LaunchConfiguration('drone_params'),
            'connection': LaunchConfiguration('connection'),
            'mavlink_forward': LaunchConfiguration('mavlink_forward')
        }.items(),
    )

    # Call autopilot package launch file
    autopilot_launch_file = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory('autopilot'), 'launch/autopilot.launch.py')),
        # Define costume launch arguments/parameters used 
        launch_arguments={
            'id': LaunchConfiguration('vehicle_id'),
            'namespace': LaunchConfiguration('vehicle_ns'),
            'autopilot_yaml': LaunchConfiguration('drone_params'),
        }.items(),
    )

    # ----------------------------------------
    # ----------- IMAGE PIPELINE -------------
    # ----------------------------------------

    """Launch file which brings up visual slam node configured for RealSense."""
    realsense_camera_node = ComposableNode(
        name='camera',
        namespace=[
            LaunchConfiguration('vehicle_ns'), 
            LaunchConfiguration('vehicle_id')],
        package='realsense2_camera',
        plugin='realsense2_camera::RealSenseNodeFactory',
        parameters=[LaunchConfiguration('drone_params')],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    visual_slam_node = ComposableNode(
        name='visual_slam_node',
        namespace=[
            LaunchConfiguration('vehicle_ns'), 
            LaunchConfiguration('vehicle_id')],
        package='isaac_ros_visual_slam',
        plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode',
        parameters=[{
            'enable_image_denoising': False,
            'rectified_images': True,
            'enable_imu_fusion': True,
            'gyro_noise_density': 0.000244,
            'gyro_random_walk': 0.000019393,
            'accel_noise_density': 0.001862,
            'accel_random_walk': 0.003,
            'calibration_frequency': 200.0,
            'image_jitter_threshold_ms': 22.00,
            'base_frame': 'camera_link',
            'imu_frame': 'camera_gyro_optical_frame',
            'enable_slam_visualization': True,
            'enable_landmarks_view': True,
            'enable_observations_view': True,
            'camera_optical_frames': [
                'camera_infra1_optical_frame',
                'camera_infra2_optical_frame',
            ],
        }],
        remappings=[
            ('visual_slam/image_0', 'camera/infra1/image_rect_raw'),
            ('visual_slam/camera_info_0', 'camera/infra1/camera_info'),
            ('visual_slam/image_1', 'camera/infra2/image_rect_raw'),
            ('visual_slam/camera_info_1', 'camera/infra2/camera_info'),
            ('visual_slam/imu', 'camera/imu'),
        ],
    )

    visual_slam_launch_container = ComposableNodeContainer(
        name='visual_slam_launch_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[realsense_camera_node, visual_slam_node], 
        output='screen',
        emulate_tty=True, # needed for display of logs
        arguments=['--ros-args', '--log-level', 'info'],
    )

    # Create the node that starts the web video server
    web_video_server = Node(
        package='web_video_server',
        namespace=[
            LaunchConfiguration('vehicle_ns'), 
            LaunchConfiguration('vehicle_id')],
        executable='web_video_server',
        name='web_video_server',
        output="screen",
        emulate_tty=True,
        parameters=[
            # Set the default parameters for the web video server
            {
                'port': '8080',
                'address': '0.0.0.0',
                'server_threads': 1, 
                'ros_threads': '1',
                'default_stream_type': 'mjpeg',
                'verbose': True
            }
        ]
    )

    # ----------------------------------------
    # ---- RETURN THE LAUNCH DESCRIPTION -----
    # ----------------------------------------
    return LaunchDescription([
        # Launch arguments
        id_arg, 
        namespace_arg, 
        drone_params_file_arg,
        mav_connection_arg,
        mavlink_forward_arg,
        # Video Nodes
        visual_slam_launch_container,
        web_video_server,
        # Control Nodes
        mavlink_interface_launch_file,
        autopilot_launch_file
    ])
