"""
skybox.py — Large inverted textured sphere for the starfield background.

If stars.png is missing, falls back to procedural GL_POINTS star field
so the background is always star-filled.
"""
import os
import numpy as np
from OpenGL.GL import *

import shaders
from sphere_gen     import generate_sphere
from texture_loader import load_texture

_STAR_COUNT = 3000
_STAR_RADIUS = 580.0


def _gen_star_positions(n: int, r: float) -> np.ndarray:
    """Uniform random points on sphere surface, radius r."""
    rng = np.random.default_rng(42)
    # Marsaglia / cos-lat method — truly uniform on sphere
    theta = rng.uniform(0.0, 2.0 * np.pi, n)
    cos_p = rng.uniform(-1.0, 1.0, n)
    sin_p = np.sqrt(1.0 - cos_p ** 2)
    pts = np.column_stack([
        r * sin_p * np.cos(theta),
        r * cos_p,
        r * sin_p * np.sin(theta),
    ]).astype(np.float32)
    return pts


def _gen_star_colors(n: int) -> np.ndarray:
    """Randomised star colours: mostly white/blue-white, a few warm."""
    rng = np.random.default_rng(7)
    brightness = rng.uniform(0.4, 1.0, n).astype(np.float32)
    # Slight colour tint
    r_tint = np.clip(brightness + rng.uniform(-0.1, 0.2, n), 0, 1).astype(np.float32)
    g_tint = np.clip(brightness + rng.uniform(-0.05, 0.05, n), 0, 1).astype(np.float32)
    b_tint = np.clip(brightness + rng.uniform(-0.1, 0.15, n), 0, 1).astype(np.float32)
    return np.column_stack([r_tint, g_tint, b_tint]).astype(np.float32)


class Skybox:
    RADIUS = 600.0

    def __init__(self, tex_dir: str = "textures"):
        # ── Sphere VBOs (used only when texture present) ──────────────────────
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
        glBufferData(GL_ARRAY_BUFFER, uvs.nbytes, uvs, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        # ── Texture ───────────────────────────────────────────────────────────
        tex_path = f"{tex_dir}/stars.png"
        self._has_tex_file = os.path.exists(tex_path)
        self._tex    = load_texture(tex_path, flip=False) if self._has_tex_file else 0
        self._shader = shaders.link_program(shaders.UNLIT_VERT, shaders.UNLIT_FRAG)
        self._u_tex    = glGetUniformLocation(self._shader, "u_tex")
        self._u_color  = glGetUniformLocation(self._shader, "u_color")
        self._u_hasTex = glGetUniformLocation(self._shader, "u_hasTexture")

        # ── Procedural star field VBO (always built; used when no texture) ────
        self._star_pos    = _gen_star_positions(_STAR_COUNT, _STAR_RADIUS)
        self._star_colors = _gen_star_colors(_STAR_COUNT)

        self._star_vbo_pos = glGenBuffers(1)
        self._star_vbo_col = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._star_vbo_pos)
        glBufferData(GL_ARRAY_BUFFER, self._star_pos.nbytes,
                     self._star_pos, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self._star_vbo_col)
        glBufferData(GL_ARRAY_BUFFER, self._star_colors.nbytes,
                     self._star_colors, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        if self._has_tex_file:
            print("[skybox] Using stars.png texture.")
        else:
            print(f"[skybox] stars.png not found — using procedural starfield "
                  f"({_STAR_COUNT} stars).")

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self) -> None:
        if self._has_tex_file:
            self._draw_sphere()
        else:
            self._draw_point_stars()

    # ── Sphere (texture path) ─────────────────────────────────────────────────

    def _draw_sphere(self) -> None:
        glDepthMask(GL_FALSE)
        glCullFace(GL_FRONT)
        glUseProgram(self._shader)
        glUniform1i(self._u_tex,    0)
        glUniform4f(self._u_color,  1.0, 1.0, 1.0, 1.0)
        glUniform1f(self._u_hasTex, 1.0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._tex)
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
        glDrawElements(GL_TRIANGLES, self._idx, GL_UNSIGNED_INT, None)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)
        glCullFace(GL_BACK)
        glDepthMask(GL_TRUE)

    # ── Procedural point stars (no-texture fallback) ──────────────────────────

    def _draw_point_stars(self) -> None:
        glDepthMask(GL_FALSE)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        glUseProgram(0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_POINT_SMOOTH)
        glPointSize(1.8)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self._star_vbo_pos)
        glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, self._star_vbo_col)
        glColorPointer(3, GL_FLOAT, 0, None)
        glDrawArrays(GL_POINTS, 0, _STAR_COUNT)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        glDisable(GL_POINT_SMOOTH)
        glDisable(GL_BLEND)
        glDepthMask(GL_TRUE)
        glColor4f(1.0, 1.0, 1.0, 1.0)   # reset colour state