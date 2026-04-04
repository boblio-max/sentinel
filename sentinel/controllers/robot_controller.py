from sentinel.backends.base import Backend
from sentinel.bus import SwarmBus
from sentinel.models import RobotState
from sentinel.controllers.boids import BoidsController
from typing import Dict, Any
import math

class RobotController:
    def __init__(self, robot_id: int, backend: Backend, swarm_bus: SwarmBus):
        self.id = robot_id
        self.backend = backend
        self.bus = swarm_bus
        self.boids = BoidsController()

    def get_heading(self, orientation_quat) -> float:
        """Approximates 2D heading from quaternion since we only care about Z-axis rotation."""
        # mujoco uses (w, x, y, z)
        w, x, y, z = orientation_quat
        # Euler yaw angle calculation from quaternion
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        return math.atan2(t3, t4)

    def step(self):
        """Standard swarm tick."""
        # 1. Read local state
        sensor_data = self.backend.get_sensor_data()
        
        # Parse state
        pos = sensor_data["qpos"]
        vel = sensor_data["qvel"]
        
        # Assuming floating base has 7 pos (pos3, quat4) and 6 vel (lin3, ang3), and wheels follow.
        x, y = pos[0], pos[1]
        heading = self.get_heading(pos[3:7])
        vx, vy = vel[0], vel[1]
        
        my_state = RobotState(
            id=self.id,
            position=(x, y),
            heading=heading,
            velocity=(vx, vy)
        )
        
        # 2. Publish local state to SwarmBus
        self.bus.publish(self.id, my_state)
        
        # 3. Get neighbors
        neighbors = self.bus.get_neighbors(self.id, radius=5.0)
        
        # 4. Run swarm algorithm
        joint_commands = self.boids.compute_velocities(my_state, neighbors)
        
        # 5. Apply commands
        self.backend.set_joints(joint_commands)
