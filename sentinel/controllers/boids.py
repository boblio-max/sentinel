import math
from typing import List, Dict, Optional, Tuple
from sentinel.models import RobotState
from sentinel import config

class BoidsController:
    def __init__(self, 
                 sep_radius=config.DEFAULT_SEP_RADIUS, 
                 align_radius=config.DEFAULT_ALIGN_RADIUS, 
                 coh_radius=config.DEFAULT_COH_RADIUS):
        self.sep_radius = sep_radius
        self.align_radius = align_radius
        self.coh_radius = coh_radius
        
        # weights
        self.w_sep = config.WEIGHT_SEPARATION
        self.w_align = config.WEIGHT_ALIGNMENT
        self.w_coh = config.WEIGHT_COHESION
        self.w_goal = config.DEFAULT_GOAL_WEIGHT
        
        self.max_speed = config.MAX_SPEED
        self.target_goal: Optional[Tuple[float, float]] = None

    def set_goal(self, goal: Optional[Tuple[float, float]]) -> None:
        """Set a global target goal for the swarm to move towards."""
        self.target_goal = goal

    def compute_velocities(self, local_state: RobotState, neighbors: List[RobotState]) -> Dict[str, float]:
        """Reads local and neighbor state, outputs wheel velocities."""
        
        sep_vec = [0.0, 0.0]
        align_vec = [0.0, 0.0]
        center_of_mass = [0.0, 0.0]
        
        sep_count = 0
        align_count = 0
        coh_count = 0
        
        my_x, my_y = local_state.position
        
        for n in neighbors:
            dx = my_x - n.position[0]
            dy = my_y - n.position[1]
            dist = math.hypot(dx, dy)
            
            if dist == 0:
                dist = 0.0001
                
            if dist < self.sep_radius:
                sep_vec[0] += dx / (dist * dist) # Inverse square for separation
                sep_vec[1] += dy / (dist * dist)
                sep_count += 1
                
            if dist < self.align_radius:
                align_vec[0] += n.velocity[0]
                align_vec[1] += n.velocity[1]
                align_count += 1
                
            if dist < self.coh_radius:
                center_of_mass[0] += n.position[0]
                center_of_mass[1] += n.position[1]
                coh_count += 1
                
        # Average vectors
        desired_v = [0.0, 0.0]
        
        # 1. Separation
        if sep_count > 0:
            desired_v[0] += sep_vec[0] * self.w_sep
            desired_v[1] += sep_vec[1] * self.w_sep
            
        # 2. Alignment
        if align_count > 0:
            align_vec = [align_vec[0]/align_count, align_vec[1]/align_count]
            desired_v[0] += align_vec[0] * self.w_align
            desired_v[1] += align_vec[1] * self.w_align
            
        # 3. Cohesion
        if coh_count > 0:
            center_of_mass = [center_of_mass[0]/coh_count, center_of_mass[1]/coh_count]
            coh_vec = [center_of_mass[0] - my_x, center_of_mass[1] - my_y]
            # normalize cohesion vector
            coh_dist = math.hypot(coh_vec[0], coh_vec[1])
            if coh_dist > 0:
                desired_v[0] += (coh_vec[0]/coh_dist) * self.w_coh
                desired_v[1] += (coh_vec[1]/coh_dist) * self.w_coh

        # 4. Goal Seeking
        if self.target_goal:
            goal_vec = [self.target_goal[0] - my_x, self.target_goal[1] - my_y]
            goal_dist = math.hypot(goal_vec[0], goal_vec[1])
            if goal_dist > 0:
                desired_v[0] += (goal_vec[0]/goal_dist) * self.w_goal
                desired_v[1] += (goal_vec[1]/goal_dist) * self.w_goal
            
        # If no intention (no neighbors + no goal), wander slowly
        if not neighbors and not self.target_goal:
            # Add a slight bias so they don't just sit still
            desired_v[0] += 0.5 * math.cos(local_state.heading)
            desired_v[1] += 0.5 * math.sin(local_state.heading)

        # Target heading from combined vectors
        target_heading = math.atan2(desired_v[1], desired_v[0])
        v_mag = math.hypot(desired_v[0], desired_v[1])
        
        # P-controller to steer diff drive toward target heading
        heading_error = target_heading - local_state.heading
        # Normalize angle to -pi to pi
        heading_error = (heading_error + math.pi) % (2 * math.pi) - math.pi
        
        # Simple mixing: forward speed + turn speed
        base_speed = min(v_mag, self.max_speed)
        
        # if heading error is large, prioritize turning in place
        if abs(heading_error) > math.pi / 3:
            base_speed *= 0.2
            
        turn_speed = heading_error * 5.0 # Kp for steering
        turn_speed = max(-config.MAX_TURN_SPEED, min(config.MAX_TURN_SPEED, turn_speed))
        
        wheel_left = base_speed - turn_speed
        wheel_right = base_speed + turn_speed
        
        return {
            "left_wheel_motor": wheel_left,
            "right_wheel_motor": wheel_right
        }
