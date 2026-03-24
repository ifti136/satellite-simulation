"""
sphere_gen.py — UV sphere geometry.
"""
import math
import numpy as np


def generate_sphere(stacks: int = 64, slices: int = 64, radius: float = 1.0):
    verts, norms, uvs = [], [], []
    for i in range(stacks + 1):
        phi = math.pi * i / stacks
        sin_phi, cos_phi = math.sin(phi), math.cos(phi)
        for j in range(slices + 1):
            theta = 2.0 * math.pi * j / slices
            sin_t, cos_t = math.sin(theta), math.cos(theta)
            nx, ny, nz = sin_phi * cos_t, cos_phi, sin_phi * sin_t
            verts.append([nx * radius, ny * radius, nz * radius])
            norms.append([nx, ny, nz])
            uvs.append([j / slices, 1.0 - i / stacks])
    indices = []
    stride = slices + 1
    for i in range(stacks):
        for j in range(slices):
            a = i * stride + j
            b = a + stride
            indices += [a, b, a + 1, b, b + 1, a + 1]
    return (np.array(verts,   dtype=np.float32),
            np.array(norms,   dtype=np.float32),
            np.array(uvs,     dtype=np.float32),
            np.array(indices, dtype=np.int32))
