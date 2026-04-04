import math
from typing import List, Dict
from sentinel.models import RobotState

class BoidsController:
    def __init__(self, sep_radius=1.0, align_radius=2.0, coh_radius=2.0):
        self.sep_radius = sep_radius
        self.align_radius = align_radius
        self.coh_radius = coh_radius
        
        # weights
        self.w_sep = 2.0
        self.w_align = 1.0
        self.w_coh = 1.0
        
        self.max_speed = 5.0

    def compute_velocities(self, local_state: RobotState, neighbors: List[RobotState]) -> Dict[str, float]:
        """Reads local and neighbor state, outputs wheel velocities."""
        
        # If no neighbors, just move forward slowly
        if not neighbors:
            return {"left_wheel_motor": 2.0, "right_wheel_motor": 2.0}

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
                sep_vec[0] += dx / dist
                sep_vec[1] += dy / dist
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
        
        if sep_count > 0:
            sep_vec = [sep_vec[0]/sep_count, sep_vec[1]/sep_count]
            desired_v[0] += sep_vec[0] * self.w_sep
            desired_v[1] += sep_vec[1] * self.w_sep
            
        if align_count > 0:
            align_vec = [align_vec[0]/align_count, align_vec[1]/align_count]
            desired_v[0] += align_vec[0] * self.w_align
            desired_v[1] += align_vec[1] * self.w_align
            
        if coh_count > 0:
            center_of_mass = [center_of_mass[0]/coh_count, center_of_mass[1]/coh_count]
            coh_vec = [center_of_mass[0] - my_x, center_of_mass[1] - my_y]
            # normalize cohesion vector so it doesn't overpower
            coh_dist = math.hypot(coh_vec[0], coh_vec[1])
            if coh_dist > 0:
                coh_vec = [coh_vec[0]/coh_dist, coh_vec[1]/coh_dist]
            desired_v[0] += coh_vec[0] * self.w_coh
            desired_v[1] += coh_vec[1] * self.w_coh
            
        # Target heading
        target_heading = math.atan2(desired_v[1], desired_v[0])
        v_mag = math.hypot(desired_v[0], desired_v[1])
        
        # P-controller to steer diff drive toward target heading
        heading_error = target_heading - local_state.heading
        # Normalize angle to -pi to pi
        heading_error = (heading_error + math.pi) % (2 * math.pi) - math.pi
        
        # Simple mixing: forward speed + turn speed
        base_speed = min(v_mag, self.max_speed)
        
        # if heading error is large, prioritize turning in place
        if abs(heading_error) > math.pi / 2:
            base_speed = 0.5 # slow forward
            
        turn_speed = heading_error * 5.0 # Kp
        
        wheel_left = base_speed - turn_speed
        wheel_right = base_speed + turn_speed
        
        return {
            "left_wheel_motor": wheel_left,
            "right_wheel_motor": wheel_right
        }
