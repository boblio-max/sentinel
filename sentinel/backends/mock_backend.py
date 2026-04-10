"""
MockBackend: A simple backend for testing without simulation or hardware.
Useful for unit tests and verifying the Backend interface contract.
"""

from typing import Dict, Any
from .base import Backend
from sentinel.models import SensorReading, JointCommands
import math
import time


class MockBackend(Backend):
    """
    Simple mock backend for testing.
    Simulates a robot with constant circular motion.
    """
    
    def __init__(self, robot_id: int = 0):
        super().__init__(robot_id)
        self.position = [0.0, 0.0, 0.0]
        self.orientation = [0.0, 0.0, 0.0, 1.0]  # (x, y, z, w)
        self.linear_velocity = [0.0, 0.0, 0.0]
        self.angular_velocity = [0.0, 0.0, 0.0]
        self.joint_positions = {"left_wheel_motor": 0.0, "right_wheel_motor": 0.0}
        self.joint_velocities = {"left_wheel_motor": 0.0, "right_wheel_motor": 0.0}
        self.start_time = None
        self._step_count = 0
    
    def initialize(self) -> None:
        """Initialize mock backend."""
        self.start_time = time.time()
        self.running = True
    
    def get_sensor_data(self) -> SensorReading:
        """Return mock sensor data with circular motion."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        # Simulate circular motion with 10-second period
        t = (elapsed * 2 * math.pi) / 10.0
        
        # Position on a circle of radius 2m
        x = 2.0 * math.cos(t)
        y = 2.0 * math.sin(t)
        z = 0.1
        
        # Heading tangent to circle
        heading = t + math.pi / 2
        
        # Quaternion from yaw
        quat = self._yaw_to_quaternion(heading)
        
        # Velocity tangent to circle
        v_mag = 2.0  # m/s
        vx = -v_mag * math.sin(t)
        vy = v_mag * math.cos(t)
        
        # Angular velocity
        wx, wy = 0.0, 0.0
        wz = v_mag / 2.0  # Going around 2m radius circle
        
        reading = SensorReading(
            position=(x, y, z),
            orientation=quat,
            linear_velocity=(vx, vy, 0.0),
            angular_velocity=(wx, wy, wz),
            joint_positions=self.joint_positions.copy(),
            joint_velocities=self.joint_velocities.copy()
        )
        
        return reading
    
    def set_joints(self, commands: JointCommands) -> None:
        """Accept joint commands and store them."""
        for name, velocity in commands.velocities.items():
            if name in self.joint_velocities:
                self.joint_velocities[name] = velocity
    
    def step(self, dt: float = 0.001) -> None:
        """Simulate one time step."""
        self._step_count += 1
    
    def reset(self) -> None:
        """Reset to initial state."""
        self.position = [0.0, 0.0, 0.0]
        self.orientation = [0.0, 0.0, 0.0, 1.0]
        self.linear_velocity = [0.0, 0.0, 0.0]
        self.angular_velocity = [0.0, 0.0, 0.0]
        self.joint_velocities = {"left_wheel_motor": 0.0, "right_wheel_motor": 0.0}
        self._step_count = 0
    
    def shutdown(self) -> None:
        """Shutdown mock backend."""
        self.running = False
    
    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> tuple:
        """Convert yaw angle to quaternion (x, y, z, w)."""
        angle = yaw / 2.0
        x = 0.0
        y = 0.0
        z = math.sin(angle)
        w = math.cos(angle)
        return (x, y, z, w)
