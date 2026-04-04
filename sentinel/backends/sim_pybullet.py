import pybullet as p
import pybullet_data
from typing import Dict, Any
from .base import Backend
import math

class SimBackend(Backend):
    def __init__(self, urdf_path: str, start_pos: tuple = (0, 0, 0.05)):
        # Connect to PyBullet (GUI mode for visualization)
        self.physics_client = p.connect(p.GUI)
        
        # Load environment
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        self.plane_id = p.loadURDF("plane.urdf")
        
        # Load Robot
        start_orientation = p.getQuaternionFromEuler([0, 0, 0])
        self.robot_id = p.loadURDF(urdf_path, start_pos, start_orientation)
        
        # Map joint names to IDs
        self.joint_name_to_id = {}
        num_joints = p.getNumJoints(self.robot_id)
        for i in range(num_joints):
            info = p.getJointInfo(self.robot_id, i)
            joint_name = info[1].decode('utf-8')
            self.joint_name_to_id[joint_name] = info[0]
            
    def get_sensor_data(self) -> Dict[str, Any]:
        """Returns position and simplified sensor data"""
        pos, ori = p.getBasePositionAndOrientation(self.robot_id)
        
        joint_states = p.getJointStates(self.robot_id, list(self.joint_name_to_id.values()))
        joint_velocities = {name: state[1] for name, state in zip(self.joint_name_to_id.keys(), joint_states)}
        
        return {
            "position": pos,
            "orientation": ori,
            "joint_velocities": joint_velocities
        }

    def set_joints(self, commands: Dict[str, float]) -> None:
        """Applies velocities to joints."""
        for name, velocity in commands.items():
            if name in self.joint_name_to_id:
                j_id = self.joint_name_to_id[name]
                p.setJointMotorControl2(
                    bodyUniqueId=self.robot_id,
                    jointIndex=j_id,
                    controlMode=p.VELOCITY_CONTROL,
                    targetVelocity=velocity,
                    force=2.0 # Allow some max force
                )
                
    def step_simulation(self):
        """Advances simulation by one step."""
        p.stepSimulation()

    def reset(self) -> None:
        p.resetSimulation()
        p.setGravity(0, 0, -9.81)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.loadURDF("plane.urdf")
