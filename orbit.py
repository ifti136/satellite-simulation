"""
orbit.py — Circular orbital mechanics.
Covers Earth→Sun, Moon→Earth, and satellite→Earth orbits.
"""
import math
import numpy as np


class Orbit:
    """
    Circular orbit in a parent-body reference frame.

    Parameters
    ----------
    radius      : float  — orbital radius in sim units
    inclination : float  — orbital plane tilt in **degrees** (around X axis)
    speed       : float  — angular velocity in rad/s
    phase       : float  — initial angle in radians
    """

    def __init__(self, radius: float, inclination: float,
                 speed: float, phase: float = 0.0):
        self.radius      = radius
        self.inclination = math.radians(inclination)
        self.speed       = speed
        self.angle       = phase         # current angle (radians)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.angle = (self.angle + self.speed * dt) % (2 * math.pi)

    # ── Position relative to parent-body centre ───────────────────────────────

    def local_position(self) -> np.ndarray:
        """
        Returns (x, y, z) of the orbiting body in its parent's world frame.
        The orbit lies in the XZ plane and is then tilted by *inclination*
        around the X axis.
        """
        # Orbit in the XZ plane
        lx = self.radius * math.cos(self.angle)
        ly = 0.0
        lz = self.radius * math.sin(self.angle)

        # Tilt by inclination around X axis
        inc = self.inclination
        px = lx
        py =  ly * math.cos(inc) - lz * math.sin(inc)
        pz =  ly * math.sin(inc) + lz * math.cos(inc)

        return np.array([px, py, pz], dtype=np.float64)

    def velocity_direction(self) -> np.ndarray:
        """
        Normalised tangential (forward) direction of the orbiting body.
        Used by the camera's TPP follow mode.
        """
        # d/dθ of local_position, normalised
        inc = self.inclination
        vx = -math.sin(self.angle)
        vy =  0.0
        vz =  math.cos(self.angle)

        # Same inclination rotation
        fx = vx
        fy =  vy * math.cos(inc) - vz * math.sin(inc)
        fz =  vy * math.sin(inc) + vz * math.cos(inc)

        v = np.array([fx, fy, fz], dtype=np.float64)
        n = np.linalg.norm(v)
        return v / n if n > 0 else v
