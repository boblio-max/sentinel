from sentinel import Node, NodeResult

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False

class GPIONode(Node):
    def __init__(self, pin: int, state: int):
        super().__init__(name=f"GPIO(pin:{pin}={state})")
        self.description = "Set GPIO pin HIGH or LOW."
        self.pin = pin
        self.state = 1 if state else 0

    def execute(self, context: dict) -> NodeResult:
        if context.get("simulation_mode") or not HAS_GPIO:
            state_str = "HIGH" if self.state == 1 else "LOW"
            print(f"[Sentinel SIM] GPIO Pin {self.pin} set to {state_str}")
            return self.ok(data={"pin": self.pin, "state": self.state})
            
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.HIGH if self.state == 1 else GPIO.LOW)
        except Exception as e:
            return self.fail(f"GPIO Error on pin {self.pin}: {e}")
            
        return self.ok(data={"pin": self.pin, "state": self.state})
