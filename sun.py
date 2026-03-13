"""
sun.py — Glowing Sun object (stationary at world origin).
"""
import math
import numpy as np
from OpenGL.GL import *

import shaders
from sphere_gen import generate_sphere
from texture_loader import load_texture
import config


class Sun:
    def __init__(self, tex_dir: str = "textures"):
        # Build sun sphere VBOs
        verts, norms, uvs, indices = generate_sphere(48, 48, config.SUN_RADIUS)
        self._index_count = len(indices)

        self._vbo_v = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_v)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)

        self._vbo_n = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_n)
        glBufferData(GL_ARRAY_BUFFER, norms.nbytes, norms, GL_STATIC_DRAW)

        self._vbo_u = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._vbo_u)
        glBufferData(GL_ARRAY_BUFFER, uvs.nbytes, uvs, GL_STATIC_DRAW)

        self._ibo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        # Texture + shader
        self._tex    = load_texture(f"{tex_dir}/sun.png")
        self._shader = shaders.link_program(shaders.UNLIT_VERT, shaders.UNLIT_FRAG)
        self._unlit_tex_loc   = glGetUniformLocation(self._shader, "u_tex")
        self._unlit_col_loc   = glGetUniformLocation(self._shader, "u_color")
        self._unlit_has_loc   = glGetUniformLocation(self._shader, "u_hasTexture")

        # Atmosphere / bloom shader
        self._atmo_shader = shaders.link_program(shaders.ATMO_VERT, shaders.ATMO_FRAG)
        self._atmo_col_loc   = glGetUniformLocation(self._atmo_shader, "u_color")
        self._atmo_alpha_loc = glGetUniformLocation(self._atmo_shader, "u_alpha")
        self._atmo_scale     = 1.25   # slightly larger than planet

        self.position = np.array([0.0, 0.0, 0.0])

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        pass   # Sun is stationary

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        glPushMatrix()
        glTranslatef(*self.position)

        # ── Glow corona (additive, slightly larger sphere) ────────────────────
        self._draw_atmosphere()

        # ── Sun body (unlit, textured) ────────────────────────────────────────
        glUseProgram(self._shader)
        glUniform1i(self._unlit_tex_loc, 0)
        glUniform4f(self._unlit_col_loc, 1.0, 0.98, 0.85, 1.0)
        glUniform1f(self._unlit_has_loc, 1.0)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._tex)

        self._render_vbo()

        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glPopMatrix()

    def _draw_atmosphere(self) -> None:
        glPushMatrix()
        glScalef(self._atmo_scale, self._atmo_scale, self._atmo_scale)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)   # additive
        glDepthMask(GL_FALSE)
        glCullFace(GL_FRONT)

        glUseProgram(self._atmo_shader)
        glUniform3f(self._atmo_col_loc, 1.0, 0.82, 0.30)
        glUniform1f(self._atmo_alpha_loc, 0.9)

        self._render_vbo()

        glUseProgram(0)
        glCullFace(GL_BACK)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
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
