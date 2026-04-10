from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, Optional
import numpy as np

@dataclass
class RobotState:
    """Published state of a robot in the swarm."""
    id: int
    position: Tuple[float, float]
    heading: float
    velocity: Tuple[float, float]
    timestamp: float = 0.0


@dataclass
class SensorReading:
    """Raw sensor data from a backend (sim or real)."""
    position: Tuple[float, float, float]  # (x, y, z) in world frame
    orientation: Tuple[float, float, float, float]  # (x, y, z, w) quaternion
    linear_velocity: Tuple[float, float, float]  # (vx, vy, vz)
    angular_velocity: Tuple[float, float, float]  # (wx, wy, wz)
    joint_positions: Dict[str, float] = field(default_factory=dict)
    joint_velocities: Dict[str, float] = field(default_factory=dict)
    proximity_sensors: Dict[str, float] = field(default_factory=dict)
    imu_accel: Optional[Tuple[float, float, float]] = None
    imu_gyro: Optional[Tuple[float, float, float]] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JointCommands:
    """Commands to send to actuators."""
    velocities: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, float] = field(default_factory=dict)
    torques: Dict[str, float] = field(default_factory=dict)
    extra_data: Dict[str, Any] = field(default_factory=dict)
