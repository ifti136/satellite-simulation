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
FAR_CLIP      = 600.0

# ── Scale: 1 unit = 1 Earth radius = 6 371 km ────────────────────────────────
EARTH_RADIUS  = 1.0
SUN_RADIUS    = 5.0
MOON_RADIUS   = 0.272     # Earth radii

# Solar-system display distances
SUN_DISTANCE  = 40.0      # Earth–Sun distance in sim units

# Moon orbit around Earth
MOON_ORBIT_RADIUS = 4.5

# Satellite orbits around Earth (scaled up for visibility; real ~1.07 ER)
ISS_ORBIT_RADIUS     = 2.0
HUBBLE_ORBIT_RADIUS  = 2.4
STARLINK_ORBIT_RADIUS = 2.7

# Real-world orbital data (shown in HUD/popup)
SATELLITES_DATA = {
    "ISS": {
        "full_name":    "International Space Station",
        "orbit_radius": ISS_ORBIT_RADIUS,
        "inclination":  51.6,          # degrees
        "altitude_km":  408,
        "velocity_kms": 7.66,
        "period_min":   92.65,
        "operator":     "NASA / Roscosmos / ESA / JAXA / CSA",
        "launched":     "20 November 1998",
        "description":  ("The ISS is a modular space station in low Earth orbit.\n"
                         "It is the largest human-made body ever placed in space\n"
                         "and serves as a microgravity research lab."),
        "color":        (0.85, 0.88, 0.92),   # silver-white
        "panel_color":  (0.18, 0.30, 0.55),   # deep blue panels
    },
    "Hubble": {
        "full_name":    "Hubble Space Telescope",
        "orbit_radius": HUBBLE_ORBIT_RADIUS,
        "inclination":  28.5,
        "altitude_km":  547,
        "velocity_kms": 7.59,
        "period_min":   95.42,
        "operator":     "NASA / ESA",
        "launched":     "24 April 1990",
        "description":  ("HST is a space telescope that was launched into\n"
                         "low Earth orbit in 1990. It has contributed greatly\n"
                         "to our understanding of the universe."),
        "color":        (0.80, 0.80, 0.75),   # aluminium
        "panel_color":  (0.60, 0.70, 0.30),   # golden-yellow panels
    },
    "Starlink": {
        "full_name":    "Starlink GROUP 6-30",
        "orbit_radius": STARLINK_ORBIT_RADIUS,
        "inclination":  53.0,
        "altitude_km":  550,
        "velocity_kms": 7.58,
        "period_min":   95.60,
        "operator":     "SpaceX",
        "launched":     "14 October 2023",
        "description":  ("Part of SpaceX's Starlink constellation.\n"
                         "A flat-panel satellite designed to provide\n"
                         "broadband internet globally."),
        "color":        (0.70, 0.70, 0.70),   # dark grey body
        "panel_color":  (0.10, 0.18, 0.35),   # dark solar array
    },
}

# ── Time ─────────────────────────────────────────────────────────────────────
# Angular velocities (radians/second of SIMULATION time)
# Earth orbit around Sun: full loop in ~60 s sim time
EARTH_ORBIT_SPEED    = (2 * math.pi) / 60.0
EARTH_ROTATION_SPEED = (2 * math.pi) / 15.0   # axis spin, 15 s/rev
MOON_ORBIT_SPEED     = (2 * math.pi) / 20.0

# Satellite angular velocities derived from v = sqrt(GM/r^3)
# We just use nice visible values
ISS_ORBIT_SPEED      = (2 * math.pi) / 5.0
HUBBLE_ORBIT_SPEED   = (2 * math.pi) / 7.0
STARLINK_ORBIT_SPEED = (2 * math.pi) / 6.0

# ── Camera ────────────────────────────────────────────────────────────────────
CAM_MODE_SOLAR     = "solar"
CAM_MODE_EARTH_TPP = "earth_tpp"
CAM_MODE_SAT_TPP   = "satellite_tpp"

# ── Colours (NASA palette) ────────────────────────────────────────────────────
NASA_DARK   = (0.02, 0.02, 0.08, 1.0)
NASA_BLUE   = (0.00, 0.48, 0.78)
NASA_ACCENT = (0.00, 0.75, 1.00)
NASA_WHITE  = (0.95, 0.97, 1.00)
