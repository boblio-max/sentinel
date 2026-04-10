import mujoco
from mujoco import viewer
import time
from typing import Dict, Any
from .base import Backend
from sentinel.models import SensorReading, JointCommands
import math


class SimBackend(Backend):
    """PyBullet-based physics simulation backend."""
    
    def __init__(self, robot_id: int, xml_path: str, headless: bool = False, start_pos: tuple = None):
        super().__init__(robot_id)
        self.xml_path = xml_path
        self.headless = headless
        self.model = None
        self.data = None
        self.viewer = None
        self.actuator_name_to_id = {}
        self.start_pos = start_pos or (0, 0, 0.1)
        
    def initialize(self) -> None:
        """Load model and initialize MuJoCo."""
        self.model = mujoco.MjModel.from_xml_path(self.xml_path)
        self.data = mujoco.MjData(self.model)
        
        # Set start position (assuming floating base at qpos[0..2])
        if self.start_pos and len(self.start_pos) >= 2:
            self.data.qpos[0] = self.start_pos[0]
            self.data.qpos[1] = self.start_pos[1]
            if len(self.start_pos) >= 3:
                self.data.qpos[2] = self.start_pos[2]
        
        # Launch viewer unless headless
        if not self.headless:
            self.viewer = viewer.launch_passive(self.model, self.data)
        
        # Map actuator names
        self.actuator_name_to_id = {}
        for i in range(self.model.nu):
            name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            if name:
                self.actuator_name_to_id[name] = i
        
        self.running = True
        
    def get_sensor_data(self) -> SensorReading:
        """Extract sensor reading from MuJoCo state."""
        # Position and orientation of root (0)
        root_xpos = self.data.xpos[0].copy()
        root_xquat = self.data.xquat[0].copy()  # (qx, qy, qz, qw)
        
        # Linear and angular velocity of root
        root_linvel = self.data.qvel[:3].copy() if len(self.data.qvel) >= 3 else [0, 0, 0]
        root_angvel = self.data.qvel[3:6].copy() if len(self.data.qvel) >= 6 else [0, 0, 0]
        
        # Extract joint data
        joint_positions = {}
        joint_velocities = {}
        for i in range(self.model.nq):
            dof_spec = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_DOF, i)
            if dof_spec:
                joint_positions[dof_spec] = float(self.data.qpos[i])
        
        for i in range(self.model.nv):
            vel_name = mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
            if vel_name:
                joint_velocities[vel_name] = float(self.data.qvel[i])
        
        # Convert quaternion from MuJoCo (qx, qy, qz, qw) to (x, y, z, w)
        quat_xyzw = tuple(root_xquat)
        
        return SensorReading(
            position=tuple(root_xpos),
            orientation=quat_xyzw,
            linear_velocity=tuple(root_linvel),
            angular_velocity=tuple(root_angvel),
            joint_positions=joint_positions,
            joint_velocities=joint_velocities
        )

    def set_joints(self, commands: JointCommands) -> None:
        """Apply velocity or position commands to actuators."""
        # Apply velocity commands
        for name, velocity in commands.velocities.items():
            if name in self.actuator_name_to_id:
                idx = self.actuator_name_to_id[name]
                self.data.ctrl[idx] = velocity
        
        # Position commands would typically use position servo gains;
        # for now, we only support velocity control
                
    def step(self, dt: float = 0.001) -> None:
        """Advance simulation by one step."""
        mujoco.mj_step(self.model, self.data, nstep=int(dt / self.model.opt.timestep))
        if self.viewer:
            self.viewer.sync()

    def reset(self) -> None:
        """Reset to initial state."""
        if self.model and self.data:
            mujoco.mj_resetData(self.model, self.data)
            if self.start_pos:
                self.data.qpos[0] = self.start_pos[0]
                self.data.qpos[1] = self.start_pos[1]
                if len(self.start_pos) >= 3:
                    self.data.qpos[2] = self.start_pos[2]
            if self.viewer:
                self.viewer.sync()
    
    def shutdown(self) -> None:
        """Clean shutdown."""
        if self.viewer:
            self.viewer.close()
        self.running = False
