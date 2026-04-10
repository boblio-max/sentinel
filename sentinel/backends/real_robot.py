"""
RealBackend: Interface to physical robot with PCA9685 servo driver.
Communicates via I2C to the servo driver on the robot's Raspberry Pi.
"""

from typing import Dict, Any, Optional
from .base import Backend
from sentinel.models import SensorReading, JointCommands
import time
import struct
import socket
import json
import logging

logger = logging.getLogger(__name__)


class RealBackend(Backend):
    """
    Backend for physical robot with:
    - PCA9685 servo driver (for motor control)
    - IMU + proximity sensors (on Raspberry Pi)
    - Socket bridge to main machine running Sentinel
    """
    
    def __init__(self, robot_id: int, host: str = "localhost", port: int = 5555, timeout: float = 2.0):
        """
        Args:
            robot_id: Robot ID in swarm
            host: IP address of Raspberry Pi running robot
            port: Port for socket communication
            timeout: Socket timeout in seconds
        """
        super().__init__(robot_id)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        
        # Servo configuration
        self.servo_names = [f"servo_{i}" for i in range(8)]  # Adjust based on actual servos
        self.servo_to_channel = {name: i for i, name in enumerate(self.servo_names)}
        
        # PCA9685 settings
        self.pca9685_addr = 0x40  # Default I2C address
        self.pca9685_freq = 50  # 50 Hz for standard servos
        
        # Last known sensor state
        self._last_sensor_reading = None
        
    def initialize(self) -> None:
        """Establish connection to physical robot over socket."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to real robot at {self.host}:{self.port}")
            
            # Send initialization command
            init_msg = {"command": "init", "robot_id": self.robot_id}
            self._send_command(init_msg)
            
            self.running = True
        except Exception as e:
            logger.error(f"Failed to connect to real robot: {e}")
            self.running = False
            raise
    
    def get_sensor_data(self) -> SensorReading:
        """
        Poll physical robot for current sensor readings.
        
        Robot sends back JSON with:
        - position: [x, y, z]
        - orientation: [qx, qy, qz, qw]
        - linear_velocity: [vx, vy, vz]
        - angular_velocity: [wx, wy, wz]
        - joint_positions: {servo_0: angle, ...}
        - joint_velocities: {servo_0: vel, ...}
        - imu_accel: [ax, ay, az]
        - imu_gyro: [gx, gy, gz]
        - proximity: {front: dist, left: dist, right: dist}
        """
        try:
            request = {"command": "read_sensors"}
            response = self._send_command(request)
            
            # Parse response
            sensor_data = SensorReading(
                position=tuple(response.get("position", [0, 0, 0])),
                orientation=tuple(response.get("orientation", [0, 0, 0, 1])),
                linear_velocity=tuple(response.get("linear_velocity", [0, 0, 0])),
                angular_velocity=tuple(response.get("angular_velocity", [0, 0, 0])),
                joint_positions=response.get("joint_positions", {}),
                joint_velocities=response.get("joint_velocities", {}),
                imu_accel=tuple(response.get("imu_accel", [0, 0, 0])) if response.get("imu_accel") else None,
                imu_gyro=tuple(response.get("imu_gyro", [0, 0, 0])) if response.get("imu_gyro") else None,
                extra_data={
                    "proximity": response.get("proximity", {}),
                    "battery_voltage": response.get("battery_voltage", 0),
                    "cpu_temp": response.get("cpu_temp", 0),
                }
            )
            
            self._last_sensor_reading = sensor_data
            return sensor_data
            
        except Exception as e:
            logger.error(f"Failed to read sensors from real robot: {e}")
            # Return last known state or default if no prior reading
            if self._last_sensor_reading:
                return self._last_sensor_reading
            else:
                return SensorReading(
                    position=(0, 0, 0),
                    orientation=(0, 0, 0, 1),
                    linear_velocity=(0, 0, 0),
                    angular_velocity=(0, 0, 0)
                )
    
    def set_joints(self, commands: JointCommands) -> None:
        """
        Send motor commands to physical servos via PCA9685.
        
        Expects velocities in commands.velocities dict with servo names as keys.
        Converts velocity to PWM duty cycle appropriate for servo.
        """
        try:
            # Convert to servo PWM commands
            servo_commands = {}
            for servo_name, velocity in commands.velocities.items():
                if servo_name in self.servo_to_channel:
                    # Convert velocity (-1.0 to 1.0) to PWM (0-4095 for PCA9685)
                    # Center is 1500 us, range is 1000-2000 us for standard servo
                    pwm_value = self._velocity_to_pwm(velocity)
                    servo_commands[servo_name] = pwm_value
            
            # Send command to robot
            msg = {
                "command": "set_servos",
                "servos": servo_commands
            }
            self._send_command(msg)
            
        except Exception as e:
            logger.error(f"Failed to set joints on real robot: {e}")
    
    def step(self, dt: float = 0.001) -> None:
        """
        For real robot, step is typically a no-op since hardware runs independently.
        Could be used for timing synchronization if needed.
        """
        # Real robot's control loop runs on Raspberry Pi
        # This is mainly for interface compatibility
        pass
    
    def reset(self) -> None:
        """
        Reset robot to safe state: stop all motors, zero servos to center position.
        """
        try:
            # Commands to center all servos
            center_commands = JointCommands(
                velocities={name: 0.0 for name in self.servo_names}
            )
            self.set_joints(center_commands)
            
            # Send explicit reset command
            reset_msg = {"command": "reset"}
            self._send_command(reset_msg)
            logger.info("Real robot reset to safe state")
            
        except Exception as e:
            logger.error(f"Failed to reset real robot: {e}")
    
    def shutdown(self) -> None:
        """
        Clean shutdown: stop motors and close connection.
        """
        try:
            if self.running:
                # Stop all motors
                stop_msg = {"command": "stop_all"}
                self._send_command(stop_msg)
                
                # Close socket
                if self.socket:
                    self.socket.close()
                
                logger.info("Real robot backend shut down cleanly")
            
        except Exception as e:
            logger.error(f"Error during real robot shutdown: {e}")
        finally:
            self.running = False
    
    # ===== Helper Methods =====
    
    def _send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send command to robot and receive response.
        Uses JSON serialization over socket.
        """
        if not self.socket:
            raise RuntimeError("Not connected to real robot")
        
        # Serialize and send
        msg_json = json.dumps(command) + "\n"
        self.socket.sendall(msg_json.encode('utf-8'))
        
        # Receive response
        response_json = self._receive_json()
        return response_json
    
    def _receive_json(self) -> Dict[str, Any]:
        """Receive a complete JSON message from socket."""
        buffer = b""
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise ConnectionError("Robot connection closed")
            buffer += chunk
            
            # Try to parse a complete line
            if b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                try:
                    return json.loads(line.decode('utf-8'))
                except json.JSONDecodeError:
                    continue  # Keep trying if invalid JSON
    
    def _velocity_to_pwm(self, velocity: float) -> int:
        """
        Convert velocity command (-1.0 to 1.0) to PCA9685 PWM value (0-4095).
        
        Servo pulse width:
        - 1000 us = -90 degrees (full reverse)
        - 1500 us = 0 degrees (center)
        - 2000 us = +90 degrees (full forward)
        
        PCA9685 at 50 Hz with 4096 steps:
        - 1000 us / 20000 us = 0.05 = 204.8 steps
        - 1500 us / 20000 us = 0.075 = 307.2 steps
        - 2000 us / 20000 us = 0.10 = 409.6 steps
        """
        # Clamp velocity to [-1, 1]
        velocity = max(-1.0, min(1.0, velocity))
        
        # Map to PWM: center at 307 (1.5ms), range ±102 steps (500µs)
        pwm = int(307 + velocity * 102)
        return pwm
    
    def _pwm_to_velocity(self, pwm: int) -> float:
        """Inverse of _velocity_to_pwm."""
        velocity = (pwm - 307) / 102.0
        return max(-1.0, min(1.0, velocity))
