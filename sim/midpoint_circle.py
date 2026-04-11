"""
midpoint_circle.py — Midpoint Circle Algorithm for 3-D geometry generation.

The MCA is an integer rasterisation algorithm.  We run it on an integer
grid of radius R, collect the (x, y) pixel coordinates for one octant,
expand to all eight octants, sort by angle in [0, 2pi), normalise onto the
unit circle, and resample to exactly N evenly-spaced points.

Public API
----------
    circle_points(n)  ->  list of n (cos_theta, sin_theta) pairs
"""
import math


# ── Integer MCA ───────────────────────────────────────────────────────────────

_MCA_RADIUS = 512   # larger grid → more raw points → smoother interpolation


def _mca_integer_octant(R: int) -> list:
    """
    Classic integer Midpoint Circle Algorithm, first octant only.
    Starts at (R, 0) and walks toward (R/sqrt2, R/sqrt2).
    Returns (x, y) integer pairs with x >= y >= 0.
    """
    pts = []
    x = R
    y = 0
    d = 1 - R   # initial decision variable

    while x >= y:
        pts.append((x, y))
        y += 1
        if d < 0:
            d += 2 * y + 1          # East step
        else:
            x -= 1
            d += 2 * (y - x) + 1   # South-East step

    return pts


def _expand_octants(octant: list) -> list:
    """
    Reflect one octant into all eight via sign/swap symmetry.
    Returns unique (cos, sin) float pairs covering the full circle,
    each normalised onto the unit circle.
    """
    seen = set()
    pts  = []

    def add(ix: int, iy: int):
        key = (ix, iy)
        if key in seen:
            return
        seen.add(key)
        length = math.sqrt(ix * ix + iy * iy)
        if length > 0:
            pts.append((ix / length, iy / length))

    for (x, y) in octant:
        add( x,  y);  add( y,  x)
        add(-x,  y);  add(-y,  x)
        add( x, -y);  add( y, -x)
        add(-x, -y);  add(-y, -x)

    return pts


def _sort_by_angle(pts: list) -> list:
    """Sort unit-circle points by angle in [0, 2pi)."""
    def _angle(p):
        a = math.atan2(p[1], p[0])        # in [-pi, pi]
        return a if a >= 0 else a + 2 * math.pi   # remap to [0, 2pi)
    return sorted(pts, key=_angle)


def _resample_uniform(sorted_pts: list, n: int) -> list:
    """
    Linearly interpolate the sorted unit-circle cloud to produce exactly N
    uniformly-spaced points covering [0, 2pi).

    The wrap-around segment (last point back to first) is included so
    that angles near 2pi are interpolated correctly and the full circle
    is always covered.
    """
    # Build angle array in [0, 2pi)
    angles = []
    for p in sorted_pts:
        a = math.atan2(p[1], p[0])
        if a < 0:
            a += 2 * math.pi
        angles.append(a)

    # Append wrap-around entry so the last segment closes the circle
    angles_w = angles       + [angles[0] + 2 * math.pi]
    pts_w    = sorted_pts   + [sorted_pts[0]]
    n_seg    = len(angles_w) - 1

    result = []
    for i in range(n):
        target = 2.0 * math.pi * i / n

        # Binary search for the segment that brackets `target`
        lo, hi = 0, n_seg - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if angles_w[mid + 1] <= target:
                lo = mid + 1
            else:
                hi = mid

        a0, a1 = angles_w[lo], angles_w[lo + 1]
        span   = a1 - a0
        t      = (target - a0) / span if span > 1e-12 else 0.0

        x0, y0 = pts_w[lo]
        x1, y1 = pts_w[lo + 1]
        rx = x0 + (x1 - x0) * t
        ry = y0 + (y1 - y0) * t

        # Re-normalise back onto the unit circle
        length = math.sqrt(rx * rx + ry * ry)
        if length > 1e-12:
            rx /= length
            ry /= length

        result.append((rx, ry))

    return result


# ── Build lookup table once at import time ────────────────────────────────────

_MAX_N  = 1024

_octant  = _mca_integer_octant(_MCA_RADIUS)
_full    = _expand_octants(_octant)
_sorted  = _sort_by_angle(_full)
_TABLE   = _resample_uniform(_sorted, _MAX_N)   # 1024 evenly-spaced unit points


# ── Public API ────────────────────────────────────────────────────────────────

def circle_points(n: int) -> list:
    """
    Return exactly N (cos_theta, sin_theta) pairs uniformly spaced around
    the unit circle, derived via the Midpoint Circle Algorithm.

    Drop-in replacement for:
        [(math.cos(2*pi*i/n), math.sin(2*pi*i/n)) for i in range(n)]
    """
    if n <= 0:
        return []
    if n <= _MAX_N:
        step = _MAX_N / n
        return [_TABLE[round(i * step) % _MAX_N] for i in range(n)]
    # n > _MAX_N: resample on demand (rare — only extreme-detail geometry)
    return _resample_uniform(_sorted, n)