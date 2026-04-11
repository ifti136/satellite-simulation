"""
satellite.py — ISS, Hubble, TDRS satellites.

Architecture
------------
  Satellite        — abstract base (orbit, trail, picking, shader setup)
  ModelSatellite   — renders from a loaded OBJ model
  FallbackXxx      — renders procedural geometry when no OBJ is present
  ISS / Hubble / TDRS — concrete classes, auto-pick model or fallback

The factory function make_satellite(name) returns the correct concrete type.

FallbackTDRS's parabolic dish fan uses the Midpoint Circle Algorithm via
midpoint_circle.circle_points() instead of per-vertex math.sin/cos.
"""
import math
import collections
import numpy as np
from OpenGL.GL import *

import shaders
import config
from orbit           import Orbit
from model_loader    import load_obj, _auto_scale
from midpoint_circle import circle_points


# ── Global sun direction (updated by scene.py each frame) ────────────────────
sun_eye_dir_global = np.array([1.0, 0.0, 0.0], dtype=np.float32)


# ── VBO helpers ───────────────────────────────────────────────────────────────

def _upload(verts, norms, uvs, indices):
    vbo_v, vbo_n, vbo_u = glGenBuffers(3)
    ibo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_v)
    glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_n)
    glBufferData(GL_ARRAY_BUFFER, norms.nbytes, norms, GL_STATIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_u)
    glBufferData(GL_ARRAY_BUFFER, uvs.nbytes,   uvs,   GL_STATIC_DRAW)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
    return vbo_v, vbo_n, vbo_u, ibo


def _render(vbo_v, vbo_n, vbo_u, ibo, idx_count):
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_v); glVertexPointer(3, GL_FLOAT, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_n); glNormalPointer(GL_FLOAT, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_u); glTexCoordPointer(2, GL_FLOAT, 0, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
    glDrawElements(GL_TRIANGLES, idx_count, GL_UNSIGNED_INT, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisableClientState(GL_NORMAL_ARRAY)
    glDisableClientState(GL_VERTEX_ARRAY)


# ── Fallback geometry helpers ─────────────────────────────────────────────────

def _draw_box(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2
    faces = [
        (( 0, 0, 1),[(-hx,-hy, hz),( hx,-hy, hz),( hx, hy, hz),(-hx, hy, hz)]),
        (( 0, 0,-1),[( hx,-hy,-hz),(-hx,-hy,-hz),(-hx, hy,-hz),( hx, hy,-hz)]),
        (( 1, 0, 0),[( hx,-hy, hz),( hx,-hy,-hz),( hx, hy,-hz),( hx, hy, hz)]),
        ((-1, 0, 0),[(-hx,-hy,-hz),(-hx,-hy, hz),(-hx, hy, hz),(-hx, hy,-hz)]),
        (( 0, 1, 0),[(-hx, hy, hz),( hx, hy, hz),( hx, hy,-hz),(-hx, hy,-hz)]),
        (( 0,-1, 0),[(-hx,-hy,-hz),( hx,-hy,-hz),( hx,-hy, hz),(-hx,-hy, hz)]),
    ]
    for (nx,ny,nz), vs in faces:
        glBegin(GL_QUADS)
        glNormal3f(nx,ny,nz)
        for v in vs: glVertex3f(*v)
        glEnd()


def _draw_panel(w, h, nx, ny, nz):
    hw, hh = w/2, h/2
    glBegin(GL_QUADS)
    glNormal3f( nx, ny, nz)
    glVertex3f(-hw,-hh,0); glVertex3f(hw,-hh,0)
    glVertex3f( hw, hh,0); glVertex3f(-hw, hh,0)
    glNormal3f(-nx,-ny,-nz)
    glVertex3f(-hw, hh,0); glVertex3f(hw, hh,0)
    glVertex3f( hw,-hh,0); glVertex3f(-hw,-hh,0)
    glEnd()


# ── Abstract base ─────────────────────────────────────────────────────────────

class Satellite:
    TRAIL_LEN = 140

    def __init__(self, name: str):
        self.name  = name
        self.data  = config.SATELLITES_DATA[name]
        self.orbit = Orbit(
            radius      = self.data["orbit_radius"],
            inclination = self.data["inclination"],
            speed       = self.data["orbit_speed"],
            phase       = self.data.get("phase", 0.0),
        )
        self._trail: collections.deque = collections.deque(maxlen=self.TRAIL_LEN)
        self._panel_angle = 0.0

        self._shader     = shaders.link_program(shaders.PHONG_VERT, shaders.PHONG_FRAG)
        self._u_tex      = glGetUniformLocation(self._shader, "u_tex")
        self._u_lightDir = glGetUniformLocation(self._shader, "u_lightDir")
        self._u_color    = glGetUniformLocation(self._shader, "u_color")
        self._u_specPow  = glGetUniformLocation(self._shader, "u_specPow")
        self._u_hasTex   = glGetUniformLocation(self._shader, "u_hasTexture")
        self._u_ambBoost = glGetUniformLocation(self._shader, "u_ambientBoost")

    # ── Position / kinematics ─────────────────────────────────────────────────

    def local_position(self) -> np.ndarray:
        return self.orbit.local_position()

    def world_position(self, earth_wp: np.ndarray) -> np.ndarray:
        return earth_wp + self.local_position()

    def velocity_direction(self) -> np.ndarray:
        return self.orbit.velocity_direction()

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float, earth_wp: np.ndarray) -> None:
        self.orbit.update(dt)
        self._panel_angle += dt * 0.3
        self._trail.append(self.world_position(earth_wp).copy())

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, earth_wp: np.ndarray, sun_eye_dir: np.ndarray) -> None:
        wp  = self.world_position(earth_wp)
        fwd = self.velocity_direction()
        up  = np.array([0.0, 1.0, 0.0])
        right = np.cross(fwd, up)
        rn = np.linalg.norm(right)
        right = right / (rn + 1e-9)
        up_n  = np.cross(right, fwd)

        R = np.eye(4, dtype=np.float64)
        R[:3,0] = fwd; R[:3,1] = up_n; R[:3,2] = right

        self._draw_trail()
        glPushMatrix()
        glTranslatef(*wp.astype(float))
        glMultMatrixd(R.T)
        self._draw_body(sun_eye_dir)
        glPopMatrix()

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        raise NotImplementedError

    def _draw_trail(self) -> None:
        if len(self._trail) < 2:
            return
        glDisable(GL_DEPTH_TEST)
        glLineWidth(1.2)
        glBegin(GL_LINE_STRIP)
        n = len(self._trail)
        r, g, b = self.data["panel_color"]
        for i, p in enumerate(self._trail):
            glColor4f(r, g, b, (i / n) * 0.7)
            glVertex3f(*p)
        glEnd()
        glEnable(GL_DEPTH_TEST)
        glColor4f(1, 1, 1, 1)

    def is_hit_by_ray(self, ray_origin, ray_dir, earth_wp, radius=0.25) -> bool:
        c  = self.world_position(earth_wp)
        oc = ray_origin - c
        b  = 2.0 * np.dot(oc, ray_dir)
        c2 = np.dot(oc, oc) - radius**2
        return (b*b - 4*c2) > 0


# ── Model-based satellite ─────────────────────────────────────────────────────

class ModelSatellite(Satellite):
    """Renders an OBJ model scaled to fit within a unit sphere."""

    def __init__(self, name: str):
        super().__init__(name)
        model_path = self.data.get("model", "")
        verts, norms, uvs, indices = load_obj(model_path)
        verts = _auto_scale(verts, target_radius=0.4)
        self._vbo_v, self._vbo_n, self._vbo_u, self._ibo = _upload(verts, norms, uvs, indices)
        self._idx_count = len(indices)

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform3f(self._u_color, *self.data["color"])
        glUniform1f(self._u_specPow, 70.0)
        glUniform1f(self._u_hasTex,  0.0)
        glUniform1f(self._u_ambBoost, 0.05)
        _render(self._vbo_v, self._vbo_n, self._vbo_u, self._ibo, self._idx_count)
        glUseProgram(0)


# ── Fallback procedural satellites ───────────────────────────────────────────

class FallbackISS(Satellite):
    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform1f(self._u_hasTex,   0.0)
        glUniform1f(self._u_specPow,  80.0)
        glUniform1f(self._u_ambBoost, 0.0)

        glUniform3f(self._u_color, *self.data["color"])
        _draw_box(1.4, 0.05, 0.05)

        glPushMatrix(); glTranslatef(0,0,0)
        glUniform3f(self._u_color, 0.90,0.90,0.88)
        _draw_box(0.22,0.18,0.18); glPopMatrix()

        for side in [-1,1]:
            for st in [-0.55,-0.2,0.2,0.55]:
                glPushMatrix()
                glTranslatef(st*1.3, 0.06, side*0.25)
                glRotatef(math.degrees(self._panel_angle*0.1),1,0,0)
                glUniform3f(self._u_color, *self.data["panel_color"])
                _draw_panel(0.45,0.18,0,0,1); glPopMatrix()
        glUseProgram(0)


class FallbackHubble(Satellite):
    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform1f(self._u_hasTex,   0.0)
        glUniform1f(self._u_specPow,  55.0)
        glUniform1f(self._u_ambBoost, 0.0)

        glUniform3f(self._u_color, *self.data["color"])
        _draw_box(0.14,0.14,0.50)

        glPushMatrix(); glTranslatef(0,0,0.27)
        glUniform3f(self._u_color, 0.25,0.25,0.25)
        _draw_box(0.10,0.10,0.04); glPopMatrix()

        for side in [-1,1]:
            glPushMatrix(); glTranslatef(side*0.24,0,0)
            glRotatef(math.degrees(self._panel_angle*0.08),0,0,1)
            glUniform3f(self._u_color, *self.data["panel_color"])
            _draw_panel(0.22,0.42,0,1,0); glPopMatrix()
        glUseProgram(0)


class FallbackTDRS(Satellite):
    """
    TDRS procedural geometry.

    Layout (in satellite-local space, X = forward along orbit):
      • Central hexagonal bus — approximated as a compact cube
      • Two large parabolic dish antennas (SSA / MA) on booms fore and aft,
        approximated as shallow octagonal dish faces (flat panel + small hub)
      • Two solar array wings extending left/right (±Z) from the bus,
        each made of two panel segments with a slow tracking rotation
      • One omni antenna stub on top (+Y)

    The dish rim circle (GL_TRIANGLE_FAN) uses MCA-derived points via
    circle_points() — replacing the original math.cos/sin per-vertex loop.
    """

    # Number of sides used to approximate the dish rim
    _DISH_SEGS = 8

    # Pre-compute dish rim points once at class level (shared across instances).
    # circle_points(N) returns (cos_θ, sin_θ) for N uniform angles via MCA.
    _DISH_PTS: list[tuple[float, float]] = circle_points(_DISH_SEGS) + \
                                           [circle_points(_DISH_SEGS)[0]]  # close fan

    def _draw_body(self, sun_eye_dir: np.ndarray) -> None:
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform1f(self._u_hasTex,   0.0)
        glUniform1f(self._u_specPow,  75.0)
        glUniform1f(self._u_ambBoost, 0.03)

        body_col  = self.data["color"]
        panel_col = self.data["panel_color"]
        dish_col  = (0.92, 0.92, 0.90)
        hub_col   = (0.55, 0.55, 0.55)

        # ── Central bus ───────────────────────────────────────────────────────
        glUniform3f(self._u_color, *body_col)
        _draw_box(0.20, 0.20, 0.20)

        # ── Omni antenna stub (top) ───────────────────────────────────────────
        glPushMatrix()
        glTranslatef(0.0, 0.12, 0.0)
        glUniform3f(self._u_color, *hub_col)
        _draw_box(0.02, 0.06, 0.02)
        glPopMatrix()

        # ── Solar array wings ─────────────────────────────────────────────────
        wing_rot = math.degrees(self._panel_angle * 0.08)
        for side in (-1, 1):
            glPushMatrix()
            glTranslatef(0.0, 0.0, side * 0.18)
            glRotatef(wing_rot, 0, 0, 1)
            glPushMatrix()
            glTranslatef(0.0, 0.0, side * 0.18)
            glUniform3f(self._u_color, *panel_col)
            _draw_panel(0.38, 0.14, 0, 1, 0)
            glPopMatrix()
            glPushMatrix()
            glTranslatef(0.0, 0.0, side * 0.40)
            glUniform3f(self._u_color, *panel_col)
            _draw_panel(0.38, 0.14, 0, 1, 0)
            glPopMatrix()
            glPopMatrix()

        # ── Dish antennas on booms (fore +X, aft -X) ─────────────────────────
        dish_r     = 0.20
        dish_depth = 0.06

        for sign, boom_len in ((1, 0.28), (-1, 0.28)):
            # Boom strut
            glPushMatrix()
            glTranslatef(sign * 0.10, 0.0, 0.0)
            glUniform3f(self._u_color, *hub_col)
            _draw_box(boom_len, 0.015, 0.015)
            glPopMatrix()

            # Dish hub
            dish_x = sign * (0.10 + boom_len * 0.5 + 0.02)
            glPushMatrix()
            glTranslatef(dish_x, 0.0, 0.0)
            glUniform3f(self._u_color, *hub_col)
            _draw_box(0.04, 0.04, 0.04)
            glPopMatrix()

            # Dish reflector — MCA-derived octagonal fan
            # _DISH_PTS gives (cos_θ, sin_θ) for each rim vertex, computed
            # once at class definition via circle_points().  No trig here.
            glUniform3f(self._u_color, *dish_col)
            nx = float(sign)
            glBegin(GL_TRIANGLE_FAN)
            # Centre vertex (recessed to suggest parabolic depth)
            glNormal3f(nx, 0.0, 0.0)
            glVertex3f(dish_x - sign * dish_depth, 0.0, 0.0)
            # Rim vertices from MCA lookup
            for (cos_t, sin_t) in self._DISH_PTS:
                cy = dish_r * cos_t
                cz = dish_r * sin_t
                glNormal3f(nx * 0.7, cos_t * 0.3, sin_t * 0.3)
                glVertex3f(dish_x, cy, cz)
            glEnd()

        glUseProgram(0)


# ── Factory ───────────────────────────────────────────────────────────────────

_FALLBACKS = {"ISS": FallbackISS, "Hubble": FallbackHubble, "TDRS": FallbackTDRS}


def make_satellite(name: str) -> Satellite:
    """
    Try to load the OBJ model. If the file does not exist, transparently
    fall back to the hand-coded procedural geometry.
    """
    import os
    model_path = config.SATELLITES_DATA[name].get("model", "")
    if model_path and os.path.exists(model_path):
        print(f"[satellite] Using 3D model for {name}: {model_path}")
        return ModelSatellite(name)
    else:
        print(f"[satellite] No model found for {name} — using fallback geometry")
        return _FALLBACKS[name](name)
