"""
RobotController: Unified controller for any robot (sim or real).
Runs the same swarm algorithm regardless of backend.
"""

from sentinel.backends.base import Backend
from sentinel.bus import SwarmBus
from sentinel.models import RobotState, JointCommands, SensorReading
from sentinel.controllers.boids import BoidsController
from typing import Tuple, Optional
import math
import time
import logging

logger = logging.getLogger(__name__)


class RobotController:
    """
    Unified controller for a single robot in the swarm.
    Works with any backend (SimBackend or RealBackend) transparently.
    """
    
    def __init__(self, robot_id: int, backend: Backend, swarm_bus: SwarmBus):
        """
        Args:
            robot_id: Unique ID in swarm (0-9)
            backend: Backend instance (sim or real)
            swarm_bus: Shared communication bus
        """
        self.id = robot_id
        self.backend = backend
        self.bus = swarm_bus
        self.boids = BoidsController()
        
        # State tracking
        self._last_state: Optional[RobotState] = None
        self._tick_count = 0
    
    @staticmethod
    def quaternion_to_yaw(quat: Tuple[float, float, float, float]) -> float:
        """
        Convert quaternion to yaw angle (2D heading).
        
        Quaternion format: (x, y, z, w) or (w, x, y, z); handles both.
        Returns yaw in radians [-π, π].
        """
        # Try to detect format: if first element is > 0.9, likely it's (w, x, y, z)
        if abs(quat[0]) > 0.5:
            # Likely (w, x, y, z) format (MuJoCo)
            w, x, y, z = quat
        else:
            # Likely (x, y, z, w) format (PyBullet)
            x, y, z, w = quat
        
        # Yaw from quaternion: atan2(2(wz + xy), 1 - 2(y² + z²))
        numerator = 2.0 * (w * z + x * y)
        denominator = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(numerator, denominator)
        
        return yaw
    
    @staticmethod
    def get_2d_velocity(lin_vel: Tuple[float, float, float], yaw: float) -> Tuple[float, float]:
        """
        Project 3D linear velocity onto 2D ground plane in robot's frame.
        For swarm purposes, we care about heading and forward speed only.
        """
        vx, vy, vz = lin_vel
        # In the world frame, (vx, vy) is the 2D velocity
        return (vx, vy)
    
    def initialize(self) -> None:
        """Initialize the backend (called once at startup)."""
        self.backend.initialize()
        logger.info(f"Robot {self.id} controller initialized")
    
    def shutdown(self) -> None:
        """Shutdown the backend (called once at shutdown)."""
        self.backend.shutdown()
        logger.info(f"Robot {self.id} controller shut down")
    
    def step(self, dt: float = 0.001) -> None:
        """
        Execute one control cycle:
        1. Read sensor data (position, orientation, velocity)
        2. Publish state to swarm bus
        3. Read neighbor states
        4. Run swarm algorithm (Boids)
        5. Execute motor commands
        """
        # 1. Read sensor data
        try:
            sensor_data = self.backend.get_sensor_data()
        except Exception as e:
            logger.error(f"Robot {self.id}: Failed to read sensors: {e}")
            return
        
        # 2. Parse sensor data into RobotState
        my_state = self._sensor_to_robot_state(sensor_data)
        self._last_state = my_state
        
        # 3. Publish to swarm bus
        self.bus.publish(self.id, my_state)
        
        # 4. Read neighbor states (within communication radius)
        neighbors = self.bus.get_neighbors(self.id, radius=5.0)
        
        # 5. Run swarm algorithm (Boids)
        try:
            wheel_velocities = self.boids.compute_velocities(my_state, neighbors)
        except Exception as e:
            logger.error(f"Robot {self.id}: Boids computation failed: {e}")
            return
        
        # 6. Convert velocities to JointCommands and apply
        joint_commands = self._velocities_to_joint_commands(wheel_velocities)
        try:
            self.backend.set_joints(joint_commands)
        except Exception as e:
            logger.error(f"Robot {self.id}: Failed to set joints: {e}")
        
        # 7. Step backend simulation (important for sim backends)
        try:
            self.backend.step(dt)
        except Exception as e:
            logger.error(f"Robot {self.id}: Backend step failed: {e}")
        
        self._tick_count += 1
    
    def _sensor_to_robot_state(self, sensor_data: SensorReading) -> RobotState:
        """Convert raw sensor reading to RobotState for swarm use."""
        # Extract position
        pos_x, pos_y = sensor_data.position[0], sensor_data.position[1]
        
        # Extract heading from orientation quaternion
        heading = self.quaternion_to_yaw(sensor_data.orientation)
        
        # Extract 2D velocity
        vel_2d = self.get_2d_velocity(sensor_data.linear_velocity, heading)
        
        state = RobotState(
            id=self.id,
            position=(pos_x, pos_y),
            heading=heading,
            velocity=vel_2d,
            timestamp=time.time()
        )
        
        return state
    
    def _velocities_to_joint_commands(self, wheel_velocities: dict) -> JointCommands:
        """
        Convert wheel velocity commands (from Boids) to JointCommands.
        
        Input: dict like {"left_wheel_motor": 2.0, "right_wheel_motor": 2.0}
        Output: JointCommands with velocities field populated
        """
        commands = JointCommands(
            velocities=wheel_velocities
        )
        return commands
    
    def get_state(self) -> Optional[RobotState]:
        """Get last known state of this robot."""
        return self._last_state
    
    def get_tick_count(self) -> int:
        """Get number of ticks executed."""
        return self._tick_count
