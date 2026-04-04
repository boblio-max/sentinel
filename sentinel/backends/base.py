from abc import ABC, abstractmethod
from typing import Dict, Any

class Backend(ABC):
    @abstractmethod
    def get_sensor_data(self) -> Dict[str, Any]:
        """Returns position, velocity, proximity, etc."""
        pass

    @abstractmethod
    def set_joints(self, commands: Dict[str, float]) -> None:
        """Applies joint velocities/positions to the robot.
        commands is a dictionary mapping joint names to target velocities.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        pass
