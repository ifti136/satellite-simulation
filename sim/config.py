"""
config.py — Global constants for the NASA Orbital Simulation
"""
import math

# ── Window ────────────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE  = "NASA Orbital Simulation"
FPS           = 60
FOV           = 50.0
NEAR_CLIP     = 0.05
FAR_CLIP      = 800.0

# ── Scale: 1 unit ≈ 1 Earth radius ───────────────────────────────────────────
EARTH_RADIUS  = 1.0
SUN_RADIUS    = 6.0

# ── Camera modes ──────────────────────────────────────────────────────────────
CAM_MODE_SOLAR     = "solar"
CAM_MODE_PLANET    = "planet_tpp"
CAM_MODE_SAT_TPP   = "satellite_tpp"

# ── Simulation time multipliers ───────────────────────────────────────────────
TIME_SCALES = [0.0, 1.0, 10.0, 50.0]   # pause, 1×, 10×, 50×
TIME_SCALE_LABELS = ["PAUSE", "1×", "10×", "50×"]

# ── Colours (NASA palette) ────────────────────────────────────────────────────
NASA_DARK   = (0.02, 0.02, 0.08, 1.0)
NASA_BLUE   = (0.00, 0.48, 0.78)
NASA_ACCENT = (0.00, 0.75, 1.00)
NASA_WHITE  = (0.95, 0.97, 1.00)

# ── Planet definitions ────────────────────────────────────────────────────────
# orbit_radius : distance from Sun in sim units
# radius       : planet radius in sim units
# tilt         : axial tilt in degrees
# orbit_speed  : rad / sim-second at 1× speed
# rot_speed    : self-rotation rad / sim-second at 1×
# texture      : filename in textures/
# rings        : True if planet has a ring system
# ring_inner/outer: ring radii relative to planet radius
# moons        : list of moon config dicts
# color        : fallback RGB if texture missing

TAU = 2 * math.pi

PLANETS_DATA = [
    {
        "name":        "Mercury",
        "radius":       0.38,
        "tilt":         0.034,
        "orbit_radius": 14.0,
        "orbit_speed":  TAU / 40.0,
        "rot_speed":    TAU / 140.0,
        "texture":      "mercury.png",
        "rings":        False,
        "moons":        [],
        "color":        (0.75, 0.72, 0.68),
    },
    {
        "name":        "Venus",
        "radius":       0.95,
        "tilt":         177.4,
        "orbit_radius": 22.0,
        "orbit_speed":  TAU / 65.0,
        "rot_speed":    TAU / 200.0,
        "texture":      "venus.png",
        "rings":        False,
        "moons":        [],
        "color":        (0.90, 0.82, 0.60),
    },
    {
        "name":        "Earth",
        "radius":       1.0,
        "tilt":         23.4,
        "orbit_radius": 32.0,
        "orbit_speed":  TAU / 90.0,
        "rot_speed":    TAU / 30.0,
        "texture":      "earth_day.png",
        "night_texture": "earth_night.png",
        "rings":        False,
        "moons": [
            {
                "name":         "Moon",
                "radius":        0.272,
                "orbit_radius":  4.5,
                "orbit_speed":   TAU / 45.0,
                "inclination":   5.1,
                "texture":       "moon.png",
                "color":         (0.70, 0.70, 0.68),
            }
        ],
        "color":        (0.25, 0.45, 0.75),
    },
    {
        "name":        "Mars",
        "radius":       0.53,
        "tilt":         25.2,
        "orbit_radius": 50.0,
        "orbit_speed":  TAU / 140.0,
        "rot_speed":    TAU / 31.0,
        "texture":      "mars.png",
        "rings":        False,
        "moons": [
            {
                "name":        "Phobos",
                "radius":       0.08,
                "orbit_radius": 1.5,
                "orbit_speed":  TAU / 3.0,
                "inclination":  1.0,
                "texture":      "moon.png",
                "color":        (0.55, 0.50, 0.45),
            },
            {
                "name":        "Deimos",
                "radius":       0.05,
                "orbit_radius": 2.2,
                "orbit_speed":  TAU / 6.0,
                "inclination":  1.8,
                "texture":      "moon.png",
                "color":        (0.52, 0.48, 0.44),
            },
        ],
        "color":        (0.78, 0.40, 0.22),
    },
    {
        "name":        "Jupiter",
        "radius":       3.5,
        "tilt":         3.1,
        "orbit_radius": 100.0,
        "orbit_speed":  TAU / 280.0,
        "rot_speed":    TAU / 10.0,
        "texture":      "jupiter.png",
        "rings":        False,
        "moons":        [],
        "color":        (0.82, 0.72, 0.58),
    },
    {
        "name":        "Saturn",
        "radius":       3.0,
        "tilt":         26.7,
        "orbit_radius": 160.0,
        "orbit_speed":  TAU / 420.0,
        "rot_speed":    TAU / 11.0,
        "texture":      "saturn.png",
        "rings":        True,
        "ring_inner":   1.3,
        "ring_outer":   2.4,
        "ring_texture": "saturn_ring.png",
        "moons":        [],
        "color":        (0.88, 0.82, 0.62),
    },
    {
        "name":        "Uranus",
        "radius":       2.0,
        "tilt":         97.8,
        "orbit_radius": 230.0,
        "orbit_speed":  TAU / 600.0,
        "rot_speed":    TAU / 17.0,
        "texture":      "uranus.png",
        "rings":        False,
        "moons":        [],
        "color":        (0.68, 0.88, 0.92),
    },
    {
        "name":        "Neptune",
        "radius":       1.9,
        "tilt":         28.3,
        "orbit_radius": 310.0,
        "orbit_speed":  TAU / 800.0,
        "rot_speed":    TAU / 16.0,
        "texture":      "neptune.png",
        "rings":        False,
        "moons":        [],
        "color":        (0.22, 0.38, 0.82),
    },
]

# ── Satellites (orbit Earth specifically) ─────────────────────────────────────
SATELLITES_DATA = {
    "ISS": {
        "full_name":    "International Space Station",
        "orbit_radius":  2.0,
        "inclination":   51.6,
        "altitude_km":   408,
        "velocity_kms":  7.66,
        "period_min":    92.65,
        "operator":      "NASA / Roscosmos / ESA / JAXA / CSA",
        "launched":      "20 November 1998",
        "description":   ("The ISS is a modular space station in low Earth orbit.\n"
                          "It serves as a microgravity and space environment research lab."),
        "orbit_speed":   TAU / 20.0,
        "model":         "models/iss.obj",
        "color":         (0.85, 0.88, 0.92),
        "panel_color":   (0.18, 0.30, 0.55),
        "phase":         0.0,
    },
    "Hubble": {
        "full_name":    "Hubble Space Telescope",
        "orbit_radius":  2.4,
        "inclination":   28.5,
        "altitude_km":   547,
        "velocity_kms":  7.59,
        "period_min":    95.42,
        "operator":      "NASA / ESA",
        "launched":      "24 April 1990",
        "description":   ("HST is a space telescope launched into low Earth orbit.\n"
                          "It has contributed greatly to our understanding of the universe."),
        "orbit_speed":   TAU / 25.0,
        "model":         "models/hubble.obj",
        "color":         (0.80, 0.80, 0.75),
        "panel_color":   (0.60, 0.70, 0.30),
        "phase":         math.pi * 0.7,
    },
    "TDRS": {
        # Tracking and Data Relay Satellite — geosynchronous, large dish antennas
        "full_name":    "TDRS-M (TDRS-13)",
        "orbit_radius":  5.5,          # GEO sits much higher than ISS/Hubble
        "inclination":   0.0,          # geosynchronous — equatorial orbit
        "altitude_km":   35_786,       # geostationary altitude
        "velocity_kms":  3.07,
        "period_min":    1436.1,       # ~24 hours
        "operator":      "NASA / Boeing",
        "launched":      "18 August 2017",
        "description":   ("TDRS-M is the 13th satellite in NASA's Tracking and\n"
                          "Data Relay Satellite System. It provides high-bandwidth\n"
                          "S-, Ku- and Ka-band relay links to the ISS and other craft."),
        "orbit_speed":   TAU / 55.0,   # slow — GEO orbit takes much longer visually
        "model":         "models/tdrs.obj",
        "color":         (0.88, 0.88, 0.85),   # white/silver body
        "panel_color":   (0.15, 0.25, 0.50),   # dark blue solar arrays
        "phase":         math.pi * 1.4,
    },
}
