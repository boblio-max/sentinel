import pybullet as p
import pybullet_data
from typing import Dict, Any
from .base import Backend
from sentinel.models import SensorReading, JointCommands
import math


class PyBulletBackend(Backend):
    """PyBullet-based physics simulation backend."""
    
    def __init__(self, robot_id: int, urdf_path: str, start_pos: tuple = (0, 0, 0.05), use_gui: bool = False):
        super().__init__(robot_id)
        self.urdf_path = urdf_path
        self.start_pos = start_pos
        self.use_gui = use_gui
        self.physics_client = None
        self.robot_id_pb = None
        self.plane_id = None
        self.joint_name_to_id = {}
        
    def initialize(self) -> None:
        """Connect to PyBullet and load robot URDF."""
        # Connect to PyBullet
        mode = p.GUI if self.use_gui else p.DIRECT
        self.physics_client = p.connect(mode)
        
        # Load environment
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        self.plane_id = p.loadURDF("plane.urdf")
        
        # Load robot
        start_orientation = p.getQuaternionFromEuler([0, 0, 0])
        self.robot_id_pb = p.loadURDF(self.urdf_path, self.start_pos, start_orientation)
        
        # Map joint names to IDs
        self.joint_name_to_id = {}
        num_joints = p.getNumJoints(self.robot_id_pb)
        for i in range(num_joints):
            info = p.getJointInfo(self.robot_id_pb, i)
            joint_name = info[1].decode('utf-8')
            self.joint_name_to_id[joint_name] = info[0]
        
        self.running = True
        
    def get_sensor_data(self) -> SensorReading:
        """Extract sensor reading from PyBullet state."""
        pos, ori = p.getBasePositionAndOrientation(self.robot_id_pb)
        lin_vel, ang_vel = p.getBaseVelocity(self.robot_id_pb)
        
        joint_states = p.getJointStates(self.robot_id_pb, list(self.joint_name_to_id.values()))
        
        joint_positions = {}
        joint_velocities = {}
        for name, j_idx in self.joint_name_to_id.items():
            # Find the state for this joint
            state = p.getJointState(self.robot_id_pb, j_idx)
            joint_positions[name] = float(state[0])
            joint_velocities[name] = float(state[1])
        
        # PyBullet returns quaternion as (x, y, z, w)
        return SensorReading(
            position=tuple(pos),
            orientation=tuple(ori),
            linear_velocity=tuple(lin_vel),
            angular_velocity=tuple(ang_vel),
            joint_positions=joint_positions,
            joint_velocities=joint_velocities
        )

    def set_joints(self, commands: JointCommands) -> None:
        """Apply velocity commands to joints."""
        for name, velocity in commands.velocities.items():
            if name in self.joint_name_to_id:
                j_id = self.joint_name_to_id[name]
                p.setJointMotorControl2(
                    bodyUniqueId=self.robot_id_pb,
                    jointIndex=j_id,
                    controlMode=p.VELOCITY_CONTROL,
                    targetVelocity=velocity,
                    force=2.0
                )
                
    def step(self, dt: float = 0.001) -> None:
        """Advance PyBullet simulation by one step."""
        p.stepSimulation()

    def reset(self) -> None:
        """Reset robot to initial state."""
        if self.physics_client is not None:
            p.resetBasePositionAndOrientation(self.robot_id_pb, self.start_pos, p.getQuaternionFromEuler([0, 0, 0]))
            p.resetBaseVelocity(self.robot_id_pb, [0, 0, 0], [0, 0, 0])
    
    def shutdown(self) -> None:
        """Clean shutdown: disconnect from PyBullet."""
        if self.physics_client is not None:
            p.disconnect(self.physics_client)
        self.running = False
