from dataclasses import dataclass
from typing import Tuple

@dataclass
class RobotState:
    id: int
    position: Tuple[float, float]
    heading: float
    velocity: Tuple[float, float]
