"""Operator-facing task manager.

Listens on /inspector/command (std_msgs/String, JSON) and publishes the robot state on
/inspector/status (std_msgs/String, JSON, 2 Hz). The pick-and-place steps themselves are
inherited from PickPlaceNode.

Commands:
  {"action": "start", "colors": ["red", "green"]}   sort these cubes, in this order
  {"action": "stop"}                                finish the current cube, then stop
  {"action": "reset_slots"}                         pedestal was emptied by hand
"""
import json
import sys
import time
from collections import deque

import rclpy
from rclpy.clock import Clock, ClockType
from std_msgs.msg import String

from inspector_pick_place.pick_place_node import (
    GRIPPER_OPEN, HOME, PickPlaceError, PickPlaceNode)
from inspector_pick_place.task_geometry import PLACE_SLOTS

KNOWN_COLOURS = ('red', 'green', 'blue')


class TaskManager(PickPlaceNode):
    def __init__(self):
        super().__init__()
        self.state = 'starting'
        self.current = None
        self.step = ''
        self.done, self.failed, self.skipped = [], [], []
        self.next_slot = 0
        self.stop_flag = False
        self.queue = deque()
        self.log = deque(maxlen=60)

        self.status_pub = self.create_publisher(String, '/inspector/status', 10)
        self.create_subscription(String, '/inspector/command', self._on_command, 10)
        # wall-clock timer so status keeps flowing even if the simulation is paused
        self.create_timer(0.5, self._publish_status,
                          clock=Clock(clock_type=ClockType.SYSTEM_TIME))

    # ------------------------------------------------------------ status / log
    def _note(self, text, level='info'):
        self.log.append({'t': time.strftime('%H:%M:%S'), 'level': level, 'msg': text})
        logger = self.get_logger()
        (logger.error if level == 'error' else logger.warn if level == 'warn' else logger.info)(text)

    def _publish_status(self):
        payload = {
            'state': self.state,
            'current': self.current,
            'step': self.step,
            'done': self.done,
            'failed': self.failed,
            'skipped': self.skipped,
            'next_slot': self.next_slot,
            'slots_total': len(PLACE_SLOTS),
            'log': list(self.log)[-30:],
        }
        self.status_pub.publish(String(data=json.dumps(payload)))

    # ------------------------------------------------------------ commands
    def _on_command(self, msg):
        try:
            cmd = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        action = cmd.get('action')
        if action == 'start':
            if self.state != 'ready' or self.queue:
                self._note(f'start ignored, robot is {"busy" if self.queue else self.state}', 'warn')
                return
            colours = []
            for c in cmd.get('colors', []):
                if c in KNOWN_COLOURS and c not in colours:
                    colours.append(c)
            if not colours:
                self._note('start ignored, no valid colours given', 'warn')
                return
            self.queue.append(colours)
        elif action == 'stop':
            if self.state == 'running':
                self.stop_flag = True
                self._note('stop requested, finishing the current object', 'warn')
        elif action == 'reset_slots':
            if self.state == 'ready':
                self.next_slot = 0
                self._note('pedestal slots reset')
        else:
            self._note(f'unknown command: {action}', 'warn')

    # ------------------------------------------------------------ step labels
    def moveit_to(self, joints, label):
        self.step = f'moving: {label}'
        super().moveit_to(joints, label)

    def linear_move(self, p0, p1, label):
        self.step = label
        super().linear_move(p0, p1, label)

    def gripper(self, opening):
        self.step = 'opening gripper' if opening > 0 else 'closing gripper'
        super().gripper(opening)

    # ------------------------------------------------------------ sorting run
    def _recover(self):
        try:
            self.gripper(GRIPPER_OPEN)
            self.moveit_to(HOME, 'home (recovery)')
        except PickPlaceError as e:
            self._note(f'recovery failed: {e}', 'error')

    def _execute(self, colours):
        self.state = 'running'
        self.stop_flag = False
        self.done, self.failed, self.skipped = [], [], []
        self._note('sorting started: ' + ', '.join(colours))
        for colour in colours:
            if self.stop_flag:
                self._note(f'stopped before {colour}', 'warn')
                break
            if self.next_slot >= len(PLACE_SLOTS):
                self._note('pedestal is full, empty it and reset the slots', 'error')
                break
            self.current = colour
            self._note(f'picking {colour}')
            try:
                placed = self.pick_and_place(colour, self.next_slot)
            except PickPlaceError as e:
                self._note(f'{colour} failed: {e}', 'error')
                self.failed.append(colour)
                self._recover()
                continue
            if placed:
                self.done.append(colour)
                self.next_slot += 1
                self._note(f'{colour} placed in slot {self.next_slot}')
            else:
                self.skipped.append(colour)
                self._note(f'{colour} not found or not reachable, skipped', 'warn')
        self.current = None
        self.step = ''
        self.state = 'ready'
        self._note(f'finished: {len(self.done)} sorted, {len(self.failed)} failed, '
                   f'{len(self.skipped)} skipped')

    def serve(self):
        try:
            self._note('waiting for simulation, MoveIt and camera')
            self.wait_for_system()
            self._sleep(float(self.get_parameter('start_delay').value))
            self.add_obstacles()
            self.gripper(GRIPPER_OPEN)
            self.moveit_to(HOME, 'home')
            self.step = ''
            self.state = 'ready'
            self._note('ready')
        except PickPlaceError as e:
            self.state = 'error'
            self.step = ''
            self._note(f'startup failed: {e}', 'error')
        while rclpy.ok():
            if self.queue:
                self._execute(self.queue.popleft())
            else:
                rclpy.spin_once(self, timeout_sec=0.1)


def main(args=None):
    rclpy.init(args=args)
    node = TaskManager()
    try:
        node.serve()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
