import multiprocessing
import os
import time
import math
import random
import sys
import pygame
from typing import Dict, List, Optional, Tuple

from sentinel.backends.sim_mujoco import SimBackend
from sentinel.controllers.robot_controller import RobotController
from sentinel.bus import SwarmBus
from sentinel import config

def sim_robot_worker(robot_id: int, shared_dict: dict, urdf_path: str, start_pos: tuple):
    """Entry point for a single robot simulation process."""
    # Headless mode for all workers
    backend = SimBackend(robot_id=robot_id, xml_path=urdf_path, headless=True, start_pos=start_pos)
    bus = SwarmBus(shared_dict)
    
    robot = RobotController(robot_id=robot_id, backend=backend, swarm_bus=bus)
    robot.initialize()
    
    tick = 0
    start_time = time.time()
    
    try:
        while True:
            # Check for global goal in shared dictionary
            goal = shared_dict.get('goal')
            if goal:
                robot.boids.set_goal(goal)
            
            # Control loop
            robot.step()
            
            # Realtime sync
            elapsed = time.time() - start_time
            # Target timestep from config or backend
            target_dt = 1.0 / config.SIM_TICK_RATE
            sleep_time = target_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            start_time = time.time()
            tick += 1
    except KeyboardInterrupt:
        pass
    finally:
        robot.shutdown()

class SentinelOrchestrator:
    def __init__(self, n_sim=config.DEFAULT_N_SIM, visualize=True):
        self.n_sim = n_sim
        self.manager = multiprocessing.Manager()
        self.shared_dict = self.manager.dict()
        self.bus = SwarmBus(self.shared_dict)
        self.processes = []
        
        # UI State
        self.visualize = visualize
        self.goal: Optional[Tuple[float, float]] = None
        self.trails: Dict[int, List[Tuple[int, int]]] = {i: [] for i in range(n_sim)}
        self.max_trail_len = 20
        
        if self.visualize:
            pygame.init()
            self.screen = pygame.display.set_mode(config.WINDOW_SIZE)
            pygame.display.set_caption("SENTINEL | Swarm Command & Control")
            self.font_main = pygame.font.SysFont("Verdana", 14)
            self.font_header = pygame.font.SysFont("Verdana", 18, bold=True)
            self.font_logo = pygame.font.SysFont("Verdana", 24, bold=True)
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(current_dir, "assets", "robot.xml")

    def _world_to_px(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        """Map physical bounds (-10 to 10) to screen pixel coordinates."""
        # Simple mapping assuming center is (500, 400) for 1000x800
        # Let's use a scale factor
        scale = config.WINDOW_SIZE[0] / 20.0 # 50px per unit
        offset_x = config.WINDOW_SIZE[0] // 2
        offset_y = config.WINDOW_SIZE[1] // 2
        
        px_x = int(pos[0] * scale + offset_x)
        px_y = int(-pos[1] * scale + offset_y)
        return (px_x, px_y)

    def _px_to_world(self, px: Tuple[int, int]) -> Tuple[float, float]:
        scale = config.WINDOW_SIZE[0] / 20.0
        offset_x = config.WINDOW_SIZE[0] // 2
        offset_y = config.WINDOW_SIZE[1] // 2
        
        wx = (px[0] - offset_x) / scale
        wy = -(px[1] - offset_y) / scale
        return (wx, wy)

    def draw_dashboard(self):
        self.screen.fill(config.COLOR_BG)
        
        # 1. Draw Grid
        grid_step = config.GRID_SIZE
        for x in range(0, config.WINDOW_SIZE[0], grid_step):
            pygame.draw.line(self.screen, config.COLOR_GRID, (x, 0), (x, config.WINDOW_SIZE[1]), 1)
        for y in range(0, config.WINDOW_SIZE[1], grid_step):
            pygame.draw.line(self.screen, config.COLOR_GRID, (0, y), (config.WINDOW_SIZE[0], y), 1)

        # 2. Draw Goal Point
        if self.goal:
            g_px = self._world_to_px(self.goal)
            # Pulse effect or static marker
            pygame.draw.circle(self.screen, config.COLOR_GOAL, g_px, 8, 2)
            pygame.draw.circle(self.screen, config.COLOR_GOAL, g_px, 2)

        # 3. Draw Robots
        swarm_positions = []
        for r_id in range(self.n_sim):
            s = self.shared_dict.get(r_id)
            if not s:
                continue
            
            swarm_positions.append(s.position)
            px = self._world_to_px(s.position)
            
            # Update and draw trails
            self.trails[r_id].append(px)
            if len(self.trails[r_id]) > self.max_trail_len:
                self.trails[r_id].pop(0)
            
            if len(self.trails[r_id]) > 1:
                pygame.draw.lines(self.screen, config.COLOR_GRID, False, self.trails[r_id], 1)

            # Draw robot glow (layers)
            for r in range(16, 8, -2):
                alpha = int(100 * (1 - r/16))
                surface = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(surface, (*config.COLOR_ROBOT_GLOW, alpha), (r, r), r)
                self.screen.blit(surface, (px[0]-r, px[1]-r))

            # Core
            pygame.draw.circle(self.screen, config.COLOR_ROBOT, px, 6)
            
            # Heading Indicator
            h_len = 15
            h_end = (
                px[0] + int(h_len * math.cos(s.heading)),
                px[1] - int(h_len * math.sin(s.heading))
            )
            pygame.draw.line(self.screen, config.COLOR_HEADING, px, h_end, 2)

        # 4. Draw GUI Overlay / Telemetry
        # Semi-transparent overlay for sidebar
        sidebar_w = 220
        sidebar_bg = pygame.Surface((sidebar_w, config.WINDOW_SIZE[1]), pygame.SRCALPHA)
        sidebar_bg.fill((10, 15, 25, 200))
        self.screen.blit(sidebar_bg, (0, 0))
        
        y_off = 20
        # Logo
        logo = self.font_logo.render("SENTINEL", True, config.COLOR_ROBOT)
        self.screen.blit(logo, (20, y_off))
        y_off += 40
        
        # Telemetry
        header = self.font_header.render("SWARM STATUS", True, config.COLOR_TEXT)
        self.screen.blit(header, (20, y_off))
        y_off += 30
        
        self.screen.blit(self.font_main.render(f"Robots: {self.n_sim}", True, config.COLOR_TEXT), (20, y_off))
        y_off += 20
        
        if swarm_positions:
            avg_x = sum(p[0] for p in swarm_positions) / len(swarm_positions)
            avg_y = sum(p[1] for p in swarm_positions) / len(swarm_positions)
            dispersion = sum(math.hypot(p[0]-avg_x, p[1]-avg_y) for p in swarm_positions) / len(swarm_positions)
            
            self.screen.blit(self.font_main.render(f"Centroid: {avg_x:.1f}, {avg_y:.1f}", True, config.COLOR_TEXT), (20, y_off))
            y_off += 20
            self.screen.blit(self.font_main.render(f"Dispersion: {dispersion:.2f}", True, config.COLOR_TEXT), (20, y_off))
            y_off += 20
        
        y_off += 20
        goal_status = "SET" if self.goal else "IDLE"
        self.screen.blit(self.font_main.render(f"Mode: {goal_status}", True, config.COLOR_GOAL if self.goal else config.COLOR_TEXT), (20, y_off))
        
        # Footnote
        self.screen.blit(self.font_main.render("Click grid to set GOAL", True, (100, 110, 120)), (20, config.WINDOW_SIZE[1]-40))

        pygame.display.flip()

    def run(self, ticks_to_run: int = -1):
        print(f"Spawning {self.n_sim} sim robots...")
        
        # Clean startup: Clear shared dict
        self.shared_dict.clear()
        
        # Spawn randomized positions
        for i in range(self.n_sim):
            sx = random.uniform(-4.0, 4.0)
            sy = random.uniform(-4.0, 4.0)
            p = multiprocessing.Process(
                target=sim_robot_worker, 
                args=(i, self.shared_dict, self.model_path, (sx, sy))
            )
            self.processes.append(p)
            p.start()
            
        print("Swarm simulation running! Click the dashboard to set objectives.")
        
        tick = 0
        clock = pygame.time.Clock() if self.visualize else None
        
        running = True
        try:
            while running and (ticks_to_run < 0 or tick < ticks_to_run):
                if self.visualize:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                        
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            # Handle goal setting
                            self.goal = self._px_to_world(event.pos)
                            self.shared_dict['goal'] = self.goal
                            print(f"Global Goal Updated: {self.goal}")
                            
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_r: # Reset goal
                                self.goal = None
                                if 'goal' in self.shared_dict:
                                    del self.shared_dict['goal']
                                print("Goal Reset")

                    self.draw_dashboard()
                    clock.tick(config.SIM_TICK_RATE) 
                else:
                    time.sleep(1.0/config.SIM_TICK_RATE)
                
                tick += 1
                
        except KeyboardInterrupt:
            print("\nKeyboard Interrupt caught.")
        finally:
            self.shutdown()

    def shutdown(self):
        print("Shutting down swarm processes...")
        if self.visualize:
            pygame.quit()
        for p in self.processes:
            if p.is_alive():
                p.terminate()
        for p in self.processes:
            p.join(timeout=1.0)
        print("Shutdown complete.")
