"""
scene.py — Orchestrates Sun, all 8 planets (with moons/rings), and satellites.
"""
import math
import numpy as np
from OpenGL.GL import *

import config
import satellite as sat_module
from sun     import Sun
from planet  import Planet
from skybox  import Skybox
from midpoint_circle import circle_points


class Scene:
    def __init__(self, tex_dir: str = "textures"):
        self.skybox = Skybox(tex_dir)
        self.sun    = Sun(tex_dir)

        # Build all planets from config
        self.planets = [Planet(data, tex_dir) for data in config.PLANETS_DATA]

        # Earth is the 3rd planet (index 2)
        self.earth = self.planets[2]

        # Satellites orbit Earth
        self.satellites = [sat_module.make_satellite(n)
                           for n in ("ISS", "Hubble", "TDRS")]

        self.sim_time   = 0.0
        self.time_scale = 1.0          # set by HUD buttons

        # Pre-compute orbit guide vertex lists once using MCA.
        # Each planet gets a list of (x, z) pairs for its orbit circle.
        self._orbit_guide_pts = self._build_orbit_guides()

    # ── Orbit guide pre-computation ───────────────────────────────────────────

    @staticmethod
    def _build_orbit_guides() -> list[list[tuple[float, float]]]:
        """
        Build one circle-point list per planet using the Midpoint Circle
        Algorithm.  Called once at startup — zero trig per draw call.

        Returns a list (one entry per planet) of (x, z) float tuples.
        """
        N = 180   # guide circle resolution
        unit_pts = circle_points(N)   # (cos, sin) × N via MCA
        guides = []
        for planet_data in config.PLANETS_DATA:
            r = planet_data["orbit_radius"]
            guides.append([(cx * r, cz * r) for (cx, cz) in unit_pts])
        return guides

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def earth_world(self) -> np.ndarray:
        return self.earth.world_position

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        scaled = dt * self.time_scale
        self.sim_time += scaled
        self.sun.update(scaled)
        for planet in self.planets:
            planet.update(scaled)
        ew = self.earth_world
        for s in self.satellites:
            s.update(scaled, ew)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, cam_eye: np.ndarray) -> None:
        ew = self.earth_world

        # Compute sun→planet eye-space direction for Phong shaders
        vm = np.array(glGetFloatv(GL_MODELVIEW_MATRIX),
                      dtype=np.float32).reshape(4, 4)
        sun4 = vm.T @ np.array([0.0, 0.0, 0.0, 1.0])
        ep4  = vm.T @ np.array([*ew, 1.0])
        sun_eye_dir = sun4[:3] - ep4[:3]
        nd = np.linalg.norm(sun_eye_dir)
        if nd > 0: sun_eye_dir /= nd
        sat_module.sun_eye_dir_global = sun_eye_dir.astype(np.float32)

        # Draw
        self.skybox.draw()
        self.sun.draw()

        # Orbit guide circles
        self._draw_orbit_guides()

        for planet in self.planets:
            planet.draw(cam_eye, sun_eye_dir)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for s in self.satellites:
            s.draw(ew, sun_eye_dir)
        glDisable(GL_BLEND)

    def _draw_orbit_guides(self) -> None:
        """
        Faint dashed circles showing each planet's orbital path.

        Vertex positions come from the MCA-generated lookup table built in
        __init__ — no trig calls here at all.
        """
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(0.8)

        for pts in self._orbit_guide_pts:
            glBegin(GL_LINE_LOOP)
            glColor4f(0.3, 0.4, 0.6, 0.25)
            for (x, z) in pts:
                glVertex3f(x, 0.0, z)
            glEnd()

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

    # ── Picking ───────────────────────────────────────────────────────────────

    def pick_satellite(self, ray_origin: np.ndarray,
                       ray_dir: np.ndarray) -> str | None:
        ew = self.earth_world
        best_name, best_dist = None, math.inf
        for s in self.satellites:
            if not s.is_hit_by_ray(ray_origin, ray_dir, ew):
                continue
            c  = s.world_position(ew)
            oc = ray_origin - c
            b  = 2.0 * np.dot(oc, ray_dir)
            c2 = np.dot(oc, oc) - 0.25**2
            disc = b*b - 4*c2
            if disc > 0:
                t = (-b - math.sqrt(disc)) / 2.0
                if 0 < t < best_dist:
                    best_dist, best_name = t, s.name
        return best_name

    def pick_planet(self, ray_origin: np.ndarray,
                    ray_dir: np.ndarray) -> str | None:
        """Ray-sphere test against all planets."""
        best_name, best_dist = None, math.inf
        for planet in self.planets:
            wp = planet.world_position
            r  = planet._radius * 1.1
            oc = ray_origin - wp
            b  = 2.0 * np.dot(oc, ray_dir)
            c  = np.dot(oc, oc) - r**2
            disc = b*b - 4*c
            if disc > 0:
                t = (-b - math.sqrt(disc)) / 2.0
                if 0 < t < best_dist:
                    best_dist, best_name = t, planet.name
        return best_name
