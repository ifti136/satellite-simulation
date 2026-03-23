"""
satellite.py — ISS, Hubble, and Starlink satellite models.

Each satellite is rendered using OpenGL immediate-mode geometry
(box body + solar panel quads) with Phong shading.
A fading orbit trail is drawn as a line strip.
"""
import math
import numpy as np
from OpenGL.GL import *
from ctypes import c_void_p

import shaders
import config
from orbit import Orbit


# ── Geometry helpers ────────────────────────────────────────────────────────────

def _box_normals_verts(sx, sy, sz):
    """Return flat list of (normal, vertex) pairs forming a box."""
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    faces = [
        # normal        vertices (4 per face)
        (( 0, 0, 1),  [(-hx,-hy, hz),( hx,-hy, hz),( hx, hy, hz),(-hx, hy, hz)]),
        (( 0, 0,-1),  [( hx,-hy,-hz),(-hx,-hy,-hz),(-hx, hy,-hz),( hx, hy,-hz)]),
        (( 1, 0, 0),  [( hx,-hy, hz),( hx,-hy,-hz),( hx, hy,-hz),( hx, hy, hz)]),
        ((-1, 0, 0),  [(-hx,-hy,-hz),(-hx,-hy, hz),(-hx, hy, hz),(-hx, hy,-hz)]),
        (( 0, 1, 0),  [(-hx, hy, hz),( hx, hy, hz),( hx, hy,-hz),(-hx, hy,-hz)]),
        (( 0,-1, 0),  [(-hx,-hy,-hz),( hx,-hy,-hz),( hx,-hy, hz),(-hx,-hy, hz)]),
    ]
    return faces


def _draw_box(sx, sy, sz):
    for (nx, ny, nz), verts in _box_normals_verts(sx, sy, sz):
        glBegin(GL_QUADS)
        glNormal3f(nx, ny, nz)
        for v in verts:
            glVertex3f(*v)
        glEnd()


def _draw_panel(w, h, nx, ny, nz):
    """Flat quad (solar panel)."""
    hw, hh = w / 2, h / 2
    glBegin(GL_QUADS)
    glNormal3f(nx, ny, nz)
    glVertex3f(-hw, -hh, 0); glVertex3f( hw, -hh, 0)
    glVertex3f( hw,  hh, 0); glVertex3f(-hw,  hh, 0)
    glNormal3f(-nx, -ny, -nz)
    glVertex3f(-hw,  hh, 0); glVertex3f( hw,  hh, 0)
    glVertex3f( hw, -hh, 0); glVertex3f(-hw, -hh, 0)
    glEnd()


# ── Base Satellite class ────────────────────────────────────────────────────────

class Satellite:
    """Abstract base for all satellites."""

    TRAIL_LEN = 120     # number of positions kept for trail

    def __init__(self, name: str, orbit: Orbit):
        self.name  = name
        self.orbit = orbit
        self.data  = config.SATELLITES_DATA[name]

        self._trail: list = []          # world positions
        self._panel_angle = 0.0        # slow spin of solar panels

        # Phong shader (no texture – use colour)
        self._shader     = shaders.link_program(shaders.PHONG_VERT, shaders.PHONG_FRAG)
        self._u_tex      = glGetUniformLocation(self._shader, "u_tex")
        self._u_lightDir = glGetUniformLocation(self._shader, "u_lightDir")
        self._u_color    = glGetUniformLocation(self._shader, "u_color")
        self._u_specPow  = glGetUniformLocation(self._shader, "u_specPow")
        self._u_hasTex   = glGetUniformLocation(self._shader, "u_hasTexture")

    # ── Computed properties ──────────────────────────────────────────────────

    def local_position(self) -> np.ndarray:
        return self.orbit.local_position()

    def world_position(self, earth_world: np.ndarray) -> np.ndarray:
        return earth_world + self.local_position()

    def velocity_direction(self) -> np.ndarray:
        return self.orbit.velocity_direction()

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt: float, earth_world: np.ndarray) -> None:
        self.orbit.update(dt)
        self._panel_angle += dt * 0.3
        wp = self.world_position(earth_world)
        self._trail.append(wp.copy())
        if len(self._trail) > self.TRAIL_LEN:
            self._trail.pop(0)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, earth_world: np.ndarray, sun_eye_dir: np.ndarray) -> None:
        wp = self.world_position(earth_world)
        fwd = self.velocity_direction()        # orbit tangent  (+X if 0°)
        up  = np.array([0.0, 1.0, 0.0])
        right = np.cross(fwd, up)
        right_n = right / (np.linalg.norm(right) + 1e-9)
        up_n    = np.cross(right_n, fwd)

        # Build orientation matrix aligning satellite to orbit direction
        R = np.eye(4, dtype=np.float64)
        R[:3, 0] = fwd
        R[:3, 1] = up_n
        R[:3, 2] = right_n

        # Draw orbit trail
        self._draw_trail()

        # Draw satellite body
        glPushMatrix()
        glTranslatef(*wp)
        glMultMatrixd(R.T)     # column-major
        self._draw_body(sun_eye_dir)
        glPopMatrix()

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        """Subclasses implement satellite-specific geometry."""
        raise NotImplementedError

    def _set_material(self, r, g, b, spec: float = 60.0) -> None:
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir_global)
        glUniform3f(self._u_color,    r, g, b)
        glUniform1f(self._u_specPow,  spec)
        glUniform1f(self._u_hasTex,   0.0)

    def _draw_trail(self) -> None:
        if len(self._trail) < 2:
            return
        glDisable(GL_DEPTH_TEST)
        glLineWidth(1.2)
        glBegin(GL_LINE_STRIP)
        n = len(self._trail)
        for i, p in enumerate(self._trail):
            alpha = i / n
            r, g, b = self.data["panel_color"]
            glColor4f(r, g, b, alpha * 0.6)
            glVertex3f(*p)
        glEnd()
        glEnable(GL_DEPTH_TEST)
        glColor4f(1, 1, 1, 1)

    # Click detection ─────────────────────────────────────────────────────────

    def is_hit_by_ray(self, ray_origin: np.ndarray, ray_dir: np.ndarray,
                      earth_world: np.ndarray, radius: float = 0.25) -> bool:
        """Fast sphere-ray intersection for click picking."""
        centre = self.world_position(earth_world)
        oc = ray_origin - centre
        b  = 2.0 * np.dot(oc, ray_dir)
        c  = np.dot(oc, oc) - radius ** 2
        return (b * b - 4 * c) > 0


# ── Global for material helper (set before draw call from scene) ──────────────
sun_eye_dir_global = np.array([1.0, 0.0, 0.0], dtype=np.float32)


# ── ISS ──────────────────────────────────────────────────────────────────────

class ISS(Satellite):
    def __init__(self):
        super().__init__(
            "ISS",
            Orbit(config.ISS_ORBIT_RADIUS, 51.6, config.ISS_ORBIT_SPEED, phase=0.0),
        )

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        body_col   = self.data["color"]
        panel_col  = self.data["panel_color"]

        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform1f(self._u_hasTex, 0.0)
        glUniform1f(self._u_specPow, 80.0)

        # Central truss (long beam)
        glUniform3f(self._u_color, *body_col)
        _draw_box(1.4, 0.05, 0.05)

        # Habitation module
        glPushMatrix(); glTranslatef(0, 0, 0)
        glUniform3f(self._u_color, 0.90, 0.90, 0.88)
        _draw_box(0.22, 0.18, 0.18)
        glPopMatrix()

        # 4 large solar panel pairs along truss
        for side in [-1, 1]:
            for station in [-0.55, -0.2, 0.2, 0.55]:
                glPushMatrix()
                glTranslatef(station * 1.3, 0.06, side * 0.25)
                glRotatef(math.degrees(self._panel_angle * 0.1), 1, 0, 0)
                glUniform3f(self._u_color, *panel_col)
                _draw_panel(0.45, 0.18, 0, 0, 1)
                glPopMatrix()

        glUseProgram(0)


# ── Hubble ───────────────────────────────────────────────────────────────────

class Hubble(Satellite):
    def __init__(self):
        super().__init__(
            "Hubble",
            Orbit(config.HUBBLE_ORBIT_RADIUS, 28.5, config.HUBBLE_ORBIT_SPEED, phase=math.pi * 0.7),
        )

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        body_col  = self.data["color"]
        panel_col = self.data["panel_color"]

        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform1f(self._u_hasTex, 0.0)
        glUniform1f(self._u_specPow, 55.0)

        # Cylindrical body (approximated with rectangular prisms)
        glUniform3f(self._u_color, *body_col)
        _draw_box(0.14, 0.14, 0.50)   # main tube

        # Mirror aperture
        glPushMatrix(); glTranslatef(0, 0, 0.27)
        glUniform3f(self._u_color, 0.25, 0.25, 0.25)
        _draw_box(0.10, 0.10, 0.04)
        glPopMatrix()

        # Two solar panels
        for side in [-1, 1]:
            glPushMatrix()
            glTranslatef(side * 0.24, 0, 0)
            glRotatef(math.degrees(self._panel_angle * 0.08), 0, 0, 1)
            glUniform3f(self._u_color, *panel_col)
            _draw_panel(0.22, 0.42, 0, 1, 0)
            glPopMatrix()

        glUseProgram(0)


# ── Starlink ──────────────────────────────────────────────────────────────────

class Starlink(Satellite):
    def __init__(self):
        super().__init__(
            "Starlink",
            Orbit(config.STARLINK_ORBIT_RADIUS, 53.0, config.STARLINK_ORBIT_SPEED, phase=math.pi * 1.4),
        )

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        body_col  = self.data["color"]
        panel_col = self.data["panel_color"]

        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform1f(self._u_hasTex, 0.0)
        glUniform1f(self._u_specPow, 90.0)

        # Flat body
        glUniform3f(self._u_color, *body_col)
        _draw_box(0.28, 0.06, 0.14)

        # Single wide solar array (one side)
        glPushMatrix()
        glTranslatef(0.32, 0, 0)
        glRotatef(math.degrees(self._panel_angle * 0.15), 1, 0, 0)
        glUniform3f(self._u_color, *panel_col)
        _draw_panel(0.55, 0.12, 0, 1, 0)
        glPopMatrix()

        # Small antenna dish
        glPushMatrix(); glTranslatef(0, 0.06, 0)
        glUniform3f(self._u_color, 0.9, 0.9, 0.9)
        _draw_box(0.10, 0.01, 0.10)
        glPopMatrix()

        glUseProgram(0)
