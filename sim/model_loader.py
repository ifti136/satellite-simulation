"""
model_loader.py — Pure-Python OBJ loader.

Returns numpy arrays ready to upload into OpenGL VBOs:
    (vertices, normals, texcoords, indices)

Each index triplet references a unique (position, normal, uv) combination.
Faces are triangulated (fan method) so quads and polygons are handled.

If the .obj file is missing, falls back to a unit sphere so the rest of
the code never receives None.
"""
import os
import math
import numpy as np
from sphere_gen import generate_sphere


def load_obj(path: str):
    """
    Load an OBJ file.  Returns (verts, norms, uvs, indices) as float32/int32
    numpy arrays compatible with glDrawElements(GL_TRIANGLES).
    """
    if not os.path.exists(path):
        print(f"[model] WARNING: OBJ not found — {path!r}  (using sphere fallback)")
        return generate_sphere(32, 32, 1.0)

    raw_pos   = []   # list of [x,y,z]
    raw_uv    = []   # list of [u,v]
    raw_norm  = []   # list of [nx,ny,nz]
    faces     = []   # list of face-vertex tuples (pos_idx, uv_idx, norm_idx)
                     # indices are already 0-based after parsing

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                token = parts[0]

                if token == "v":
                    raw_pos.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif token == "vt":
                    u = float(parts[1])
                    v = float(parts[2]) if len(parts) > 2 else 0.0
                    raw_uv.append([u, v])
                elif token == "vn":
                    raw_norm.append([float(parts[1]), float(parts[2]), float(parts[3])])
                elif token == "f":
                    # Each vertex entry: "v", "v/vt", "v//vn", or "v/vt/vn"
                    face_verts = []
                    for entry in parts[1:]:
                        segs = entry.split("/")
                        pi = int(segs[0]) - 1
                        ti = (int(segs[1]) - 1) if len(segs) > 1 and segs[1] else -1
                        ni = (int(segs[2]) - 1) if len(segs) > 2 and segs[2] else -1
                        # Handle negative (relative) indices
                        if pi < 0: pi += len(raw_pos) + 1
                        if ti < 0 and ti != -1: ti += len(raw_uv) + 1
                        if ni < 0 and ni != -1: ni += len(raw_norm) + 1
                        face_verts.append((pi, ti, ni))
                    # Fan triangulate
                    for i in range(1, len(face_verts) - 1):
                        faces.append((face_verts[0], face_verts[i], face_verts[i + 1]))

    except Exception as e:
        print(f"[model] ERROR parsing {path}: {e}  (using sphere fallback)")
        return generate_sphere(32, 32, 1.0)

    if not faces:
        print(f"[model] WARNING: no faces in {path}  (using sphere fallback)")
        return generate_sphere(32, 32, 1.0)

    # Build de-duplicated vertex list indexed by (pi, ti, ni)
    index_map = {}
    out_verts  = []
    out_norms  = []
    out_uvs    = []
    out_indices = []

    has_uv   = bool(raw_uv)
    has_norm = bool(raw_norm)

    for tri in faces:
        for (pi, ti, ni) in tri:
            key = (pi, ti, ni)
            if key not in index_map:
                index_map[key] = len(out_verts)
                out_verts.append(raw_pos[pi])
                out_uvs.append(raw_uv[ti] if (has_uv and ti >= 0) else [0.0, 0.0])
                if has_norm and ni >= 0:
                    out_norms.append(raw_norm[ni])
                else:
                    out_norms.append([0.0, 1.0, 0.0])   # placeholder
            out_indices.append(index_map[key])

    # If no normals in file, compute per-face flat normals
    if not has_norm:
        flat_norms = [[0.0, 0.0, 0.0]] * len(out_verts)
        vv = np.array(out_verts, dtype=np.float64)
        idx = np.array(out_indices, dtype=np.int32).reshape(-1, 3)
        for tri_idx in idx:
            a, b, c = vv[tri_idx[0]], vv[tri_idx[1]], vv[tri_idx[2]]
            n = np.cross(b - a, c - a)
            norm = np.linalg.norm(n)
            if norm > 1e-9:
                n /= norm
            for vi in tri_idx:
                flat_norms[vi] = (np.array(flat_norms[vi]) + n).tolist()
        out_norms = flat_norms

    verts   = np.array(out_verts,   dtype=np.float32)
    norms   = np.array(out_norms,   dtype=np.float32)
    uvs     = np.array(out_uvs,     dtype=np.float32)
    indices = np.array(out_indices, dtype=np.int32)

    # Normalise normal vectors
    lengths = np.linalg.norm(norms, axis=1, keepdims=True)
    lengths = np.where(lengths < 1e-9, 1.0, lengths)
    norms /= lengths

    print(f"[model] Loaded {path!r}: {len(verts)} verts, {len(indices)//3} tris")
    return verts, norms, uvs, indices


def _auto_scale(verts: np.ndarray, target_radius: float = 1.0) -> np.ndarray:
    """
    Rescale vertices so the model fits within a sphere of target_radius.
    Call this after load_obj() if model units are unknown.
    """
    maxr = np.max(np.linalg.norm(verts, axis=1))
    if maxr > 1e-6:
        verts = verts * (target_radius / maxr)
    return verts
