#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA

from moveit_msgs.msg import CollisionObject, PlanningScene, ObjectColor
from moveit_msgs.srv import ApplyPlanningScene
from shape_msgs.msg import SolidPrimitive, Mesh, MeshTriangle

from unity_moveit_bridge_msgs.msg import ObstacleArray, MeshObstacleArray


class UnityMoveItSceneBridge(Node):
    def __init__(self):
        super().__init__('unity_moveit_scene_bridge')

        self.declare_parameter('primitive_topic', '/unity_collision_objects')
        self.declare_parameter('mesh_topic', '/unity_mesh_collision_objects')
        self.declare_parameter('apply_service', '/apply_planning_scene')
        self.declare_parameter('frame_id', 'dual_arm')

        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        prim_topic = self.get_parameter('primitive_topic').get_parameter_value().string_value
        mesh_topic = self.get_parameter('mesh_topic').get_parameter_value().string_value
        srv_name = self.get_parameter('apply_service').get_parameter_value().string_value

        self.sub_prim = self.create_subscription(ObstacleArray, prim_topic, self.cb_prim, 10)
        self.sub_mesh = self.create_subscription(MeshObstacleArray, mesh_topic, self.cb_mesh, 10)

        self.cli = self.create_client(ApplyPlanningScene, srv_name)

        self.gray = ColorRGBA(r=0.5, g=0.5, b=0.5, a=1.0)

        # Mesh geometry cache by id
        self.mesh_cache = {}

        self.get_logger().info(f"Sub primitive: {prim_topic}")
        self.get_logger().info(f"Sub mesh: {mesh_topic}")
        self.get_logger().info(f"Srv: {srv_name}")
        self.get_logger().info(f"Frame: {self.frame_id}")

    def apply_scene(self, collision_objects, color_ids):
        if not self.cli.service_is_ready():
            if not self.cli.wait_for_service(timeout_sec=0.0):
                self.get_logger().warn("apply_planning_scene not ready")
                return

        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects = collision_objects

        # Set gray colors
        scene.object_colors = []
        for oid in color_ids:
            oc = ObjectColor()
            oc.id = oid
            oc.color = self.gray
            scene.object_colors.append(oc)

        req = ApplyPlanningScene.Request()
        req.scene = scene
        self.cli.call_async(req)

    def cb_prim(self, msg: ObstacleArray):
        cos = []
        color_ids = []

        for o in msg.obstacles:
            co = CollisionObject()
            co.header.frame_id = self.frame_id
            co.id = o.id

            prim = SolidPrimitive()
            if int(o.type) == 0:
                prim.type = SolidPrimitive.BOX
                prim.dimensions = [float(o.size_x), float(o.size_y), float(o.size_z)]
            elif int(o.type) == 1:
                prim.type = SolidPrimitive.CYLINDER
                # [height, radius]
                prim.dimensions = [float(o.size_y), float(o.size_x)]
            else:
                prim.type = SolidPrimitive.SPHERE
                prim.dimensions = [float(o.size_x)]  # radius

            co.primitives = [prim]
            co.primitive_poses = [o.pose]
            co.operation = CollisionObject.ADD

            cos.append(co)
            color_ids.append(o.id)

        if cos:
            self.apply_scene(cos, color_ids)

    def cb_mesh(self, msg: MeshObstacleArray):
        cos = []
        color_ids = []

        for o in msg.obstacles:
            oid = o.id

            # Register/update mesh geometry
            if o.send_mesh:
                v = o.vertices_xyz
                t = o.triangles

                if len(v) % 3 != 0 or len(t) % 3 != 0:
                    self.get_logger().warn(f"{oid}: invalid mesh arrays")
                    continue

                mesh = Mesh()

                mesh.vertices = []
                for i in range(0, len(v), 3):
                    p = Point()
                    p.x = float(v[i + 0])
                    p.y = float(v[i + 1])
                    p.z = float(v[i + 2])
                    mesh.vertices.append(p)

                mesh.triangles = []
                for i in range(0, len(t), 3):
                    tri = MeshTriangle()
                    tri.vertex_indices = [int(t[i]), int(t[i + 1]), int(t[i + 2])]
                    mesh.triangles.append(tri)

                self.mesh_cache[oid] = mesh

            if oid not in self.mesh_cache:
                # haven't registered geometry yet
                continue

            co = CollisionObject()
            co.header.frame_id = self.frame_id
            co.id = oid
            co.operation = CollisionObject.ADD
            co.meshes = [self.mesh_cache[oid]]
            co.mesh_poses = [o.pose]

            cos.append(co)
            color_ids.append(oid)

        if cos:
            self.apply_scene(cos, color_ids)


def main():
    rclpy.init()
    node = UnityMoveItSceneBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


