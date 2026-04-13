"""
Configuration settings for the Sentinel Swarm Orchestrator.
Centralizes aesthetics, physics, and swarm logic parameters.
"""

# Dashboard Visuals
WINDOW_SIZE = (1000, 800)
GRID_SIZE = 80
COLOR_BG = (15, 15, 20)           # Deep space blue
COLOR_GRID = (30, 35, 45)         # Subtle navy grid
COLOR_ROBOT = (0, 200, 255)       # Cyber cyan
COLOR_ROBOT_GLOW = (0, 100, 255)  # Glow blue
COLOR_HEADING = (255, 60, 100)    # Neon pink
COLOR_TEXT = (220, 230, 240)      # Soft paper white
COLOR_GOAL = (50, 255, 150)       # Matrix green

# Swarm Physics (Boids)
DEFAULT_SEP_RADIUS = 1.2
DEFAULT_ALIGN_RADIUS = 2.5
DEFAULT_COH_RADIUS = 3.0
DEFAULT_GOAL_WEIGHT = 1.5

WEIGHT_SEPARATION = 3.0
WEIGHT_ALIGNMENT = 1.0
WEIGHT_COHESION = 1.2

MAX_SPEED = 4.0
MAX_TURN_SPEED = 6.0

# Simulation
DEFAULT_N_SIM = 9
SIM_TICK_RATE = 60
COMM_RADIUS = 5.0  # Communication range between robots
