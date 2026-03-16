import time
from typing import Dict, Union, List
from sentinel import Node, NodeResult

# Optional Hardware Support
try:
    from adafruit_pca9685 import PCA9685
    import board
    import busio
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False

class PCA9685Manager:
    _instance = None
    _is_initialized = False
    
    @classmethod
    def get(cls):
        if not HAS_HARDWARE:
            return None
        if not cls._is_initialized:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                cls._instance = PCA9685(i2c)
                cls._instance.frequency = 50
                cls._is_initialized = True
            except Exception as e:
                print(f"[Sentinel Hardware] Warning: PCA9685 init failed: {e}. Falling back to SIMULATION.")
                cls._instance = None
        return cls._instance

def angle_to_pulse(angle: float) -> int:
    """Convert 0-180 degree angle to PCA9685 pulse 150-600 range."""
    angle = max(0, min(180, angle))
    pulse = int(150 + (angle / 180.0) * (600 - 150))
    # PCA9685 duty_cycle expects 0-65535, so 4096 range (0-4095) * 16 is close enough, 
    # but adafruit library takes 0-0xFFFF
    # The actual calculation for adafruit-circuitpython-pca9685 `duty_cycle` property:
    # 4096 precision. So pulse / 4096 * 65535
    return int((pulse / 4096.0) * 65535)

def pulse_for_print(angle: float) -> int:
    angle = max(0, min(180, angle))
    return int(150 + (angle / 180.0) * (600 - 150))

class ArmNode(Node):
    BUILT_IN_POSES = {
        "home": {0: 90, 1: 90, 2: 90, 3: 90},
        "rest": {0: 90, 1: 180, 2: 0, 3: 90},
        "extend": {0: 90, 1: 0, 2: 0, 3: 90},
        "pickup": {0: 90, 1: 30, 2: 30, 3: 90}
    }

    def __init__(self, joint: int = None, angle: float = None, positions: Dict[int, float] = None, pose: str = None, gripper: str = None, gripper_channel: int = 3):
        super().__init__(name="Arm")
        self.description = "Control PCA9685 servo arm."
        self.positions = positions or {}
        
        if joint is not None and angle is not None:
            self.positions[joint] = angle
            
        if pose is not None:
            if pose in self.BUILT_IN_POSES:
                self.positions.update(self.BUILT_IN_POSES[pose])
            else:
                self.description = f"Invalid pose {pose}"
                
        if gripper is not None:
            if gripper == "open":
                self.positions[gripper_channel] = 0
            elif gripper == "close":
                self.positions[gripper_channel] = 180
            elif gripper == "half":
                self.positions[gripper_channel] = 90
                
        # To format name nicely
        if len(self.positions) == 1:
            j, a = next(iter(self.positions.items()))
            self.name = f"Arm(j:{j}={a}°)"
        elif pose:
            self.name = f"Arm(pose:{pose})"
        else:
            self.name = f"Arm({len(self.positions)} joints)"

    def execute(self, context: dict) -> NodeResult:
        if not self.positions:
            return self.ok(data={"status": "no_targets"})
            
        # Get target hardware
        pca = None if context.get("simulation_mode") else PCA9685Manager.get()
        
        # Read current state from context to show nice SIM transition output
        if "_arm_state" not in context:
            context["_arm_state"] = {}
            
        applied = {}
        for joint, angle in self.positions.items():
            prev = context["_arm_state"].get(joint, "?")
            
            if pca:
                try:
                    pulse_val = angle_to_pulse(angle)
                    pca.channels[joint].duty_cycle = pulse_val
                except Exception as e:
                    return self.fail(f"PCA9685 Write Error on joint {joint}: {e}")
            else:
                print(f"[Sentinel SIM] Joint {joint}: {prev}° → {angle}°  (pulse={pulse_for_print(angle)})")
                
            context["_arm_state"][joint] = angle
            applied[joint] = angle
            
        return self.ok(data={"arm_positions": applied})


class ArmSequenceNode(Node):
    def __init__(self, sequence: List[Dict[int, float]], delay: float):
        super().__init__(name=f"ArmSequence({len(sequence)} steps)")
        self.description = "Run a chronological sequence of arm positions with a delay between them."
        self.sequence = sequence
        self.delay = delay

    def execute(self, context: dict) -> NodeResult:
        pca = None if context.get("simulation_mode") else PCA9685Manager.get()
        if "_arm_state" not in context:
            context["_arm_state"] = {}

        for i, step in enumerate(self.sequence):
            for joint, angle in step.items():
                prev = context["_arm_state"].get(joint, "?")
                if pca:
                    try:
                        pulse_val = angle_to_pulse(angle)
                        pca.channels[joint].duty_cycle = pulse_val
                    except Exception as e:
                        return self.fail(f"Sequence Step {i} failed on joint {joint}: {e}")
                else:
                    print(f"[Sentinel SIM] Seq[{i}] Joint {joint}: {prev}° → {angle}°  (pulse={pulse_for_print(angle)})")
                
                context["_arm_state"][joint] = angle
                
            if not context.get("simulation_mode"):
                time.sleep(self.delay)
            else:
                print(f"[Sentinel SIM] Seq[{i}] Delay {self.delay}s")
                
        return self.ok(data={"steps_completed": len(self.sequence)})
