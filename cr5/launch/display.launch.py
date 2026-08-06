from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # 获取包路径
    urdf_file = PathJoinSubstitution([
        FindPackageShare('cr5'),
        'urdf',
        'dual_arm.xacro'
    ])
    
    # 加载URDF
    robot_desc = ParameterValue(
        Command(["xacro ", urdf_file]),
        value_type=str
    )

    # robot_state_publisher 发布TF
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_desc}],
        output="screen"
    )

    # 关节滑块GUI
    jsp_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        output="screen"
    )

    # RViz
    rviz_config = PathJoinSubstitution([
        FindPackageShare("cr5"),
        "rviz",
        "dual_urdf.rviz"
      ])
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_config],
        output="screen"
     )
    return LaunchDescription([rsp, jsp_gui, rviz])