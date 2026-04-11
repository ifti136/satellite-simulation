"""
sphere_gen.py — UV sphere geometry using the Midpoint Circle Algorithm.

Every latitude ring's cos/sin values come from midpoint_circle.circle_points()
instead of math.sin/cos per-vertex.  The stack (phi) loop still uses math for
the polar angle — that's a single value per stack, not a per-vertex operation.
"""
import math
import numpy as np
from midpoint_circle import circle_points


def generate_sphere(stacks: int = 64, slices: int = 64, radius: float = 1.0):
    """
    Generate a UV-sphere.

    Returns
    -------
    verts   : float32 (N, 3)
    norms   : float32 (N, 3)
    uvs     : float32 (N, 2)
    indices : int32   (M,)   — flat list for GL_TRIANGLES
    """
    verts, norms, uvs = [], [], []

    # Pre-compute one full circle of (cos θ, sin θ) for all slices.
    # This replaces: for j in range(slices+1): theta = 2π*j/slices; cos/sin(theta)
    # MCA gives us `slices` unique unit-circle points; we append [0] to close the seam.
    slice_pts = circle_points(slices)          # list of (cos_t, sin_t), length = slices
    slice_pts = slice_pts + [slice_pts[0]]     # close seam → length = slices + 1

    for i in range(stacks + 1):
        phi     = math.pi * i / stacks         # one trig call per stack (not per vertex)
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)

        for j, (cos_t, sin_t) in enumerate(slice_pts):
            # Normal direction (unit sphere)
            nx = sin_phi * cos_t
            ny = cos_phi
            nz = sin_phi * sin_t

            verts.append([nx * radius, ny * radius, nz * radius])
            norms.append([nx, ny, nz])
            uvs.append([j / slices, 1.0 - i / stacks])

    # Build index buffer — two triangles per quad
    indices = []
    stride  = slices + 1
    for i in range(stacks):
        for j in range(slices):
            a = i * stride + j
            b = a + stride
            indices += [a, b, a + 1, b, b + 1, a + 1]

    return (np.array(verts,   dtype=np.float32),
            np.array(norms,   dtype=np.float32),
            np.array(uvs,     dtype=np.float32),
            np.array(indices, dtype=np.int32))
