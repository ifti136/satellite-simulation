# NASA Orbital Simulation — Setup Guide

## Requirements

```
pip install PyOpenGL PyOpenGL_accelerate pygame Pillow numpy
```

## Project structure

```
sim/
├── main.py            ← entry point
├── config.py          ← all constants, planet/satellite data
├── scene.py           ← orchestrates all objects
├── camera.py          ← 3 camera modes
├── planet.py          ← generic Planet (all 8 planets + moons + rings)
├── satellite.py       ← ISS / Hubble / Starlink  (model or fallback)
├── sun.py             ← Sun with pulsing corona
├── skybox.py          ← star-field background sphere
├── hud.py             ← on-screen HUD + time-control toolbar
├── info_popup.py      ← click-to-inspect popup card
├── orbit.py           ← circular orbital mechanics
├── model_loader.py    ← pure-Python OBJ loader (no extra deps)
├── sphere_gen.py      ← UV-sphere geometry generator
├── shaders.py         ← all GLSL shaders
├── texture_loader.py  ← PIL → OpenGL texture
│
├── textures/          ← place all .png textures here
│   ├── earth_day.png
│   ├── earth_night.png
│   ├── moon.png
│   ├── sun.png
│   ├── stars.png
│   ├── mercury.png
│   ├── venus.png
│   ├── mars.png
│   ├── jupiter.png
│   ├── saturn.png
│   ├── saturn_ring.png   (optional — transparent PNG ring map)
│   ├── uranus.png
│   └── neptune.png
│
└── models/            ← place OBJ models here (optional)
    ├── iss.obj
    ├── hubble.obj
    └── starlink.obj
```

## Free texture sources

| Pack | URL |
|------|-----|
| Solar System Scope (2K/8K planet textures) | https://www.solarsystemscope.com/textures/ |
| NASA Visible Earth (Earth day/night) | https://visibleearth.nasa.gov |
| James Hastings-Trew (star-field) | http://planetpixelemporium.com/earth.html |

Download each planet texture, rename to match the filenames above, and place in `textures/`.

## Free 3D model sources (OBJ format)

| Model | URL |
|-------|-----|
| ISS (NASA official) | https://nasa3d.arc.nasa.gov/detail/iss-4k |
| Hubble (NASA) | https://nasa3d.arc.nasa.gov/detail/hubble |
| Generic satellite | https://grabcad.com (search "satellite OBJ") |

Download, export/convert to `.obj`, scale if needed, place in `models/`.  
The loader auto-scales models to fit a 0.4-unit bounding sphere.  
If no model file is found the sim falls back to hand-coded box geometry seamlessly.

## Controls

| Key / action | Effect |
|---|---|
| `1` | Solar system view (drag + scroll) |
| `2` | Planet third-person view |
| `3` | Satellite third-person view |
| `Tab` | Cycle planets (mode 2) or satellites (mode 3) |
| Mouse drag | Rotate solar view |
| Scroll wheel | Zoom in / out |
| Left click | Pick satellite or planet → info popup |
| Toolbar buttons | PAUSE / 1× / 10× / 50× time scale |
| `Esc` | Close popup / quit |

## Running

```bash
cd sim
python main.py
```

## Adding your own satellite

1. Add an entry to `SATELLITES_DATA` in `config.py` with the same keys as ISS/Hubble/Starlink.
2. Add a fallback geometry class in `satellite.py` (copy `FallbackStarlink` and edit).
3. Register it in `_FALLBACKS` and in the `make_satellite` call list in `scene.py`.
4. Optionally drop an OBJ file at the path given in `"model"` — it will be used automatically.

## Adding a planet

Add a dict to `PLANETS_DATA` in `config.py` with all required keys.  
`scene.py` builds planets dynamically from that list — no code changes needed.
