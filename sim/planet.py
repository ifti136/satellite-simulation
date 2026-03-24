"""
planet.py — Generic Planet class.

Replaces the separate earth.py / moon.py with one unified class driven
entirely by the PLANETS_DATA config dicts.  Earth's special day/night
shader is activated automatically when "night_texture" is present.

Each Planet owns:
  • solar_orbit  : Orbit around the Sun
  • moons        : list of Moon objects (orbiting this planet)
  • rings        : optional RingDisc object (Saturn etc.)
"""
import math
import numpy as np
from OpenGL.GL import *

import shaders
import config
from sphere_gen    import generate_sphere
from texture_loader import load_texture
from orbit         import Orbit


# ── helpers ───────────────────────────────────────────────────────────────────

def _rot_axis(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues rotation matrix (4×4) around an arbitrary axis."""
    ax = axis / (np.linalg.norm(axis) + 1e-12)
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = ax
    return np.array([
        [c+x*x*(1-c),   x*y*(1-c)-z*s, x*z*(1-c)+y*s, 0],
        [y*x*(1-c)+z*s, c+y*y*(1-c),   y*z*(1-c)-x*s, 0],
        [z*x*(1-c)-y*s, z*y*(1-c)+x*s, c+z*z*(1-c),   0],
        [0,             0,              0,              1],
    ], dtype=np.float32)


def _rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c,-s,0,0],[s,c,0,0],[0,0,1,0],[0,0,0,1]], dtype=np.float32)


def _rot_y(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]], dtype=np.float32)


def _safe_norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


# ── VBO helpers ───────────────────────────────────────────────────────────────

def _upload_vbos(verts, norms, uvs, indices):
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
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    return vbo_v, vbo_n, vbo_u, ibo, len(indices)


def _draw_vbos(vbo_v, vbo_n, vbo_u, ibo, index_count):
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_NORMAL_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_v); glVertexPointer(3, GL_FLOAT, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_n); glNormalPointer(GL_FLOAT, 0, None)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_u); glTexCoordPointer(2, GL_FLOAT, 0, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
    glDrawElements(GL_TRIANGLES, index_count, GL_UNSIGNED_INT, None)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisableClientState(GL_NORMAL_ARRAY)
    glDisableClientState(GL_VERTEX_ARRAY)


# ── Ring disc ─────────────────────────────────────────────────────────────────

class RingDisc:
    """Flat ring disc drawn as a triangle strip in the XZ plane."""

    SEGMENTS = 120

    def __init__(self, inner: float, outer: float,
                 tex_path: str, fallback_color=(0.88, 0.82, 0.62)):
        self._inner  = inner
        self._outer  = outer
        self._color  = fallback_color
        self._tex    = load_texture(f"textures/{tex_path}") if tex_path else 0
        self._shader = shaders.link_program(shaders.RING_VERT, shaders.RING_FRAG)
        self._u_tex      = glGetUniformLocation(self._shader, "u_ringTex")
        self._u_hasTex   = glGetUniformLocation(self._shader, "u_hasTexture")
        self._u_color    = glGetUniformLocation(self._shader, "u_ringColor")
        self._build_vbo()

    def _build_vbo(self):
        N = self.SEGMENTS
        verts, uvs, indices = [], [], []
        for i in range(N + 1):
            theta = 2 * math.pi * i / N
            ct, st = math.cos(theta), math.sin(theta)
            # inner vertex
            verts += [self._inner * ct, 0.0, self._inner * st]
            uvs   += [0.0, i / N]
            # outer vertex
            verts += [self._outer * ct, 0.0, self._outer * st]
            uvs   += [1.0, i / N]

        for i in range(N):
            b = i * 2
            indices += [b, b+1, b+2, b+1, b+3, b+2]

        self._vbo_v = glGenBuffers(1)
        self._vbo_u = glGenBuffers(1)
        self._ibo   = glGenBuffers(1)
        self._idx_count = len(indices)

        v = np.array(verts, dtype=np.float32)
        u = np.array(uvs,   dtype=np.float32)
        idx = np.array(indices, dtype=np.int32)

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v)
        glBufferData(GL_ARRAY_BUFFER, v.nbytes, v, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u)
        glBufferData(GL_ARRAY_BUFFER, u.nbytes, u, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, idx.nbytes, idx, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def draw(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_CULL_FACE)
        glDepthMask(GL_FALSE)

        glUseProgram(self._shader)
        glUniform1i(self._u_tex, 0)
        glUniform3f(self._u_color, *self._color)
        has = 1.0 if self._tex else 0.0
        glUniform1f(self._u_hasTex, has)
        if self._tex:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self._tex)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u)
        glTexCoordPointer(2, GL_FLOAT, 0, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glDrawElements(GL_TRIANGLES, self._idx_count, GL_UNSIGNED_INT, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        glUseProgram(0)
        if self._tex:
            glBindTexture(GL_TEXTURE_2D, 0)
        glDepthMask(GL_TRUE)
        glEnable(GL_CULL_FACE)
        glDisable(GL_BLEND)


# ── Moon (orbits a planet) ────────────────────────────────────────────────────

class Moon:
    def __init__(self, data: dict):
        self.name  = data["name"]
        self._r    = data["radius"]
        self._col  = data.get("color", (0.7, 0.7, 0.68))
        self.orbit = Orbit(
            radius      = data["orbit_radius"],
            inclination = data.get("inclination", 0.0),
            speed       = data["orbit_speed"],
            phase       = data.get("phase", 0.0),
        )
        verts, norms, uvs, indices = generate_sphere(32, 32, self._r)
        self._vbo_v, self._vbo_n, self._vbo_u, self._ibo, self._idx = \
            _upload_vbos(verts, norms, uvs, indices)
        tex_name = data.get("texture", "")
        self._tex    = load_texture(f"textures/{tex_name}") if tex_name else 0
        self._shader = shaders.link_program(shaders.PHONG_VERT, shaders.PHONG_FRAG)
        self._u_tex      = glGetUniformLocation(self._shader, "u_tex")
        self._u_lightDir = glGetUniformLocation(self._shader, "u_lightDir")
        self._u_color    = glGetUniformLocation(self._shader, "u_color")
        self._u_specPow  = glGetUniformLocation(self._shader, "u_specPow")
        self._u_hasTex   = glGetUniformLocation(self._shader, "u_hasTexture")
        self._u_ambBoost = glGetUniformLocation(self._shader, "u_ambientBoost")

    def update(self, dt: float) -> None:
        self.orbit.update(dt)

    @property
    def local_position(self) -> np.ndarray:
        return self.orbit.local_position()

    def world_position(self, planet_wp: np.ndarray) -> np.ndarray:
        return planet_wp + self.local_position

    def draw(self, planet_wp: np.ndarray, sun_eye_dir: np.ndarray) -> None:
        wp = self.world_position(planet_wp)
        glPushMatrix()
        glTranslatef(*wp.astype(float))
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform3f(self._u_color, *self._col)
        glUniform1f(self._u_specPow, 15.0)
        glUniform1f(self._u_ambBoost, 0.0)
        has = 1.0 if self._tex else 0.0
        glUniform1f(self._u_hasTex, has)
        if self._tex:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self._tex)
            glUniform1i(self._u_tex, 0)
        _draw_vbos(self._vbo_v, self._vbo_n, self._vbo_u, self._ibo, self._idx)
        if self._tex:
            glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glPopMatrix()


# ── Planet ────────────────────────────────────────────────────────────────────

class Planet:
    """
    One planet (Mercury … Neptune).
    Driven entirely by a PLANETS_DATA config dict.
    Earth's entry has "night_texture" which activates the day/night shader.
    """

    def __init__(self, data: dict, tex_dir: str = "textures"):
        self.name    = data["name"]
        self._data   = data
        self._radius = data["radius"]
        self._color  = data.get("color", (0.7, 0.7, 0.7))
        self._tilt   = math.radians(data.get("tilt", 0.0))
        self._rot_angle = 0.0
        self._is_earth  = "night_texture" in data

        # Solar orbit
        self.solar_orbit = Orbit(
            radius      = data["orbit_radius"],
            inclination = 0.0,
            speed       = data["orbit_speed"],
            phase       = data.get("phase", 0.0),
        )

        # Sphere geometry
        detail = 72 if self._is_earth else 48
        verts, norms, uvs, indices = generate_sphere(detail, detail, self._radius)
        self._vbo_v, self._vbo_n, self._vbo_u, self._ibo, self._idx = \
            _upload_vbos(verts, norms, uvs, indices)

        # Atmosphere shell (slightly larger sphere)
        atmo_r = self._radius * 1.06
        av, an, _, ai = generate_sphere(32, 32, atmo_r)
        self._atmo_vbo_v, self._atmo_vbo_n, _, self._atmo_ibo, self._atmo_idx = \
            _upload_vbos(av, an, np.zeros((len(av),2), np.float32), ai)

        # Textures
        tex_path = f"{tex_dir}/{data['texture']}"
        self._tex_day   = load_texture(tex_path)
        self._tex_night = load_texture(f"{tex_dir}/{data['night_texture']}") \
                          if self._is_earth else 0

        # Shaders
        if self._is_earth:
            self._shader     = shaders.link_program(shaders.EARTH_VERT, shaders.EARTH_FRAG)
            self._u_modelRot = glGetUniformLocation(self._shader, "u_modelRot")
            self._u_earthPos = glGetUniformLocation(self._shader, "u_earthPos")
            self._u_sunPos   = glGetUniformLocation(self._shader, "u_sunPos")
            self._u_camPos   = glGetUniformLocation(self._shader, "u_camPos")
            self._u_dayTex   = glGetUniformLocation(self._shader, "u_dayTex")
            self._u_nightTex = glGetUniformLocation(self._shader, "u_nightTex")
        else:
            self._shader     = shaders.link_program(shaders.PHONG_VERT, shaders.PHONG_FRAG)
            self._u_tex      = glGetUniformLocation(self._shader, "u_tex")
            self._u_lightDir = glGetUniformLocation(self._shader, "u_lightDir")
            self._u_color    = glGetUniformLocation(self._shader, "u_color")
            self._u_specPow  = glGetUniformLocation(self._shader, "u_specPow")
            self._u_hasTex   = glGetUniformLocation(self._shader, "u_hasTexture")
            self._u_ambBoost = glGetUniformLocation(self._shader, "u_ambientBoost")

        self._atmo_shader    = shaders.link_program(shaders.ATMO_VERT, shaders.ATMO_FRAG)
        self._atmo_col_loc   = glGetUniformLocation(self._atmo_shader, "u_color")
        self._atmo_alpha_loc = glGetUniformLocation(self._atmo_shader, "u_alpha")

        # Atmo colour depends on planet
        self._atmo_color = {
            "Earth":   (0.28, 0.62, 1.0),
            "Venus":   (0.90, 0.80, 0.50),
            "Mars":    (0.75, 0.45, 0.25),
            "Jupiter": (0.80, 0.70, 0.55),
            "Saturn":  (0.85, 0.78, 0.58),
            "Uranus":  (0.55, 0.85, 0.92),
            "Neptune": (0.30, 0.45, 0.90),
        }.get(self.name, (0.6, 0.6, 0.6))

        # Moons
        self.moons = [Moon(md) for md in data.get("moons", [])]

        # Rings
        self.rings = None
        if data.get("rings"):
            ri = data.get("ring_inner", 1.3) * self._radius
            ro = data.get("ring_outer", 2.2) * self._radius
            rt = data.get("ring_texture", "")
            self.rings = RingDisc(ri, ro, rt)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def world_position(self) -> np.ndarray:
        return self.solar_orbit.local_position()

    @property
    def model_matrix(self) -> np.ndarray:
        return _rot_z(self._tilt) @ _rot_y(self._rot_angle)

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.solar_orbit.update(dt)
        self._rot_angle += self._data["rot_speed"] * dt
        if self._rot_angle > 2 * math.pi:
            self._rot_angle -= 2 * math.pi
        for moon in self.moons:
            moon.update(dt)

    # ── Draw ───────────────────────────────────────────────────────────────────

    def draw(self, cam_pos: np.ndarray, sun_eye_dir: np.ndarray) -> None:
        wp = self.world_position
        mm = self.model_matrix

        glPushMatrix()
        glTranslatef(float(wp[0]), float(wp[1]), float(wp[2]))
        glMultMatrixf(mm.T)

        # Atmosphere
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        glCullFace(GL_FRONT)
        glUseProgram(self._atmo_shader)
        glUniform3f(self._atmo_col_loc, *self._atmo_color)
        glUniform1f(self._atmo_alpha_loc, 0.65)
        _draw_vbos(self._atmo_vbo_v, self._atmo_vbo_n,
                   np.zeros((1,), np.float32),    # uvs unused in atmo
                   self._atmo_ibo, self._atmo_idx)
        glCullFace(GL_BACK)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glUseProgram(0)

        # Planet body
        if self._is_earth:
            self._draw_earth(wp, mm, cam_pos)
        else:
            self._draw_phong(sun_eye_dir)

        glPopMatrix()

        # Rings (drawn in world space after planet pop)
        if self.rings is not None:
            glPushMatrix()
            glTranslatef(float(wp[0]), float(wp[1]), float(wp[2]))
            glRotatef(self._data.get("tilt", 0.0), 0, 0, 1)
            self.rings.draw()
            glPopMatrix()

        # Moons
        for moon in self.moons:
            moon.draw(wp, sun_eye_dir)

    def _draw_earth(self, wp, mm, cam_pos):
        glUseProgram(self._shader)
        glUniformMatrix4fv(self._u_modelRot, 1, GL_TRUE, mm)
        glUniform3f(self._u_earthPos, float(wp[0]), float(wp[1]), float(wp[2]))
        glUniform3f(self._u_sunPos, 0.0, 0.0, 0.0)
        glUniform3f(self._u_camPos, float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2]))
        glUniform1i(self._u_dayTex,   0)
        glUniform1i(self._u_nightTex, 1)
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, self._tex_day)
        glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D, self._tex_night)
        _draw_vbos(self._vbo_v, self._vbo_n, self._vbo_u, self._ibo, self._idx)
        glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D, 0)
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def _draw_phong(self, sun_eye_dir):
        glUseProgram(self._shader)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform3f(self._u_color, *self._color)
        glUniform1f(self._u_specPow, 25.0)
        glUniform1f(self._u_ambBoost, 0.0)
        has = 1.0 if self._tex_day else 0.0
        glUniform1f(self._u_hasTex, has)
        if self._tex_day:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self._tex_day)
            glUniform1i(self._u_tex, 0)
        _draw_vbos(self._vbo_v, self._vbo_n, self._vbo_u, self._ibo, self._idx)
        if self._tex_day:
            glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    # ── Convenience accessors ─────────────────────────────────────────────────

    def get_orbit(self):
        return self.solar_orbit

    def velocity_direction(self) -> np.ndarray:
        return self.solar_orbit.velocity_direction()
