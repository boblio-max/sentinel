import time
from typing import Optional
from sentinel import Node, NodeResult

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class MotorNode(Node):
    def __init__(self, pin: int, speed: int, duration: float = None):
        """
        Speed 0-100. Duration in seconds (None for indefinite).
        """
        super().__init__(name=f"Motor(pin:{pin}, speed:{speed}%)")
        self.description = "Drive DC Motor via PWM."
        self.pin = pin
        self.speed = max(0, min(100, speed))
        self.duration = duration

    def execute(self, context: dict) -> NodeResult:
        if context.get("simulation_mode") or not HAS_GPIO:
            dur_str = f" for {self.duration}s" if self.duration else " indefinitely"
            print(f"[Sentinel SIM] Motor on pin {self.pin} running at {self.speed}%{dur_str}")
            if self.duration and not context.get("simulation_mode"):
                time.sleep(self.duration)
            return self.ok(data={"pin": self.pin, "speed": self.speed, "duration": self.duration})
            
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            pwm = GPIO.PWM(self.pin, 1000) # 1KHz
            pwm.start(self.speed)
            
            if self.duration:
                time.sleep(self.duration)
                pwm.stop()
                # we don't GPIO.cleanup() here to not ruin other nodes potentially,
                # though a full robot context might manage this better.
                
        except Exception as e:
            return self.fail(f"GPIO PWM Error on pin {self.pin}: {e}")
            
        return self.ok(data={"pin": self.pin, "speed": self.speed, "duration": self.duration})
