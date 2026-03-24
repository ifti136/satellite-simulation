"""
orbit.py — Circular orbital mechanics.
"""
import math
import numpy as np


class Orbit:
    def __init__(self, radius: float, inclination: float,
                 speed: float, phase: float = 0.0):
        self.radius      = radius
        self.inclination = math.radians(inclination)
        self.speed       = speed
        self.angle       = phase

    def update(self, dt: float) -> None:
        self.angle = (self.angle + self.speed * dt) % (2 * math.pi)

    def local_position(self) -> np.ndarray:
        lx = self.radius * math.cos(self.angle)
        lz = self.radius * math.sin(self.angle)
        inc = self.inclination
        px = lx
        py = -lz * math.sin(inc)
        pz =  lz * math.cos(inc)
        return np.array([px, py, pz], dtype=np.float64)

    def velocity_direction(self) -> np.ndarray:
        inc = self.inclination
        vx = -math.sin(self.angle)
        vz =  math.cos(self.angle)
        fx = vx
        fy = -vz * math.sin(inc)
        fz =  vz * math.cos(inc)
        v = np.array([fx, fy, fz], dtype=np.float64)
        n = np.linalg.norm(v)
        return v / n if n > 0 else v
