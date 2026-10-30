"""Automated pick-and-place for the inspector arm.

Per colour in `pick_order`:
  detect -> MoveIt to pre-grasp -> straight-line approach -> close gripper -> straight-line lift
  -> MoveIt to pre-place -> straight-line lower -> open gripper -> retreat -> MoveIt home.
Large moves use MoveIt's /move_action; short final segments are IK-interpolated and sent
directly to arm_controller (a 4-DOF arm cannot hold tool orientation for MoveIt Cartesian paths).
"""
import json
import statistics
import sys
import time
from collections import defaultdict, deque

import rclpy
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (CollisionObject, Constraints, JointConstraint,
                             MoveItErrorCodes, PlanningScene)
from moveit_msgs.srv import ApplyPlanningScene
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectoryPoint

from inspector_pick_place.kinematics import ARM_JOINTS, IKError, linear_path
from inspector_pick_place.task_geometry import PLACE_SLOTS, plan_cycle

FINGERS = ['finger_left_joint', 'finger_right_joint']
GRIPPER_OPEN = 0.020
GRIPPER_CLOSED = -0.004  # squeeze 4 mm past the 50 mm cube so the fingers keep pushing
HOME = [0.0, 0.0, 0.0, 0.0]

# Static obstacles mirrored from inspection_world.sdf: (id, centre xyz, size xyz)
OBSTACLES = [
    ('inspection_table', (0.45, 0.0, 0.2), (0.4, 0.4, 0.4)),
    ('output_pedestal', (0.0, 0.46, 0.2), (0.2, 0.32, 0.4)),
]


class PickPlaceError(RuntimeError):
    pass


def _dur(seconds: float) -> Duration:
    sec = int(seconds)
    return Duration(sec=sec, nanosec=int((seconds - sec) * 1e9))


class PickPlaceNode(Node):
    def __init__(self):
        super().__init__('pick_place_node')
        self.declare_parameter('pick_order', 'red,green,blue')
        self.declare_parameter('start_delay', 5.0)
        self.declare_parameter('approach_distance', 0.08)
        self.declare_parameter('lift_height', 0.07)
        self.declare_parameter('grasp_z_offset', 0.01)
        self.declare_parameter('linear_speed', 0.05)
        self.declare_parameter('velocity_scaling', 0.4)
        self.declare_parameter('detection_samples', 8)

        gp = self.get_parameter
        self.order = [c.strip() for c in str(gp('pick_order').value).split(',') if c.strip()]
        self.approach = gp('approach_distance').value
        self.lift = gp('lift_height').value
        self.grasp_dz = gp('grasp_z_offset').value
        self.speed = gp('linear_speed').value
        self.vel_scale = gp('velocity_scaling').value
        self.n_samples = int(gp('detection_samples').value)

        self.samples = defaultdict(lambda: deque(maxlen=30))
        self.joints = {}

        self.create_subscription(String, '/inspector/detections', self._on_det, 10)
        self.create_subscription(JointState, '/joint_states', self._on_js, 10)

        self.move_client = ActionClient(self, MoveGroup, '/move_action')
        self.arm_client = ActionClient(self, FollowJointTrajectory,
                                       '/arm_controller/follow_joint_trajectory')
        self.grip_client = ActionClient(self, FollowJointTrajectory,
                                        '/gripper_controller/follow_joint_trajectory')
        self.scene_client = self.create_client(ApplyPlanningScene, '/apply_planning_scene')

    # ---------------------------------------------------------------- callbacks
    def _on_det(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        now = time.monotonic()
        for o in data.get('objects', []):
            self.samples[o['color']].append((now, o['x'], o['y']))

    def _on_js(self, msg: JointState):
        self.joints.update(zip(msg.name, msg.position))

    # ---------------------------------------------------------------- helpers
    def _spin_until(self, predicate, timeout, what):
        end = time.monotonic() + timeout
        while rclpy.ok() and not predicate():
            if time.monotonic() > end:
                raise PickPlaceError(f'timeout waiting for {what}')
            rclpy.spin_once(self, timeout_sec=0.05)

    def _sleep(self, seconds):
        end = time.monotonic() + seconds
        while rclpy.ok() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def _send(self, client, goal, timeout, what):
        fut = client.send_goal_async(goal)
        self._spin_until(fut.done, 10.0, f'{what} goal acceptance')
        handle = fut.result()
        if not handle.accepted:
            raise PickPlaceError(f'{what} goal rejected')
        res = handle.get_result_async()
        self._spin_until(res.done, timeout, f'{what} result')
        return res.result()

    def wait_for_system(self):
        self.get_logger().info('waiting for move_group, controllers, joint states, camera ...')
        for client, name in ((self.move_client, '/move_action'),
                             (self.arm_client, 'arm_controller'),
                             (self.grip_client, 'gripper_controller')):
            if not client.wait_for_server(timeout_sec=120.0):
                raise PickPlaceError(f'{name} action server not available')
        if not self.scene_client.wait_for_service(timeout_sec=60.0):
            raise PickPlaceError('/apply_planning_scene not available')
        self._spin_until(lambda: all(j in self.joints for j in ARM_JOINTS + FINGERS), 60.0,
                         'joint states')
        self._spin_until(lambda: len(self.samples) > 0, 60.0, '/inspector/detections')
        self.get_logger().info('system ready')

    def add_obstacles(self):
        scene = PlanningScene()
        scene.is_diff = True
        for name, c, size in OBSTACLES:
            obj = CollisionObject()
            obj.id = name
            obj.header.frame_id = 'world'
            prim = SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size))
            pose = Pose()
            pose.position.x, pose.position.y, pose.position.z = c
            pose.orientation.w = 1.0
            obj.primitives.append(prim)
            obj.primitive_poses.append(pose)
            obj.operation = CollisionObject.ADD
            scene.world.collision_objects.append(obj)
        req = ApplyPlanningScene.Request()
        req.scene = scene
        fut = self.scene_client.call_async(req)
        self._spin_until(fut.done, 10.0, 'apply_planning_scene')
        if not fut.result().success:
            raise PickPlaceError('failed to add collision objects to the planning scene')
        self.get_logger().info(f'added {len(OBSTACLES)} collision objects to the planning scene')

    # ---------------------------------------------------------------- perception
    def locate(self, colour):
        """Median (x, y) of recent detections; waits for enough fresh samples."""
        def fresh():
            now = time.monotonic()
            return [s for s in self.samples[colour] if now - s[0] < 3.0]
        try:
            self._spin_until(lambda: len(fresh()) >= self.n_samples, 20.0,
                             f'{self.n_samples} fresh detections of "{colour}"')
        except PickPlaceError:
            return None
        pts = fresh()
        return (statistics.median(p[1] for p in pts), statistics.median(p[2] for p in pts))

    # ---------------------------------------------------------------- motion
    def gripper(self, opening):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = FINGERS
        goal.trajectory.points = [JointTrajectoryPoint(
            positions=[opening, opening], time_from_start=_dur(1.5))]
        res = self._send(self.grip_client, goal, 15.0, 'gripper')
        # Closing on an object stalls the fingers; a tolerance report here is expected.
        self.get_logger().debug(f'gripper result code {res.result.error_code}')
        self._sleep(0.5)

    def moveit_to(self, joints, label):
        self.get_logger().info(f'MoveIt: planning to {label}')
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = 'arm'
        req.num_planning_attempts = 10
        req.allowed_planning_time = 5.0
        req.max_velocity_scaling_factor = self.vel_scale
        req.max_acceleration_scaling_factor = self.vel_scale
        req.start_state.is_diff = True
        c = Constraints()
        for name, val in zip(ARM_JOINTS, joints):
            c.joint_constraints.append(JointConstraint(
                joint_name=name, position=float(val),
                tolerance_above=0.005, tolerance_below=0.005, weight=1.0))
        req.goal_constraints.append(c)
        goal.planning_options.plan_only = False
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        res = self._send(self.move_client, goal, 60.0, f'MoveIt "{label}"')
        code = res.result.error_code.val
        if code != MoveItErrorCodes.SUCCESS:
            raise PickPlaceError(f'MoveIt failed for "{label}" (error code {code})')

    def linear_move(self, p0, p1, label):
        """Straight TCP line p0 -> p1 executed directly on arm_controller."""
        dist = sum((a - b) ** 2 for a, b in zip(p0, p1)) ** 0.5
        steps = max(4, int(dist / 0.01))
        duration = max(1.0, dist / self.speed)
        try:
            path = linear_path(p0, p1, steps)
        except IKError as e:
            raise PickPlaceError(f'linear move "{label}" infeasible: {e}')
        self.get_logger().info(f'linear move: {label} ({dist * 100:.1f} cm, {duration:.1f} s)')
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ARM_JOINTS
        here = [self.joints[j] for j in ARM_JOINTS]
        goal.trajectory.points.append(
            JointTrajectoryPoint(positions=here, time_from_start=_dur(0.0)))
        for i, q in enumerate(path[1:], start=1):
            goal.trajectory.points.append(JointTrajectoryPoint(
                positions=[float(v) for v in q],
                time_from_start=_dur(0.5 + duration * i / steps)))
        res = self._send(self.arm_client, goal, duration + 20.0, f'linear "{label}"')
        if res.result.error_code != FollowJointTrajectory.Result.SUCCESSFUL:
            raise PickPlaceError(f'linear move "{label}" failed: {res.result.error_string}')
        self._sleep(0.3)

    # ---------------------------------------------------------------- task
    def pick_and_place(self, colour, slot_index):
        pos = self.locate(colour)
        if pos is None:
            self.get_logger().warn(f'no "{colour}" cube visible - skipping')
            return False
        if not (0.2 < pos[0] < 0.7 and abs(pos[1]) < 0.25):
            self.get_logger().warn(f'"{colour}" detected at {pos} - outside the table, skipping')
            return False
        slot = PLACE_SLOTS[slot_index]
        self.get_logger().info(
            f'=== {colour}: table ({pos[0]:.3f}, {pos[1]:.3f}) -> pedestal slot {slot} ===')
        try:
            plan = plan_cycle(pos, slot, grasp_z_offset=self.grasp_dz,
                              approach=self.approach, lift=self.lift)
        except IKError as e:
            self.get_logger().error(f'"{colour}" is not reachable: {e}')
            return False

        self.gripper(GRIPPER_OPEN)
        self.moveit_to(plan.pregrasp.joints, 'pre-grasp')
        self.linear_move(plan.pregrasp.tcp, plan.grasp.tcp, 'approach cube')
        self.gripper(GRIPPER_CLOSED)
        self.linear_move(plan.grasp.tcp, plan.lift.tcp, 'lift cube')
        self.moveit_to(plan.preplace.joints, 'pre-place')
        self.linear_move(plan.preplace.tcp, plan.place.tcp, 'lower onto pedestal')
        self.gripper(GRIPPER_OPEN)
        self.linear_move(plan.place.tcp, plan.preplace.tcp, 'retreat')
        self.moveit_to(HOME, 'home')
        return True

    def run(self):
        self.wait_for_system()
        self._sleep(float(self.get_parameter('start_delay').value))
        self.add_obstacles()
        self.gripper(GRIPPER_OPEN)
        self.moveit_to(HOME, 'home')

        if len(self.order) > len(PLACE_SLOTS):
            raise PickPlaceError(f'pick_order has {len(self.order)} colours but only '
                                 f'{len(PLACE_SLOTS)} pedestal slots exist')
        done = 0
        for i, colour in enumerate(self.order):
            try:
                done += bool(self.pick_and_place(colour, i))
            except PickPlaceError as e:
                self.get_logger().error(f'{colour}: {e} - opening gripper and returning home')
                try:
                    self.gripper(GRIPPER_OPEN)
                    self.moveit_to(HOME, 'home (recovery)')
                except PickPlaceError:
                    pass
        self.get_logger().info(f'finished: {done}/{len(self.order)} objects sorted')
        return done == len(self.order)


def main(args=None):
    rclpy.init(args=args)
    node = PickPlaceNode()
    ok = False
    try:
        ok = node.run()
    except PickPlaceError as e:
        node.get_logger().fatal(str(e))
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
