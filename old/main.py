"""
main.py — Entry point for NASA Orbital Simulation.

Controls
--------
1           Solar system view
2           Earth third-person view
3           Satellite third-person view
Tab         Cycle between satellites (ISS → Hubble → Starlink)
Scroll      Zoom in / out  (solar view)
Drag (LMB)  Rotate camera   (solar view)
Click       Pick satellite → open info popup
Esc         Close popup / quit (when no popup)
"""
import sys
import math
import numpy as np

import pygame
from pygame.locals import *
from OpenGL.GL  import *
from OpenGL.GLU import gluPerspective

import config
from scene      import Scene
from camera     import Camera
from hud        import HUD
from info_popup import InfoPopup


def init_gl(w: int, h: int) -> None:
    """One-time OpenGL state setup."""
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glFrontFace(GL_CCW)

    glShadeModel(GL_SMOOTH)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

    glClearColor(*config.NASA_DARK)
    glViewport(0, 0, w, h)


def main() -> None:
    # ── pygame / GL init ──────────────────────────────────────────────────────
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    pygame.display.set_mode(
        (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
        DOUBLEBUF | OPENGL,
    )
    pygame.mouse.set_visible(True)

    init_gl(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

    # ── Build scene objects (must be after GL context) ─────────────────────────
    print("[main] Loading scene …")
    scene  = Scene()
    camera = Camera()
    hud    = HUD(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
    popup  = InfoPopup(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

    clock   = pygame.time.Clock()
    running = True
    print("[main] Starting render loop.")

    while running:
        dt = clock.tick(config.FPS) / 1000.0   # seconds

        # ── Events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                if popup.visible:
                    popup.close()
                else:
                    running = False

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                # Satellite picking (only in solar & earth-tpp modes)
                if not popup.visible and camera.mode in (
                    config.CAM_MODE_SOLAR, config.CAM_MODE_EARTH_TPP
                ):
                    ray_o, ray_d = camera.get_pick_ray(*event.pos)
                    hit = scene.pick_satellite(ray_o, ray_d)
                    if hit:
                        popup.show(hit)
                        # Also select that satellite
                        sat_names = ["ISS", "Hubble", "Starlink"]
                        if hit in sat_names:
                            camera.sat_idx = sat_names.index(hit)

            popup.handle_event(event)
            camera.handle_event(event)

        # ── Update ────────────────────────────────────────────────────────────
        scene.update(dt)
        camera.update(dt, scene.earth, scene.satellites)

        # ── Render ────────────────────────────────────────────────────────────
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Apply camera (sets projection + modelview)
        camera.apply()

        # Draw 3-D scene
        scene.draw(camera.eye_position)

        # 2-D overlays
        hud.draw(camera, scene.satellites, scene.earth_world, scene.sim_time)
        popup.draw()

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
