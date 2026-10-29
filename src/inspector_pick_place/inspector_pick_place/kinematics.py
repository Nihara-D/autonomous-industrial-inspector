"""Closed-form kinematics of the 4-DOF inspector arm (no ROS imports).

joint_1 yaw at z=0.05 | joint_2/joint_3 pitch (shoulder z=0.25, links 0.30 / 0.25)
joint_4 roll about the tool axis. TCP is 0.13 m beyond the wrist along the forearm axis,
so the tool is collinear with the forearm and the approach direction is a by-product of IK.
Angles in the arm plane are measured from vertical: direction(theta) = (sin, cos) in (r, z).
"""
import math
from typing import List, Sequence, Tuple

SHOULDER_Z = 0.25
L_UPPER = 0.30
L_FOREARM = 0.25
TCP_OFFSET = 0.13
L_TOOL = L_FOREARM + TCP_OFFSET

# Must match the URDF <limit> tags.
JOINT_LIMITS = {
    'joint_1': (-3.14, 3.14),
    'joint_2': (-1.57, 1.57),
    'joint_3': (-2.4, 2.4),
    'joint_4': (-3.14, 3.14),
}
ARM_JOINTS = list(JOINT_LIMITS.keys())

Vec3 = Tuple[float, float, float]


class IKError(Exception):
    """Target unreachable or outside joint limits."""


def forward_kinematics(j1: float, j2: float, j3: float) -> Vec3:
    b = j2 + j3
    r = L_UPPER * math.sin(j2) + L_TOOL * math.sin(b)
    z = SHOULDER_Z + L_UPPER * math.cos(j2) + L_TOOL * math.cos(b)
    return r * math.cos(j1), r * math.sin(j1), z


def tool_direction(joints: Sequence[float]) -> Vec3:
    j1, j2, j3 = joints[0], joints[1], joints[2]
    b = j2 + j3
    return math.sin(b) * math.cos(j1), math.sin(b) * math.sin(j1), math.cos(b)


def inverse_kinematics(x: float, y: float, z: float, j4: float = 0.0) -> List[float]:
    """Elbow-up IK for the TCP position. Raises IKError if unreachable / out of limits."""
    r = math.hypot(x, y)
    if r < 0.15:
        raise IKError(f'target too close to the base axis (r={r:.3f} m)')
    j1 = math.atan2(y, x)
    zr = z - SHOULDER_Z
    d2 = r * r + zr * zr
    c3 = (d2 - L_UPPER ** 2 - L_TOOL ** 2) / (2.0 * L_UPPER * L_TOOL)
    if abs(c3) > 1.0:
        raise IKError(f'({x:.3f}, {y:.3f}, {z:.3f}) is out of reach (cos j3 = {c3:.2f})')
    j3 = math.acos(c3)
    j2 = math.atan2(r, zr) - math.atan2(L_TOOL * math.sin(j3), L_UPPER + L_TOOL * math.cos(j3))
    joints = [j1, j2, j3, j4]
    for name, q in zip(ARM_JOINTS, joints):
        lo, hi = JOINT_LIMITS[name]
        if not lo <= q <= hi:
            raise IKError(f'{name}={q:.3f} outside [{lo}, {hi}] for target '
                          f'({x:.3f}, {y:.3f}, {z:.3f})')
    return joints


def offset_along_tool(joints: Sequence[float], tcp: Vec3, distance: float) -> Vec3:
    """Point `distance` metres back along the tool axis from `tcp`."""
    d = tool_direction(joints)
    return tcp[0] - distance * d[0], tcp[1] - distance * d[1], tcp[2] - distance * d[2]


def linear_path(p0: Vec3, p1: Vec3, steps: int, j4: float = 0.0) -> List[List[float]]:
    """Joint waypoints so the TCP follows the straight line p0 -> p1 (steps+1 points)."""
    path = []
    for i in range(steps + 1):
        t = i / steps
        p = tuple(a + t * (b - a) for a, b in zip(p0, p1))
        path.append(inverse_kinematics(*p, j4=j4))
    return path
