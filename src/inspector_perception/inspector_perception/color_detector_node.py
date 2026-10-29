"""Colour object detector for the overhead camera.

Subscribes : /camera/image_raw, /camera/camera_info
Publishes  : /camera/detections_image  (annotated Image, bgr8)
             /inspector/detections     (std_msgs/String, JSON)
"""
import json

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String

from inspector_perception.detection_core import Camera, annotate, detect_colors, pixel_to_world


def image_to_bgr(msg: Image) -> np.ndarray:
    """sensor_msgs/Image -> BGR ndarray without cv_bridge."""
    ch = {'rgb8': 3, 'bgr8': 3, 'rgba8': 4, 'bgra8': 4, 'mono8': 1}.get(msg.encoding)
    if ch is None:
        raise ValueError(f'unsupported encoding {msg.encoding}')
    arr = np.frombuffer(bytes(msg.data), np.uint8).reshape(msg.height, msg.step)
    arr = arr[:, :msg.width * ch].reshape(msg.height, msg.width, ch)
    if msg.encoding == 'rgb8':
        return np.ascontiguousarray(arr[:, :, ::-1])
    if msg.encoding == 'rgba8':
        return np.ascontiguousarray(arr[:, :, 2::-1])
    if msg.encoding == 'bgra8':
        return np.ascontiguousarray(arr[:, :, :3])
    if msg.encoding == 'mono8':
        return np.repeat(arr, 3, axis=2)
    return np.ascontiguousarray(arr)


def bgr_to_msg(bgr: np.ndarray, header) -> Image:
    msg = Image()
    msg.header = header
    msg.height, msg.width = bgr.shape[:2]
    msg.encoding = 'bgr8'
    msg.is_bigendian = 0
    msg.step = msg.width * 3
    msg.data = bgr.tobytes()
    return msg


class ColorDetector(Node):
    def __init__(self):
        super().__init__('color_detector')
        self.declare_parameter('camera_x', 0.4)
        self.declare_parameter('camera_y', 0.0)
        self.declare_parameter('camera_z', 1.2)
        self.declare_parameter('plane_z', 0.475)  # top face of a cube on the 0.4 m table
        self.declare_parameter('min_area', 150.0)
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('info_topic', '/camera/camera_info')

        p = self.get_parameter
        self.cam = Camera(x=p('camera_x').value, y=p('camera_y').value, z=p('camera_z').value)
        self.plane_z = p('plane_z').value
        self.min_area = p('min_area').value
        self.have_info = False

        self.create_subscription(CameraInfo, p('info_topic').value, self._on_info, 10)
        self.create_subscription(Image, p('image_topic').value, self._on_image,
                                 qos_profile_sensor_data)
        self.pub_img = self.create_publisher(Image, '/camera/detections_image', 10)
        self.pub_det = self.create_publisher(String, '/inspector/detections', 10)
        self.get_logger().info('colour detector ready (waiting for camera images)')

    def _on_info(self, msg: CameraInfo):
        if self.have_info or msg.k[0] == 0.0:
            return
        self.cam.fx, self.cam.fy, self.cam.cx, self.cam.cy = msg.k[0], msg.k[4], msg.k[2], msg.k[5]
        self.have_info = True
        self.get_logger().info(f'intrinsics from camera_info: fx={self.cam.fx:.1f}')

    def _on_image(self, msg: Image):
        try:
            bgr = image_to_bgr(msg)
        except ValueError as e:
            self.get_logger().error(str(e), throttle_duration_sec=5.0)
            return
        dets = detect_colors(bgr, self.min_area)
        world = {i: pixel_to_world(d.u, d.v, self.cam, self.plane_z) for i, d in enumerate(dets)}
        objs = [{'color': d.color, 'u': round(d.u, 1), 'v': round(d.v, 1), 'area': d.area,
                 'x': round(world[i][0], 4), 'y': round(world[i][1], 4),
                 'z': round(world[i][2], 4)} for i, d in enumerate(dets)]
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.pub_det.publish(String(data=json.dumps(
            {'stamp': stamp, 'frame': 'world', 'objects': objs})))
        self.pub_img.publish(bgr_to_msg(annotate(bgr, dets, world), msg.header))


def main(args=None):
    rclpy.init(args=args)
    node = ColorDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
