"""Pure-geometry planning of one pick-and-place cycle (no ROS imports)."""
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from inspector_pick_place.kinematics import Vec3, inverse_kinematics, offset_along_tool

# World layout (must match inspection_world.sdf)
TABLE_TOP_Z = 0.40
CUBE_SIZE = 0.05
# Pedestal slots, filled farthest-first so later approaches never cross a placed cube.
PLACE_SLOTS: List[Tuple[float, float]] = [(0.0, 0.55), (0.0, 0.47), (0.0, 0.39)]
PLACE_SURFACE_Z = 0.40


@dataclass
class Waypoint:
    tcp: Vec3
    joints: List[float]


@dataclass
class CyclePlan:
    pregrasp: Waypoint
    grasp: Waypoint
    lift: Waypoint
    preplace: Waypoint
    place: Waypoint


def _wp(p: Sequence[float]) -> Waypoint:
    p = (float(p[0]), float(p[1]), float(p[2]))
    return Waypoint(p, inverse_kinematics(*p))


def plan_cycle(cube_xy: Tuple[float, float], slot_xy: Tuple[float, float],
               grasp_z_offset: float = 0.01, approach: float = 0.08, lift: float = 0.07,
               place_hover: float = 0.03, release_clearance: float = 0.005,
               cube_z: float = TABLE_TOP_Z + CUBE_SIZE / 2,
               place_z: float = PLACE_SURFACE_Z + CUBE_SIZE / 2) -> CyclePlan:
    """All joint-space waypoints for one cube. Raises IKError if infeasible."""
    grasp_tcp = (cube_xy[0], cube_xy[1], cube_z + grasp_z_offset)
    grasp = _wp(grasp_tcp)
    pre = _wp(offset_along_tool(grasp.joints, grasp_tcp, approach))
    lifted = _wp((grasp_tcp[0], grasp_tcp[1], grasp_tcp[2] + lift))

    place_tcp = (slot_xy[0], slot_xy[1], place_z + grasp_z_offset + release_clearance)
    place = _wp(place_tcp)
    pp = offset_along_tool(place.joints, place_tcp, approach)
    preplace = _wp((pp[0], pp[1], pp[2] + place_hover))
    return CyclePlan(pre, grasp, lifted, preplace, place)
