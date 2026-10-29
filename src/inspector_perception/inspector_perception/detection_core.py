"""ROS-free colour detection + pixel->world geometry (unit-testable)."""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# HSV ranges (OpenCV: H 0-179). Red wraps around hue 0.
COLOR_RANGES: Dict[str, List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]] = {
    'red': [((0, 120, 60), (8, 255, 255)), ((172, 120, 60), (179, 255, 255))],
    'green': [((40, 100, 50), (80, 255, 255))],
    'blue': [((100, 120, 50), (130, 255, 255))],
}

DRAW_BGR = {'red': (0, 0, 255), 'green': (0, 255, 0), 'blue': (255, 0, 0)}


@dataclass
class Detection:
    color: str
    u: float
    v: float
    area: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h


@dataclass
class Camera:
    """Pinhole camera looking straight down (optical axis = world -Z).
    Image-up = world +X, image-left = world +Y."""
    fx: float = 554.26
    fy: float = 554.26
    cx: float = 320.0
    cy: float = 240.0
    x: float = 0.4
    y: float = 0.0
    z: float = 1.2


def detect_colors(bgr: np.ndarray, min_area: float = 150.0,
                  colors: Optional[List[str]] = None) -> List[Detection]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    kernel = np.ones((3, 3), np.uint8)
    out: List[Detection] = []
    for name in (colors or COLOR_RANGES.keys()):
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for lo, hi in COLOR_RANGES[name]:
            mask |= cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            m = cv2.moments(c)
            if m['m00'] == 0:
                continue
            out.append(Detection(name, m['m10'] / m['m00'], m['m01'] / m['m00'],
                                 float(area), tuple(int(v) for v in cv2.boundingRect(c))))
    return out


def pixel_to_world(u: float, v: float, cam: Camera, plane_z: float) -> Tuple[float, float, float]:
    """Back-project a pixel onto the horizontal plane z = plane_z."""
    depth = cam.z - plane_z
    x = cam.x - (v - cam.cy) / cam.fy * depth
    y = cam.y - (u - cam.cx) / cam.fx * depth
    return x, y, plane_z


def world_to_pixel(x: float, y: float, z: float, cam: Camera) -> Tuple[float, float]:
    depth = cam.z - z
    return (cam.cx - cam.fx * (y - cam.y) / depth,
            cam.cy - cam.fy * (x - cam.x) / depth)


def annotate(bgr: np.ndarray, dets: List[Detection],
             world: Dict[int, Tuple[float, float, float]]) -> np.ndarray:
    img = bgr.copy()
    for i, d in enumerate(dets):
        x, y, w, h = d.bbox
        col = DRAW_BGR.get(d.color, (255, 255, 255))
        cv2.rectangle(img, (x, y), (x + w, y + h), col, 2)
        cv2.circle(img, (int(d.u), int(d.v)), 3, (255, 255, 255), -1)
        label = d.color
        if i in world:
            label += f' ({world[i][0]:.2f},{world[i][1]:.2f})'
        cv2.putText(img, label, (x, max(12, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1,
                    cv2.LINE_AA)
    return img
