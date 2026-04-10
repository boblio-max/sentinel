# Sentinel: Swarm Intelligence Lab
"""
Sentinel enables full 10-robot swarm testing using only 1 physical robot.
The remaining 9 robots are simulated in high-fidelity physics environments.
All 10 robots run the same decentralized swarm algorithm as equal peers.
"""

from sentinel.models import RobotState, SensorReading, JointCommands
from sentinel.backends import Backend, MockBackend, MuJoCoBackend, PyBulletBackend, RealBackend
from sentinel.controllers.robot_controller import RobotController
from sentinel.bus import SwarmBus

__version__ = "0.1.0"

__all__ = [
    # Models
    "RobotState",
    "SensorReading",
    "JointCommands",
    # Backends
    "Backend",
    "MockBackend",
    "MuJoCoBackend",
    "PyBulletBackend",
    "RealBackend",
    # Controllers
    "RobotController",
    # Communication
    "SwarmBus",
]
