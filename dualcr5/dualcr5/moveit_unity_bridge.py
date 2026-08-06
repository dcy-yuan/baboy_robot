#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from moveit_msgs.msg import DisplayTrajectory, RobotTrajectory
from sensor_msgs.msg import JointState
from enum import Enum


class BridgeMode(Enum):
    IDLE = 0
    PLAN = 1
    EXECUTE = 2


class MoveItUnityBridge(Node):

    def __init__(self):
        super().__init__('moveit_unity_bridge')

        self.mode = BridgeMode.IDLE

        # =========================================================
        # ★ Unity 期望的严格顺序
        # =========================================================
        self.desired_joint_names = [
            'left_jt1', 'left_jt2', 'left_jt3', 'left_jt4', 'left_jt5', 'left_jt6',
            'right_jt1', 'right_jt2', 'right_jt3', 'right_jt4', 'right_jt5', 'right_jt6'
        ]
        
        # 用于缓存重排索引，避免每次回调都做字符串查找
        self.reorder_indices = None

        self.trajectory_sub = self.create_subscription(
            DisplayTrajectory,
            '/display_planned_path',
            self.trajectory_callback,
            10
        )

        self.joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10
        )

        self.unity_joint_pub = self.create_publisher(
            JointState,
            '/unity/joint_states',
            10
        )

        self.unity_trajectory_pub = self.create_publisher(
            RobotTrajectory,
            '/unity/robot_trajectory',
            10
        )

        self.get_logger().info('MoveIt-Unity Bridge started')
        self.get_logger().info('Mode: IDLE')


    # =========================================================
    # ★ 新增：构建索引缓存，只需在第一帧数据到来时运行一次
    # =========================================================
    def build_reorder_indices(self, original_names):
        """
        根据第一帧的原始名称，找出它们在 desired_joint_names 中的位置索引
        """
        self.reorder_indices = []
        for desired_name in self.desired_joint_names:
            if desired_name in original_names:
                # 记录：期望的数据应该从原始数组的哪个位置取
                self.reorder_indices.append(original_names.index(desired_name))
            else:
                self.get_logger().error(f'Joint "{desired_name}" not found in incoming message!')
                return False
        
        self.get_logger().info(f'Reorder indices built: {self.reorder_indices}')
        return True


    # =========================================================
    # ★ Execute 阶段：实时重排关节状态
    # =========================================================
    def joint_state_callback(self, msg):
        
        # 第一帧数据到来时，构建索引
        if self.reorder_indices is None:
            if not self.build_reorder_indices(msg.name):
                self.get_logger().error('Failed to build indices. Dropping messages.')
                self.reorder_indices = [] # 防止无限报错
                return

        if self.mode != BridgeMode.EXECUTE:
            self.mode = BridgeMode.EXECUTE
            self.get_logger().info('Switch to EXECUTE mode')

        # 按缓存索引重排数据
        unity_msg = JointState()
        unity_msg.header = msg.header
        unity_msg.name = self.desired_joint_names
        
        # 使用列表推导式快速重排
        unity_msg.position = [msg.position[i] for i in self.reorder_indices] if msg.position else []
        unity_msg.velocity = [msg.velocity[i] for i in self.reorder_indices] if msg.velocity else []
        unity_msg.effort   = [msg.effort[i] for i in self.reorder_indices] if msg.effort else []

        self.unity_joint_pub.publish(unity_msg)


    # =========================================================
    # ★ Plan 阶段：重排规划轨迹中的每一个点
    # =========================================================
    def trajectory_callback(self, msg):
        if not msg.trajectory:
            self.get_logger().warn('Empty DisplayTrajectory received')
            return

        robot_trajectory = msg.trajectory[0]

        self.mode = BridgeMode.PLAN
        self.get_logger().info('Switch to PLAN mode')

        orig_names = robot_trajectory.joint_trajectory.joint_names
        
        # 为 Plan 轨迹单独计算一次重排索引
        plan_reorder_indices = []
        for desired_name in self.desired_joint_names:
            if desired_name in orig_names:
                plan_reorder_indices.append(orig_names.index(desired_name))
            else:
                self.get_logger().warn(f'Joint "{desired_name}" not found in plan trajectory, skipping remap.')
                # 如果名称不全，直接发布原始数据退避
                self.unity_trajectory_pub.publish(robot_trajectory)
                return

        # 遍历轨迹点，重排数据
        remapped_trajectory = robot_trajectory
        joint_traj = remapped_trajectory.joint_trajectory
        joint_traj.joint_names = self.desired_joint_names
        
        for point in joint_traj.points:
            point.positions     = [point.positions[i] for i in plan_reorder_indices] if point.positions else []
            point.velocities    = [point.velocities[i] for i in plan_reorder_indices] if point.velocities else []
            point.accelerations = [point.accelerations[i] for i in plan_reorder_indices] if point.accelerations else []
            point.effort        = [point.effort[i] for i in plan_reorder_indices] if point.effort else []

        self.unity_trajectory_pub.publish(remapped_trajectory)

        self.get_logger().info(
            f'PLAN trajectory sent to Unity '
            f'({len(remapped_trajectory.joint_trajectory.points)} points)'
        )


def main(args=None):
    rclpy.init(args=args)
    bridge = MoveItUnityBridge()

    try:
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.destroy_node()
        rclpy.shutdown()

