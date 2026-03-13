"""
scene.py — Orchestrates all scene objects: Sun, Earth, Moon, 3 satellites.
Owns the update & draw passes, and provides world-space info for picking.
"""
import math
import numpy as np
from OpenGL.GL import *

import config
import satellite as sat_module
from sun     import Sun
from earth   import Earth
from moon    import Moon
from skybox  import Skybox


class Scene:
    def __init__(self, tex_dir: str = "textures"):
        self.skybox = Skybox(tex_dir)
        self.sun    = Sun(tex_dir)
        self.earth  = Earth(tex_dir)
        self.moon   = Moon(tex_dir)

        self.satellites = [
            sat_module.ISS(),
            sat_module.Hubble(),
            sat_module.Starlink(),
        ]
        self.sim_time = 0.0

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def earth_world(self) -> np.ndarray:
        return self.earth.world_position

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.sim_time += dt
        self.sun.update(dt)
        self.earth.update(dt)
        self.moon.update(dt)
        ew = self.earth_world
        for s in self.satellites:
            s.update(dt, ew)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, cam_eye: np.ndarray) -> None:
        ew = self.earth_world

        # Compute sun direction in eye-space for Phong shaders
        vm = np.array(glGetFloatv(GL_MODELVIEW_MATRIX),
                      dtype=np.float32).reshape(4, 4)
        sun4 = vm.T @ np.array([0.0, 0.0, 0.0, 1.0])
        ep4  = vm.T @ np.array([*ew, 1.0])
        sun_eye_dir = sun4[:3] - ep4[:3]
        nd = np.linalg.norm(sun_eye_dir)
        if nd > 0:
            sun_eye_dir /= nd

        # Make available to satellite draw methods
        sat_module.sun_eye_dir_global = sun_eye_dir.astype(np.float32)

        # Draw order: skybox first (no depth write), then scene
        self.skybox.draw()
        self.sun.draw()
        self.earth.draw(cam_eye)
        self.moon.draw(ew, sun_eye_dir)

        # Enable blending for trails
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for s in self.satellites:
            s.draw(ew, sun_eye_dir)
        glDisable(GL_BLEND)

    # ── Picking ───────────────────────────────────────────────────────────────

    def pick_satellite(self, ray_origin: np.ndarray,
                       ray_dir: np.ndarray) -> str | None:
        """
        Return the name of the satellite hit by the pick ray, or None.
        Satellites are tested in order; smallest bounding-sphere hit wins.
        """
        ew = self.earth_world
        best_name = None
        best_dist = math.inf
        for s in self.satellites:
            wp  = s.world_position(ew)
            oc  = ray_origin - wp
            b   = 2.0 * np.dot(oc, ray_dir)
            c   = np.dot(oc, oc) - 0.25 ** 2
            disc = b * b - 4 * c
            if disc > 0:
                t = (-b - math.sqrt(disc)) / 2.0
                if 0 < t < best_dist:
                    best_dist = t
                    best_name = s.name
        return best_name
