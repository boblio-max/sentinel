import time
import os
import math
import sys
from sentinel.backends.sim_mujoco import SimBackend
from sentinel.controllers.robot_controller import RobotController

def main():
    # Setup Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, "assets", "robot.xml")
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        sys.exit(1)
        
    print("Initializing MuJoCo Backend...")
    try:
        backend = SimBackend(xml_path=model_path)
    except Exception as e:
        print(f"Failed to initialize backend: {e}")
        sys.exit(1)
    
    # Setup Controller
    print("Initializing RobotController...")
    robot = RobotController(robot_id=0, backend=backend)
    
    # Main Loop
    print("Starting simulation loop... Press Ctrl+C to exit.")
    tick = 0
    try:
        start_time = time.time()
        while True:
            # MuJoCo time
            
            # Generate simple sinusoidal movement for testing
            # Drive the wheels back and forth
            speed = 10.0 * math.sin(tick * 0.02)
            commands = {
                "left_wheel_motor": speed,
                "right_wheel_motor": -speed # Opposite direction for spinning
            }
            
            robot.step(commands)
            backend.step_simulation()
            
            time_until_next_step = backend.model.opt.timestep - (time.time() - start_time)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)
            start_time = time.time()
            
            tick += 1
            if tick > 2000: # script will auto terminate after a while during headless test
                break
                
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
    print("Done")

if __name__ == "__main__":
    main()
