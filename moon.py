"""
moon.py — Moon object orbiting Earth.
"""
import math
import numpy as np
from OpenGL.GL import *

import shaders
import config
from sphere_gen import generate_sphere
from texture_loader import load_texture
from orbit import Orbit


class Moon:
    def __init__(self, tex_dir: str = "textures"):
        self.orbit = Orbit(
            radius=config.MOON_ORBIT_RADIUS,
            inclination=5.1,
            speed=config.MOON_ORBIT_SPEED,
            phase=math.pi * 0.3,
        )

        # VBOs
        verts, norms, uvs, indices = generate_sphere(48, 48, config.MOON_RADIUS)
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

        self._tex    = load_texture(f"{tex_dir}/moon.png")
        self._shader = shaders.link_program(shaders.PHONG_VERT, shaders.PHONG_FRAG)

        self._u_tex      = glGetUniformLocation(self._shader, "u_tex")
        self._u_lightDir = glGetUniformLocation(self._shader, "u_lightDir")
        self._u_color    = glGetUniformLocation(self._shader, "u_color")
        self._u_specPow  = glGetUniformLocation(self._shader, "u_specPow")
        self._u_hasTex   = glGetUniformLocation(self._shader, "u_hasTexture")

    @property
    def local_position(self) -> np.ndarray:
        return self.orbit.local_position()

    def world_position(self, earth_world: np.ndarray) -> np.ndarray:
        return earth_world + self.local_position

    def update(self, dt: float) -> None:
        self.orbit.update(dt)

    def draw(self, earth_world: np.ndarray, sun_eye_dir: np.ndarray) -> None:
        lp = self.local_position
        glPushMatrix()
        glTranslatef(float(earth_world[0] + lp[0]),
                     float(earth_world[1] + lp[1]),
                     float(earth_world[2] + lp[2]))

        glUseProgram(self._shader)
        glUniform1i(self._u_tex,  0)
        glUniform3f(self._u_lightDir, *sun_eye_dir)
        glUniform3f(self._u_color,    0.7, 0.7, 0.7)
        glUniform1f(self._u_specPow,  12.0)
        glUniform1f(self._u_hasTex,   1.0)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._tex)
        self._render_vbo()
        glBindTexture(GL_TEXTURE_2D, 0)

        glUseProgram(0)
        glPopMatrix()

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
