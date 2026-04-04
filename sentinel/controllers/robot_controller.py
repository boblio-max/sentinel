from sentinel.backends.base import Backend
from typing import Dict, Any

class RobotController:
    def __init__(self, robot_id: int, backend: Backend):
        self.id = robot_id
        self.backend = backend

    def step(self, joint_commands: Dict[str, float]):
        """
        Takes explicit joint commands to verify functionality.
        """
        # Read local state
        local_state = self.backend.get_sensor_data()
        
        # Apply commands
        self.backend.set_joints(joint_commands)
