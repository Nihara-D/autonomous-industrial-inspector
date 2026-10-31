"""Republishes the annotated detector image as JPEG so it can be shown in the web app.

Subscribes : /camera/detections_image            (sensor_msgs/Image, bgr8)
Publishes  : /camera/detections_image/compressed (sensor_msgs/CompressedImage)
"""
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image


def encode_jpeg(msg: Image, quality: int) -> bytes:
    frame = np.frombuffer(bytes(msg.data), np.uint8).reshape(msg.height, msg.step)
    frame = frame[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
    ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError('jpeg encoding failed')
    return buf.tobytes()


class CameraJpeg(Node):
    def __init__(self):
        super().__init__('camera_jpeg')
        self.declare_parameter('max_rate_hz', 5.0)
        self.declare_parameter('quality', 80)
        self.min_gap = 1.0 / float(self.get_parameter('max_rate_hz').value)
        self.quality = int(self.get_parameter('quality').value)
        self.last = 0.0
        self.pub = self.create_publisher(CompressedImage, '/camera/detections_image/compressed', 1)
        self.create_subscription(Image, '/camera/detections_image', self._on_image, 1)

    def _on_image(self, msg: Image):
        now = time.monotonic()
        if now - self.last < self.min_gap or msg.encoding != 'bgr8':
            return
        self.last = now
        out = CompressedImage()
        out.header = msg.header
        out.format = 'jpeg'
        out.data = encode_jpeg(msg, self.quality)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = CameraJpeg()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
