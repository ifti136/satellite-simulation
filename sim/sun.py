"""
sun.py — Glowing Sun (stationary at world origin) with corona pulse rings.
"""
import math
import numpy as np
from OpenGL.GL import *

import shaders
import config
from sphere_gen    import generate_sphere
from texture_loader import load_texture


class Sun:
    def __init__(self, tex_dir: str = "textures"):
        self._r   = config.SUN_RADIUS
        self._time = 0.0

        verts, norms, uvs, indices = generate_sphere(48, 48, self._r)
        self._idx = len(indices)
        self._vbo_v = glGenBuffers(1); glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)
        self._vbo_n = glGenBuffers(1); glBindBuffer(GL_ARRAY_BUFFER, self._vbo_n)
        glBufferData(GL_ARRAY_BUFFER, norms.nbytes, norms, GL_STATIC_DRAW)
        self._vbo_u = glGenBuffers(1); glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u)
        glBufferData(GL_ARRAY_BUFFER, uvs.nbytes, uvs, GL_STATIC_DRAW)
        self._ibo = glGenBuffers(1); glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        self._tex    = load_texture(f"{tex_dir}/sun.png")
        self._shader = shaders.link_program(shaders.UNLIT_VERT, shaders.UNLIT_FRAG)
        self._u_tex    = glGetUniformLocation(self._shader, "u_tex")
        self._u_color  = glGetUniformLocation(self._shader, "u_color")
        self._u_hasTex = glGetUniformLocation(self._shader, "u_hasTexture")

        self._atmo_shader    = shaders.link_program(shaders.ATMO_VERT, shaders.ATMO_FRAG)
        self._atmo_col_loc   = glGetUniformLocation(self._atmo_shader, "u_color")
        self._atmo_alpha_loc = glGetUniformLocation(self._atmo_shader, "u_alpha")

        self.position = np.array([0.0, 0.0, 0.0])

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self) -> None:
        glPushMatrix()
        glTranslatef(*self.position)

        # Pulsing outer corona (2 layers, slightly different scale / phase)
        for scale, phase, alpha in [(1.35, 0.0, 0.55), (1.55, math.pi, 0.30)]:
            pulse = scale + 0.05 * math.sin(self._time * 1.2 + phase)
            self._draw_corona(pulse, alpha)

        # Sun body
        glUseProgram(self._shader)
        glUniform1i(self._u_tex, 0)
        glUniform4f(self._u_color, 1.0, 0.96, 0.80, 1.0)
        glUniform1f(self._u_hasTex, 1.0 if self._tex else 0.0)
        if self._tex:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self._tex)
        self._render()
        if self._tex:
            glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glPopMatrix()

    def _draw_corona(self, scale: float, alpha: float) -> None:
        glPushMatrix()
        glScalef(scale, scale, scale)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        glCullFace(GL_FRONT)
        glUseProgram(self._atmo_shader)
        glUniform3f(self._atmo_col_loc, 1.0, 0.78, 0.22)
        glUniform1f(self._atmo_alpha_loc, alpha)
        self._render()
        glUseProgram(0)
        glCullFace(GL_BACK)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glPopMatrix()

    def _render(self) -> None:
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v); glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_n); glNormalPointer(GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u); glTexCoordPointer(2, GL_FLOAT, 0, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glDrawElements(GL_TRIANGLES, self._idx, GL_UNSIGNED_INT, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
