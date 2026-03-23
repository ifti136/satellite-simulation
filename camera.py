"""
camera.py — Three camera modes with smooth interpolation.

Modes
-----
  solar         : wide cinematic view of the whole solar system (drag + scroll)
  earth_tpp     : top-down third-person view following Earth around the Sun
  satellite_tpp : top-down third-person view following the selected satellite
"""
import math
import numpy as np

from OpenGL.GL import *

import config


def _lerp3(a, b, t):
    return a + (b - a) * t


def _safe_normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


class Camera:
    def __init__(self):
        self.mode    = config.CAM_MODE_SOLAR
        self.sat_idx = 0   # 0=ISS, 1=Hubble, 2=Starlink

        # Current interpolated eye / centre / up
        self._eye    = np.array([0.0, 80.0, 80.0])
        self._centre = np.array([0.0,  0.0,  0.0])
        self._up     = np.array([0.0,  1.0,  0.0])

        # Smooth-lerp targets
        self._t_eye    = self._eye.copy()
        self._t_centre = self._centre.copy()
        self._t_up     = self._up.copy()

        # Solar free-rotate (mouse drag)
        self._solar_yaw   = 0.0
        self._solar_pitch = 35.0   # degrees — tilted so orbit plane is visible
        self._solar_dist  = 90.0
        self._drag_active = False
        self._drag_last   = (0, 0)

        # Cached view matrix for ray picking
        self.view_matrix = np.eye(4, dtype=np.float64)

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_event(self, event) -> None:
        import pygame
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.mode = config.CAM_MODE_SOLAR
            elif event.key == pygame.K_2:
                self.mode = config.CAM_MODE_EARTH_TPP
            elif event.key == pygame.K_3:
                self.mode = config.CAM_MODE_SAT_TPP
            elif event.key == pygame.K_TAB:
                self.sat_idx = (self.sat_idx + 1) % 3

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.mode == config.CAM_MODE_SOLAR:
                self._drag_active = True
                self._drag_last   = event.pos
            elif event.button == 4:
                self._solar_dist = max(20.0, self._solar_dist - 4.0)
            elif event.button == 5:
                self._solar_dist = min(300.0, self._solar_dist + 4.0)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._drag_active = False

        elif event.type == pygame.MOUSEMOTION:
            if self._drag_active:
                dx = event.pos[0] - self._drag_last[0]
                dy = event.pos[1] - self._drag_last[1]
                self._solar_yaw   += dx * 0.4
                self._solar_pitch  = np.clip(self._solar_pitch - dy * 0.3, 5, 85)
                self._drag_last    = event.pos

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, earth, satellites) -> None:
        if self.mode == config.CAM_MODE_SOLAR:
            self._update_solar()

        elif self.mode == config.CAM_MODE_EARTH_TPP:
            self._update_earth_tpp(earth)

        elif self.mode == config.CAM_MODE_SAT_TPP:
            sat = satellites[self.sat_idx]
            self._update_sat_tpp(sat, earth.world_position)

        # Smooth lerp — snappier (dt*6) so the camera doesn't lag badly
        alpha = min(1.0, dt * 6.0)
        self._eye    = _lerp3(self._eye,    self._t_eye,    alpha)
        self._centre = _lerp3(self._centre, self._t_centre, alpha)
        self._up     = _lerp3(self._up,     self._t_up,     alpha)

        # Keep up normalised
        n = np.linalg.norm(self._up)
        if n > 1e-9:
            self._up /= n

    # ── Solar (free-rotate around origin) ─────────────────────────────────────

    def _update_solar(self) -> None:
        yaw_r   = math.radians(self._solar_yaw)
        pitch_r = math.radians(self._solar_pitch)
        ex = self._solar_dist * math.cos(pitch_r) * math.sin(yaw_r)
        ey = self._solar_dist * math.sin(pitch_r)
        ez = self._solar_dist * math.cos(pitch_r) * math.cos(yaw_r)
        self._t_eye    = np.array([ex, ey, ez])
        self._t_centre = np.array([0.0, 0.0, 0.0])
        self._t_up     = np.array([0.0, 1.0, 0.0])

    # ── Earth TPP ─────────────────────────────────────────────────────────────
    #
    # Camera sits above-and-behind Earth as it orbits the Sun.
    # "Behind" = opposite to the orbital velocity direction (so we look forward).
    # "Above"  = along the world Y axis (the orbital plane normal).
    # The camera always looks AT Earth's world position.

    def _update_earth_tpp(self, earth) -> None:
        earth_wp  = earth.world_position          # Earth's position in world
        orbit_fwd = earth.solar_orbit.velocity_direction()  # tangent to orbit

        # We want to sit above and slightly behind Earth.
        # "up" in world space is Y (orbit is in the XZ plane).
        world_up = np.array([0.0, 1.0, 0.0])

        # Right vector of the camera (perpendicular to forward and up)
        right = _safe_normalize(np.cross(orbit_fwd, world_up))

        # Recompute a clean up that is perpendicular to both
        cam_up = _safe_normalize(np.cross(right, orbit_fwd))

        # Camera offset:
        #   pull back along -orbit_fwd (behind Earth relative to travel)
        #   raise up along cam_up (above the orbital plane)
        # Distances tuned to keep Earth nicely in frame
        back_dist = 6.0    # units behind Earth
        up_dist   = 10.0   # units above Earth

        offset = (-orbit_fwd * back_dist) + (world_up * up_dist)

        self._t_eye    = earth_wp + offset
        self._t_centre = earth_wp          # look directly at Earth
        self._t_up     = world_up          # keep horizon level

    # ── Satellite TPP ─────────────────────────────────────────────────────────
    #
    # Same logic as Earth TPP but following the satellite around Earth.
    # The satellite orbits Earth, so we compute the satellite's orbital tangent
    # and position the camera behind+above the satellite, looking at it.

    def _update_sat_tpp(self, sat, earth_wp: np.ndarray) -> None:
        sat_wp  = sat.world_position(earth_wp)    # satellite world position
        sat_fwd = sat.velocity_direction()         # tangent to satellite orbit

        world_up = np.array([0.0, 1.0, 0.0])

        # Build camera frame
        right  = _safe_normalize(np.cross(sat_fwd, world_up))
        cam_up = _safe_normalize(np.cross(right, sat_fwd))

        # For satellites the orbit is much smaller, so distances are tighter
        back_dist = 1.5
        up_dist   = 3.0

        offset = (-sat_fwd * back_dist) + (world_up * up_dist)

        self._t_eye    = sat_wp + offset
        self._t_centre = sat_wp      # look directly at the satellite
        self._t_up     = world_up

    # ── Apply to OpenGL ───────────────────────────────────────────────────────

    def apply(self) -> None:
        # --- Projection ---
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        fov_rad = math.radians(config.FOV)
        aspect  = config.WINDOW_WIDTH / config.WINDOW_HEIGHT
        f       = 1.0 / math.tan(fov_rad / 2.0)
        z_n, z_f = config.NEAR_CLIP, config.FAR_CLIP

        proj_mat = np.array([
            [f / aspect, 0,  0,                           0],
            [0,          f,  0,                           0],
            [0,          0,  (z_f + z_n) / (z_n - z_f),  (2 * z_f * z_n) / (z_n - z_f)],
            [0,          0, -1,                           0],
        ], dtype=np.float32)
        glMultMatrixf(proj_mat.T)

        # --- View / ModelView ---
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Build view matrix from eye / centre / up
        z_axis = _safe_normalize(self._eye - self._centre)   # points toward camera
        x_axis = _safe_normalize(np.cross(self._up, z_axis))
        y_axis = np.cross(z_axis, x_axis)                    # already unit

        view_mat = np.eye(4, dtype=np.float64)
        view_mat[0, :3] = x_axis
        view_mat[1, :3] = y_axis
        view_mat[2, :3] = z_axis
        view_mat[0, 3]  = -np.dot(x_axis, self._eye)
        view_mat[1, 3]  = -np.dot(y_axis, self._eye)
        view_mat[2, 3]  = -np.dot(z_axis, self._eye)

        glMultMatrixf(view_mat.T)   # OpenGL is column-major

        # Cache for pick ray
        self.view_matrix = view_mat

    # ── Ray picking ───────────────────────────────────────────────────────────

    def get_pick_ray(self, mouse_x: int, mouse_y: int):
        """
        Returns (ray_origin, ray_direction) in world space for the given pixel.
        """
        # Read back projection from OpenGL (column-major → transpose to row-major)
        proj_col = np.array(glGetFloatv(GL_PROJECTION_MATRIX),
                            dtype=np.float64).reshape(4, 4)
        proj = proj_col.T   # now row-major: proj[row][col]

        ndc_x = (2.0 * mouse_x / config.WINDOW_WIDTH)  - 1.0
        ndc_y = 1.0 - (2.0 * mouse_y / config.WINDOW_HEIGHT)

        # Unproject from clip space → eye space
        inv_proj  = np.linalg.inv(proj)
        ray_clip  = np.array([ndc_x, ndc_y, -1.0, 1.0])
        ray_eye_h = inv_proj @ ray_clip
        ray_eye   = np.array([ray_eye_h[0], ray_eye_h[1], -1.0, 0.0])

        # Unproject from eye space → world space
        # view_matrix is already row-major
        inv_view  = np.linalg.inv(self.view_matrix)
        ray_world = inv_view @ ray_eye
        ray_dir   = _safe_normalize(ray_world[:3])

        return self._eye.copy(), ray_dir

    @property
    def eye_position(self) -> np.ndarray:
        return self._eye.copy()
