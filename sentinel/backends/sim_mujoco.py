import mujoco
from mujoco import viewer
import time
from typing import Dict, Any
from .base import Backend
import math

class SimBackend(Backend):
    def __init__(self, xml_path: str):
        self.model = mujoco.MjModel.from_xml_path(xml_path)
        self.data = mujoco.MjData(self.model)
        
        # Launch viewer (this stays open as a passive window)
        self.viewer = viewer.launch_passive(self.model, self.data)
        
        # Map actuator names to ID for easy setting
        self.actuator_name_to_id = {}
        for i in range(self.model.nu):
            name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            if name:
                self.actuator_name_to_id[name] = i
                
    def get_sensor_data(self) -> Dict[str, Any]:
        """Returns position and simplified sensor data"""
        return {
            "qpos": self.data.qpos.copy(),
            "qvel": self.data.qvel.copy()
        }

    def set_joints(self, commands: Dict[str, float]) -> None:
        """Applies velocities to explicit velocity actuators via actuator names"""
        for name, velocity in commands.items():
            if name in self.actuator_name_to_id:
                idx = self.actuator_name_to_id[name]
                # In MuJoCo, for velocity actuators, the control signal is the target velocity.
                self.data.ctrl[idx] = velocity
                
    def step_simulation(self):
        """Advances simulation by one step and updates viewer."""
        mujoco.mj_step(self.model, self.data)
        self.viewer.sync()

    def reset(self) -> None:
        mujoco.mj_resetData(self.model, self.data)
        self.viewer.sync()
