import multiprocessing
import os
import time
import math
import random
import sys
import pygame
from sentinel.backends.sim_mujoco import SimBackend
from sentinel.controllers.robot_controller import RobotController
from sentinel.bus import SwarmBus

def sim_robot_worker(robot_id: int, shared_dict: dict, urdf_path: str, start_pos: tuple):
    """Entry point for a single robot simulation process."""
    # Headless mode for all workers
    backend = SimBackend(xml_path=urdf_path, headless=True, start_pos=start_pos)
    bus = SwarmBus(shared_dict)
    
    robot = RobotController(robot_id=robot_id, backend=backend, swarm_bus=bus)
    
    tick = 0
    start_time = time.time()
    
    try:
        while True:
            robot.step()
            backend.step_simulation()
            
            # Realtime lock
            time_until_next_step = backend.model.opt.timestep - (time.time() - start_time)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)
            start_time = time.time()
            
            tick += 1
    except KeyboardInterrupt:
        pass

class SentinelOrchestrator:
    def __init__(self, n_sim=9, visualize=True):
        self.n_sim = n_sim
        self.manager = multiprocessing.Manager()
        self.shared_dict = self.manager.dict()
        self.bus = SwarmBus(self.shared_dict)
        self.processes = []
        
        self.visualize = visualize
        if self.visualize:
            pygame.init()
            self.screen = pygame.display.set_mode((800, 800))
            pygame.display.set_caption("Sentinel Swarm Dashboard")
            self.font = pygame.font.SysFont("Arial", 16)
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(current_dir, "assets", "robot.xml")

    def draw_dashboard(self):
        self.screen.fill((30, 30, 30))
        
        # Grid
        for i in range(11):
            pygame.draw.line(self.screen, (50, 50, 50), (0, i * 80), (800, i * 80))
            pygame.draw.line(self.screen, (50, 50, 50), (i * 80, 0), (i * 80, 800))
        
        for r_id in range(self.n_sim):
            s = self.shared_dict.get(r_id)
            if s:
                # Map physical bounds (say -5 to 5) to 800x800 screen
                x_px = int((s.position[0] + 5.0) * (800.0 / 10.0))
                # Pygame Y is inverted relative to standard math
                y_px = int((-s.position[1] + 5.0) * (800.0 / 10.0))
                
                # Draw robot circle
                pygame.draw.circle(self.screen, (0, 150, 250), (x_px, y_px), 12)
                
                # Draw heading vector
                # Heading in world coordinates has +Y up, PyGame has +Y down
                # So we negate the Y component of the heading vector
                end_x = x_px + int(25 * math.cos(s.heading))
                end_y = y_px - int(25 * math.sin(s.heading))
                pygame.draw.line(self.screen, (255, 100, 100), (x_px, y_px), (end_x, end_y), 3)
                
                # Draw Label
                txt = self.font.render(f"{r_id}", True, (255, 255, 255))
                self.screen.blit(txt, (x_px + 15, y_px - 15))
                
        pygame.display.flip()

    def run(self, ticks_to_run: int = -1):
        print(f"Spawning {self.n_sim} sim robots...")
        
        # Spawn randomized positions in a smaller physical bounds so they stay on screen
        for i in range(self.n_sim):
            sx = random.uniform(-3.0, 3.0)
            sy = random.uniform(-3.0, 3.0)
            p = multiprocessing.Process(
                target=sim_robot_worker, 
                args=(i, self.shared_dict, self.model_path, (sx, sy))
            )
            self.processes.append(p)
            p.start()
            
        print("Swarm simulation running! Notice: PyGame dashboard is active.")
        
        tick = 0
        clock = pygame.time.Clock() if self.visualize else None
        
        running = True
        try:
            while running and (ticks_to_run < 0 or tick < ticks_to_run):
                if self.visualize:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                    
                    self.draw_dashboard()
                    clock.tick(60) # 60 FPS update for dashboard
                else:
                    time.sleep(0.1)
                
                tick += 1
                
        except KeyboardInterrupt:
            print("\nKeyboard Interrupt caught.")
        finally:
            print("Shutting down swarm processes...")
            if self.visualize:
                pygame.quit()
            for p in self.processes:
                if p.is_alive():
                    p.terminate()
            for p in self.processes:
                p.join()
            print("Shutdown complete.")
