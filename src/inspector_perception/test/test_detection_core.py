import cv2
import numpy as np
import pytest

from inspector_perception.detection_core import (
    Camera, detect_colors, pixel_to_world, world_to_pixel)

CAM = Camera()
TOP_Z = 0.475


def synth_scene(objs):
    img = np.full((480, 640, 3), 150, np.uint8)
    tl = world_to_pixel(0.65, 0.2, 0.4, CAM)
    br = world_to_pixel(0.25, -0.2, 0.4, CAM)
    cv2.rectangle(img, tuple(map(int, tl)), tuple(map(int, br)), (64, 102, 140), -1)
    bgr = {'red': (25, 25, 230), 'green': (25, 204, 25), 'blue': (230, 50, 25)}
    for color, x, y in objs:
        u, v = world_to_pixel(x, y, TOP_Z, CAM)
        half = 0.025 * CAM.fx / (CAM.z - TOP_Z)
        cv2.rectangle(img, (int(u - half), int(v - half)), (int(u + half), int(v + half)),
                      bgr[color], -1)
    return img


def test_roundtrip():
    for x, y in [(0.4, 0.12), (0.4, 0.0), (0.5, -0.1)]:
        u, v = world_to_pixel(x, y, TOP_Z, CAM)
        assert pixel_to_world(u, v, CAM, TOP_Z) == pytest.approx((x, y, TOP_Z), abs=1e-9)


def test_image_orientation():
    u_red, _ = world_to_pixel(0.4, 0.12, TOP_Z, CAM)
    u_blue, _ = world_to_pixel(0.4, -0.12, TOP_Z, CAM)
    assert u_red < CAM.cx < u_blue
    _, v_far = world_to_pixel(0.5, 0, TOP_Z, CAM)
    assert v_far < CAM.cy


def test_detects_all_three_cubes_with_mm_accuracy():
    truth = [('red', 0.4, 0.12), ('green', 0.4, 0.0), ('blue', 0.4, -0.12)]
    dets = detect_colors(synth_scene(truth))
    assert sorted(d.color for d in dets) == ['blue', 'green', 'red']
    for color, x, y in truth:
        d = next(d for d in dets if d.color == color)
        wx, wy, _ = pixel_to_world(d.u, d.v, CAM, TOP_Z)
        assert (wx, wy) == pytest.approx((x, y), abs=0.003)


def test_missing_cube_not_reported():
    dets = detect_colors(synth_scene([('green', 0.4, 0.0)]))
    assert [d.color for d in dets] == ['green']
