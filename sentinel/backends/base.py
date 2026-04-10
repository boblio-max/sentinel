from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from sentinel.models import SensorReading, JointCommands


class Backend(ABC):
    """
    Abstract base class for all robot backends (sim or real).
    This interface ensures that a RobotController works identically
    whether controlling a simulated or real robot.
    """
    
    def __init__(self, robot_id: int):
        self.robot_id = robot_id
        self.running = False

    @abstractmethod
    def initialize(self) -> None:
        """Initialize hardware/simulation. Called once at startup."""
        pass

    @abstractmethod
    def get_sensor_data(self) -> SensorReading:
        """
        Returns current sensor reading from the robot.
        For sim: query physics engine state.
        For real: read from hardware I/O.
        """
        pass

    @abstractmethod
    def set_joints(self, commands: JointCommands) -> None:
        """
        Apply joint commands to the robot.
        For sim: set target velocities/positions in physics engine.
        For real: send PWM signals to servo driver.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset robot to initial state."""
        pass

    @abstractmethod
    def step(self, dt: float = 0.001) -> None:
        """
        Advance the robot by one time step dt (seconds).
        For sim: call physics step. 
        For real: this may be a no-op (hardware steps independently).
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean shutdown: stop motors, close connections."""
        pass

    def is_running(self) -> bool:
        return self.running
