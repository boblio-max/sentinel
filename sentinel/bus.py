from typing import List, Dict
import math
from sentinel.models import RobotState

class SwarmBus:
    def __init__(self, shared_dict: Dict[int, RobotState]):
        self._state_map = shared_dict

    def publish(self, robot_id: int, state: RobotState) -> None:
        self._state_map[robot_id] = state

    def get_neighbors(self, robot_id: int, radius: float) -> List[RobotState]:
        me = self._state_map.get(robot_id)
        if not me:
            return []
            
        neighbors = []
        # _state_map is a dict proxy if multiprocessing, so we iterate items()
        for r_id, state in self._state_map.items():
            if r_id == robot_id:
                continue
            dist = math.hypot(me.position[0] - state.position[0], me.position[1] - state.position[1])
            if dist <= radius:
                neighbors.append(state)
        return neighbors
