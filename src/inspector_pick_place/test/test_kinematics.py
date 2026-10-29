import math

import pytest

from inspector_pick_place.kinematics import (
    IKError, JOINT_LIMITS, forward_kinematics, inverse_kinematics, linear_path, tool_direction)
from inspector_pick_place.task_geometry import PLACE_SLOTS, plan_cycle

CUBES = {'red': (0.4, 0.12), 'green': (0.4, 0.0), 'blue': (0.4, -0.12)}


def test_home_pose_fk():
    assert forward_kinematics(0, 0, 0) == pytest.approx((0, 0, 0.93))


@pytest.mark.parametrize('p', [(0.4, 0.12, 0.435), (0.4, 0, 0.435), (0.0, 0.55, 0.44),
                               (0.0, 0.39, 0.44), (0.3, -0.2, 0.5)])
def test_fk_ik_roundtrip(p):
    q = inverse_kinematics(*p)
    assert forward_kinematics(*q[:3]) == pytest.approx(p, abs=1e-9)
    for name, v in zip(JOINT_LIMITS, q):
        lo, hi = JOINT_LIMITS[name]
        assert lo <= v <= hi


def test_unreachable_raises():
    with pytest.raises(IKError):
        inverse_kinematics(1.2, 0, 0.4)
    with pytest.raises(IKError):
        inverse_kinematics(0.05, 0.0, 0.4)


def test_linear_path_is_straight():
    p0, p1 = (0.32, 0.1, 0.46), (0.40, 0.1, 0.435)
    path = linear_path(p0, p1, 10)
    assert len(path) == 11
    for i, q in enumerate(path):
        t = i / 10
        want = tuple(a + t * (b - a) for a, b in zip(p0, p1))
        assert forward_kinematics(*q[:3]) == pytest.approx(want, abs=1e-9)
    for a, b in zip(path, path[1:]):
        assert max(abs(x - y) for x, y in zip(a, b)) < 0.1


@pytest.mark.parametrize('color', CUBES)
@pytest.mark.parametrize('slot', range(3))
def test_every_pick_place_combination_is_feasible(color, slot):
    plan = plan_cycle(CUBES[color], PLACE_SLOTS[slot])
    for wp in (plan.grasp, plan.place):
        d = tool_direction(wp.joints)
        assert -10 < math.degrees(-math.asin(d[2])) < 45
    linear_path(plan.pregrasp.tcp, plan.grasp.tcp, 10)
    linear_path(plan.grasp.tcp, plan.lift.tcp, 6)
    linear_path(plan.preplace.tcp, plan.place.tcp, 10)
    for wp in (plan.pregrasp, plan.grasp, plan.lift, plan.preplace, plan.place):
        assert wp.tcp[2] >= 0.43
