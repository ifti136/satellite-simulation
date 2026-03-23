"""
earth.py — Earth with day/night GLSL shader, atmosphere glow, and axis tilt.
Earth orbits the Sun; the Moon and satellites orbit Earth.
"""
import math
import numpy as np
from OpenGL.GL import *

import shaders
import config
from sphere_gen import generate_sphere
from texture_loader import load_texture
from orbit import Orbit


def _rot_y(a: float) -> np.ndarray:
    """4×4 rotation matrix around Y axis."""
    c, s = math.cos(a), math.sin(a)
    return np.array([
        [ c, 0,  s, 0],
        [ 0, 1,  0, 0],
        [-s, 0,  c, 0],
        [ 0, 0,  0, 1],
    ], dtype=np.float32)


def _rot_z(a: float) -> np.ndarray:
    """4×4 rotation matrix around Z axis."""
    c, s = math.cos(a), math.sin(a)
    return np.array([
        [c, -s, 0, 0],
        [s,  c, 0, 0],
        [0,  0, 1, 0],
        [0,  0, 0, 1],
    ], dtype=np.float32)


AXIS_TILT = math.radians(23.4)   # Earth's obliquity


class Earth:
    def __init__(self, tex_dir: str = "textures"):
        # Solar orbit (Earth around Sun)
        self.solar_orbit = Orbit(
            radius=config.SUN_DISTANCE,
            inclination=0.0,
            speed=config.EARTH_ORBIT_SPEED,
            phase=0.0,
        )
        self.rotation_angle = 0.0    # spin around axis

        # Build VBOs
        verts, norms, uvs, indices = generate_sphere(72, 72, config.EARTH_RADIUS)
        self._index_count = len(indices)
        self._vbo_v, self._vbo_n, self._vbo_u = glGenBuffers(3)
        self._ibo = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_n)
        glBufferData(GL_ARRAY_BUFFER, norms.nbytes, norms, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u)
        glBufferData(GL_ARRAY_BUFFER, uvs.nbytes,   uvs,   GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        # Textures
        self._tex_day   = load_texture(f"{tex_dir}/earth_day.png")
        self._tex_night = load_texture(f"{tex_dir}/earth_night.png")

        # Earth shader
        self._shader = shaders.link_program(shaders.EARTH_VERT, shaders.EARTH_FRAG)
        self._u_modelRot  = glGetUniformLocation(self._shader, "u_modelRot")
        self._u_earthPos  = glGetUniformLocation(self._shader, "u_earthPos")
        self._u_sunPos    = glGetUniformLocation(self._shader, "u_sunPos")
        self._u_camPos    = glGetUniformLocation(self._shader, "u_camPos")
        self._u_dayTex    = glGetUniformLocation(self._shader, "u_dayTex")
        self._u_nightTex  = glGetUniformLocation(self._shader, "u_nightTex")

        # Atmosphere glow
        self._atmo_shader    = shaders.link_program(shaders.ATMO_VERT, shaders.ATMO_FRAG)
        self._atmo_col_loc   = glGetUniformLocation(self._atmo_shader, "u_color")
        self._atmo_alpha_loc = glGetUniformLocation(self._atmo_shader, "u_alpha")

        # Build atmo VBOs (slightly larger sphere)
        av, an, au, ai = generate_sphere(48, 48, config.EARTH_RADIUS * 1.07)
        self._atmo_index_count = len(ai)
        self._atmo_vbo_v, self._atmo_vbo_n = glGenBuffers(2)
        self._atmo_ibo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._atmo_vbo_v)
        glBufferData(GL_ARRAY_BUFFER, av.nbytes, av, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self._atmo_vbo_n)
        glBufferData(GL_ARRAY_BUFFER, an.nbytes, an, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._atmo_ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, ai.nbytes, ai, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def world_position(self) -> np.ndarray:
        return self.solar_orbit.local_position()

    @property
    def model_matrix(self) -> np.ndarray:
        """Combined rotation matrix for Earth's axis tilt + spin."""
        return _rot_z(AXIS_TILT) @ _rot_y(self.rotation_angle)

    # ── Update ─────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.solar_orbit.update(dt)
        self.rotation_angle = (self.rotation_angle + config.EARTH_ROTATION_SPEED * dt) % (2 * math.pi)

    # ── Draw ───────────────────────────────────────────────────────────────────

    def draw(self, cam_pos: np.ndarray) -> None:
        wp = self.world_position
        mm = self.model_matrix

        glPushMatrix()
        glTranslatef(float(wp[0]), float(wp[1]), float(wp[2]))
        # Apply tilt + spin via matrix multiply
        glMultMatrixf(mm.T)   # OpenGL column-major

        # ── Atmosphere (rim-glow) ─────────────────────────────────────────────
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        glCullFace(GL_FRONT)

        glUseProgram(self._atmo_shader)
        glUniform3f(self._atmo_col_loc, 0.30, 0.65, 1.0)
        glUniform1f(self._atmo_alpha_loc, 0.70)
        self._render_atmo()

        glCullFace(GL_BACK)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glUseProgram(0)

        # ── Earth body ────────────────────────────────────────────────────────
        glUseProgram(self._shader)

        # Supply uniforms
        glUniformMatrix4fv(self._u_modelRot, 1, GL_TRUE, mm)
        glUniform3f(self._u_earthPos, float(wp[0]), float(wp[1]), float(wp[2]))
        glUniform3f(self._u_sunPos,   0.0, 0.0, 0.0)
        glUniform3f(self._u_camPos,   float(cam_pos[0]),
                                       float(cam_pos[1]),
                                       float(cam_pos[2]))

        glUniform1i(self._u_dayTex,   0)
        glUniform1i(self._u_nightTex, 1)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._tex_day)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self._tex_night)

        self._render_vbo()

        glActiveTexture(GL_TEXTURE1); glBindTexture(GL_TEXTURE_2D, 0)
        glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glPopMatrix()

    # ── Internal VBO helpers ───────────────────────────────────────────────────

    def _render_vbo(self) -> None:
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)

        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_n)
        glNormalPointer(GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u)
        glTexCoordPointer(2, GL_FLOAT, 0, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glDrawElements(GL_TRIANGLES, self._index_count, GL_UNSIGNED_INT, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

    def _render_atmo(self) -> None:
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glBindBuffer(GL_ARRAY_BUFFER, self._atmo_vbo_v)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._atmo_vbo_n)
        glNormalPointer(GL_FLOAT, 0, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._atmo_ibo)
        glDrawElements(GL_TRIANGLES, self._atmo_index_count, GL_UNSIGNED_INT, None)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
