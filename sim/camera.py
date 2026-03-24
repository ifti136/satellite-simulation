"""
camera.py — Three camera modes with smooth interpolation.
"""
import math
import numpy as np
from OpenGL.GL import *
import config


def _lerp3(a, b, t):
    return a + (b - a) * t


def _safe_norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


class Camera:
    def __init__(self):
        self.mode      = config.CAM_MODE_SOLAR
        self.sat_idx   = 0
        self.planet_idx = 2   # default: Earth

        self._eye    = np.array([0.0, 80.0, 80.0])
        self._centre = np.array([0.0,  0.0,  0.0])
        self._up     = np.array([0.0,  1.0,  0.0])
        self._t_eye    = self._eye.copy()
        self._t_centre = self._centre.copy()
        self._t_up     = self._up.copy()

        self._solar_yaw   = 0.0
        self._solar_pitch = 35.0
        self._solar_dist  = 100.0
        self._drag_active = False
        self._drag_last   = (0, 0)

        self.view_matrix = np.eye(4, dtype=np.float64)

    def handle_event(self, event) -> None:
        import pygame
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.mode = config.CAM_MODE_SOLAR
            elif event.key == pygame.K_2:
                self.mode = config.CAM_MODE_PLANET
            elif event.key == pygame.K_3:
                self.mode = config.CAM_MODE_SAT_TPP
            elif event.key == pygame.K_TAB:
                if self.mode == config.CAM_MODE_SAT_TPP:
                    self.sat_idx = (self.sat_idx + 1) % 3
                elif self.mode == config.CAM_MODE_PLANET:
                    self.planet_idx = (self.planet_idx + 1) % len(config.PLANETS_DATA)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.mode == config.CAM_MODE_SOLAR:
                self._drag_active = True
                self._drag_last   = event.pos
            elif event.button == 4:
                self._solar_dist = max(15.0, self._solar_dist - 6.0)
            elif event.button == 5:
                self._solar_dist = min(450.0, self._solar_dist + 6.0)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._drag_active = False
        elif event.type == pygame.MOUSEMOTION:
            if self._drag_active:
                dx = event.pos[0] - self._drag_last[0]
                dy = event.pos[1] - self._drag_last[1]
                self._solar_yaw   += dx * 0.4
                self._solar_pitch  = np.clip(self._solar_pitch - dy*0.3, 5, 85)
                self._drag_last    = event.pos

    def update(self, dt: float, planets, satellites) -> None:
        if self.mode == config.CAM_MODE_SOLAR:
            self._update_solar()
        elif self.mode == config.CAM_MODE_PLANET:
            planet = planets[self.planet_idx]
            self._update_planet_tpp(planet)
        elif self.mode == config.CAM_MODE_SAT_TPP:
            earth_wp = planets[2].world_position   # Earth is index 2
            sat = satellites[self.sat_idx]
            self._update_sat_tpp(sat, earth_wp)

        alpha = min(1.0, dt * 6.0)
        self._eye    = _lerp3(self._eye,    self._t_eye,    alpha)
        self._centre = _lerp3(self._centre, self._t_centre, alpha)
        self._up     = _lerp3(self._up,     self._t_up,     alpha)
        n = np.linalg.norm(self._up)
        if n > 1e-9: self._up /= n

    def _update_solar(self) -> None:
        yaw_r   = math.radians(self._solar_yaw)
        pitch_r = math.radians(self._solar_pitch)
        ex = self._solar_dist * math.cos(pitch_r) * math.sin(yaw_r)
        ey = self._solar_dist * math.sin(pitch_r)
        ez = self._solar_dist * math.cos(pitch_r) * math.cos(yaw_r)
        self._t_eye    = np.array([ex, ey, ez])
        self._t_centre = np.array([0.0, 0.0, 0.0])
        self._t_up     = np.array([0.0, 1.0, 0.0])

    def _update_planet_tpp(self, planet) -> None:
        wp  = planet.world_position
        fwd = planet.velocity_direction()
        r   = planet._radius

        # Camera sits above-and-behind the planet
        back_dist = r * 8.0
        up_dist   = r * 12.0
        self._t_eye    = wp + (-fwd * back_dist) + np.array([0, up_dist, 0])
        self._t_centre = wp
        self._t_up     = np.array([0.0, 1.0, 0.0])

    def _update_sat_tpp(self, sat, earth_wp: np.ndarray) -> None:
        wp  = sat.world_position(earth_wp)
        fwd = sat.velocity_direction()
        self._t_eye    = wp + (-fwd * 1.5) + np.array([0, 3.0, 0])
        self._t_centre = wp
        self._t_up     = np.array([0.0, 1.0, 0.0])

    def apply(self) -> None:
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        fov_rad = math.radians(config.FOV)
        aspect  = config.WINDOW_WIDTH / config.WINDOW_HEIGHT
        f       = 1.0 / math.tan(fov_rad / 2.0)
        zn, zf  = config.NEAR_CLIP, config.FAR_CLIP
        proj = np.array([
            [f/aspect, 0,  0,                    0],
            [0,        f,  0,                    0],
            [0,        0,  (zf+zn)/(zn-zf),      (2*zf*zn)/(zn-zf)],
            [0,        0, -1,                    0],
        ], dtype=np.float32)
        glMultMatrixf(proj.T)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        z_ax = _safe_norm(self._eye - self._centre)
        x_ax = _safe_norm(np.cross(self._up, z_ax))
        y_ax = np.cross(z_ax, x_ax)
        vm = np.eye(4, dtype=np.float64)
        vm[0,:3] = x_ax; vm[0,3] = -np.dot(x_ax, self._eye)
        vm[1,:3] = y_ax; vm[1,3] = -np.dot(y_ax, self._eye)
        vm[2,:3] = z_ax; vm[2,3] = -np.dot(z_ax, self._eye)
        glMultMatrixf(vm.T)
        self.view_matrix = vm

    def get_pick_ray(self, mouse_x: int, mouse_y: int):
        proj_col = np.array(glGetFloatv(GL_PROJECTION_MATRIX),
                            dtype=np.float64).reshape(4,4)
        proj = proj_col.T
        ndc_x = (2.0 * mouse_x / config.WINDOW_WIDTH)  - 1.0
        ndc_y = 1.0 - (2.0 * mouse_y / config.WINDOW_HEIGHT)
        inv_proj = np.linalg.inv(proj)
        ray_clip = np.array([ndc_x, ndc_y, -1.0, 1.0])
        ray_eye_h = inv_proj @ ray_clip
        ray_eye   = np.array([ray_eye_h[0], ray_eye_h[1], -1.0, 0.0])
        inv_view  = np.linalg.inv(self.view_matrix)
        ray_world = inv_view @ ray_eye
        return self._eye.copy(), _safe_norm(ray_world[:3])

    @property
    def eye_position(self) -> np.ndarray:
        return self._eye.copy()
