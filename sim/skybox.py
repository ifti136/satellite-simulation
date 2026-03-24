"""
skybox.py — Large inverted textured sphere for the starfield background.
"""
import numpy as np
from OpenGL.GL import *

import shaders
from sphere_gen    import generate_sphere
from texture_loader import load_texture


class Skybox:
    RADIUS = 600.0

    def __init__(self, tex_dir: str = "textures"):
        verts, norms, uvs, indices = generate_sphere(32, 64, self.RADIUS)
        self._idx = len(indices)
        norms = -norms
        uvs[:, 0] = 1.0 - uvs[:, 0]

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

        self._tex    = load_texture(f"{tex_dir}/stars.png", flip=False)
        self._shader = shaders.link_program(shaders.UNLIT_VERT, shaders.UNLIT_FRAG)
        self._u_tex    = glGetUniformLocation(self._shader, "u_tex")
        self._u_color  = glGetUniformLocation(self._shader, "u_color")
        self._u_hasTex = glGetUniformLocation(self._shader, "u_hasTexture")

    def draw(self) -> None:
        glDepthMask(GL_FALSE)
        glCullFace(GL_FRONT)
        glUseProgram(self._shader)
        glUniform1i(self._u_tex,    0)
        glUniform4f(self._u_color,  1.0, 1.0, 1.0, 1.0)
        glUniform1f(self._u_hasTex, 1.0 if self._tex else 0.0)
        if self._tex:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self._tex)
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
        if self._tex: glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glCullFace(GL_BACK)
        glDepthMask(GL_TRUE)
