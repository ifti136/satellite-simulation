"""
camera.py — Three camera modes with smooth interpolation.

Modes
-----
  solar       : wide cinematic view of the whole solar system
  earth_tpp   : third-person behind Earth as it orbits the Sun
  satellite_tpp : third-person behind the selected satellite
"""
import math
import numpy as np

from OpenGL.GL  import *
import OpenGL.GLU as glu

#from OpenGL.GL  import *
#from OpenGL.GLU import gluLookAt, gluPerspective

import config


def _lerp3(a, b, t):
    return a + (b - a) * t


class Camera:
    def __init__(self):
        self.mode     = config.CAM_MODE_SOLAR
        self.sat_idx  = 0    # 0=ISS, 1=Hubble, 2=Starlink

        # Current & target eye/centre/up (smooth interpolation)
        self._eye    = np.array([0.0, 40.0, 90.0])
        self._centre = np.array([0.0,  0.0,  0.0])
        self._up     = np.array([0.0,  1.0,  0.0])

        self._t_eye    = self._eye.copy()
        self._t_centre = self._centre.copy()
        self._t_up     = self._up.copy()

        # For solar free-rotate mode (mouse drag)
        self._solar_yaw   = 0.0
        self._solar_pitch = 20.0       # degrees
        self._solar_dist  = 85.0
        self._drag_active = False
        self._drag_last   = (0, 0)

        # Stored view matrix for ray picking
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
            elif event.button == 4:   # scroll up – zoom in
                self._solar_dist = max(20.0, self._solar_dist - 4.0)
            elif event.button == 5:   # scroll down – zoom out
                self._solar_dist = min(250.0, self._solar_dist + 4.0)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._drag_active = False

        elif event.type == pygame.MOUSEMOTION:
            if self._drag_active:
                dx = event.pos[0] - self._drag_last[0]
                dy = event.pos[1] - self._drag_last[1]
                self._solar_yaw   += dx * 0.4
                self._solar_pitch  = np.clip(self._solar_pitch - dy * 0.3, -85, 85)
                self._drag_last    = event.pos

    # ── Update (compute target eye/centre each frame) ─────────────────────────

    def update(self, dt: float, earth, satellites) -> None:
        sat_names = ["ISS", "Hubble", "Starlink"]
        sat_list  = satellites

        earth_wp  = earth.world_position
        earth_orb = earth.solar_orbit

        if self.mode == config.CAM_MODE_SOLAR:
            self._update_solar()

        elif self.mode == config.CAM_MODE_EARTH_TPP:
            self._update_earth_tpp(earth_wp, earth_orb)

        elif self.mode == config.CAM_MODE_SAT_TPP:
            sat = sat_list[self.sat_idx]
            self._update_sat_tpp(sat, earth_wp)

        # Smooth lerp towards target
        alpha = min(1.0, dt * 5.0)
        self._eye    = _lerp3(self._eye,    self._t_eye,    alpha)
        self._centre = _lerp3(self._centre, self._t_centre, alpha)
        self._up     = _lerp3(self._up,     self._t_up,     alpha)
        n = np.linalg.norm(self._up)
        if n > 0:
            self._up /= n

    def _update_solar(self) -> None:
        yaw_r   = math.radians(self._solar_yaw)
        pitch_r = math.radians(self._solar_pitch)
        ex = self._solar_dist * math.cos(pitch_r) * math.sin(yaw_r)
        ey = self._solar_dist * math.sin(pitch_r)
        ez = self._solar_dist * math.cos(pitch_r) * math.cos(yaw_r)
        self._t_eye    = np.array([ex, ey, ez])
        self._t_centre = np.array([0.0, 0.0, 0.0])
        self._t_up     = np.array([0.0, 1.0, 0.0])

    def _update_earth_tpp(self, earth_wp, earth_orb) -> None:
        fwd   = earth_orb.velocity_direction()
        up_w  = np.array([0.0, 1.0, 0.0])
        right = np.cross(fwd, up_w)
        right /= np.linalg.norm(right) + 1e-9
        real_up = np.cross(right, fwd)

        offset  = -fwd * 9.0 + real_up * 4.0
        self._t_eye    = earth_wp + offset
        self._t_centre = earth_wp
        self._t_up     = real_up

    def _update_sat_tpp(self, sat, earth_wp) -> None:
        sat_wp = sat.world_position(earth_wp)
        fwd    = sat.velocity_direction()
        up_w   = np.array([0.0, 1.0, 0.0])
        right  = np.cross(fwd, up_w)
        r_norm = np.linalg.norm(right)
        if r_norm > 1e-6:
            right /= r_norm
        real_up = np.cross(right, fwd)

        offset  = -fwd * 2.5 + real_up * 0.8
        self._t_eye    = sat_wp + offset
        self._t_centre = sat_wp + fwd * 2.0
        self._t_up     = real_up

    # ── Apply to OpenGL ───────────────────────────────────────────────────────

    def apply(self) -> None:
    # --- 1. PROJECTION MATRIX (Replaces gluPerspective) ---
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        fov_rad = math.radians(config.FOV)
        aspect = config.WINDOW_WIDTH / config.WINDOW_HEIGHT
        f = 1.0 / math.tan(fov_rad / 2.0)
        z_n = config.NEAR_CLIP
        z_f = config.FAR_CLIP
        
        # Standard perspective matrix array
        proj_mat = np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (z_f + z_n) / (z_n - z_f), (2 * z_f * z_n) / (z_n - z_f)],
            [0, 0, -1, 0]
        ], dtype=np.float32)
        
        glMultMatrixf(proj_mat.T) # OpenGL expects column-major, so we transpose

        # --- 2. MODELVIEW MATRIX (Simplified Camera View) ---
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # We'll use a trick: rotate the coordinate system to match our eye/center/up
        # instead of relying on gluLookAt which might also be "Null"
        z_axis = (self._eye - self._centre)
        z_axis /= np.linalg.norm(z_axis)
        x_axis = np.cross(self._up, z_axis)
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis)

        view_mat = np.eye(4)
        view_mat[:3, 0] = x_axis
        view_mat[:3, 1] = y_axis
        view_mat[:3, 2] = z_axis
        view_mat[:3, 3] = [
            -np.dot(x_axis, self._eye),
            -np.dot(y_axis, self._eye),
            -np.dot(z_axis, self._eye)
        ]
        
        glMultMatrixf(view_mat.T)

        # Cache view matrix for ray picking (as your original code did)
        self.view_matrix = view_mat
        
    # ── Ray picking ───────────────────────────────────────────────────────────

    def get_pick_ray(self, mouse_x: int, mouse_y: int):
        """
        Returns (ray_origin, ray_direction) in world space for the given
        screen pixel.
        """
        proj = np.array(glGetFloatv(GL_PROJECTION_MATRIX),
                        dtype=np.float64).reshape(4, 4)
        view = self.view_matrix

        ndc_x = (2.0 * mouse_x / config.WINDOW_WIDTH)  - 1.0
        ndc_y = 1.0 - (2.0 * mouse_y / config.WINDOW_HEIGHT)

        ray_clip = np.array([ndc_x, ndc_y, -1.0, 1.0])
        ray_eye  = np.linalg.inv(proj.T) @ ray_clip
        ray_eye  = np.array([ray_eye[0], ray_eye[1], -1.0, 0.0])
        ray_world = np.linalg.inv(view.T) @ ray_eye
        ray_dir   = ray_world[:3]
        nd = np.linalg.norm(ray_dir)
        if nd > 0:
            ray_dir /= nd
        return self._eye.copy(), ray_dir

    @property
    def eye_position(self) -> np.ndarray:
        return self._eye.copy()
