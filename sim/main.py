"""
main.py — Entry point for Satellite Simulation.

Controls
--------
1            Solar system view (drag + scroll to navigate)
2            Planet third-person view  (Tab cycles planets)
3            Satellite third-person view (Tab cycles satellites)
Tab          Cycle planets (mode 2) or satellites (mode 3)
Scroll       Zoom in/out (solar view)
Drag LMB     Rotate solar view
Click        Pick satellite or planet → info popup
Toolbar      PAUSE | 1× | 10× | 50× speed buttons
Esc          Close popup / quit
"""
import sys
import pygame
from pygame.locals import *
from OpenGL.GL import *

import config
from scene      import Scene
from camera     import Camera
from hud        import HUD
from info_popup import InfoPopup


def init_gl(w: int, h: int) -> None:
    glEnable(GL_DEPTH_TEST);  glDepthFunc(GL_LEQUAL)
    glEnable(GL_CULL_FACE);   glCullFace(GL_BACK);  glFrontFace(GL_CCW)
    glShadeModel(GL_SMOOTH)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    glClearColor(*config.NASA_DARK)
    glViewport(0, 0, w, h)


def main() -> None:
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    pygame.display.set_mode(
        (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
        DOUBLEBUF | OPENGL,
    )
    pygame.mouse.set_visible(True)

    init_gl(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

    print("[main] Loading scene …")
    scene  = Scene()
    camera = Camera()
    hud    = HUD(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
    popup  = InfoPopup(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

    clock   = pygame.time.Clock()
    running = True
    print("[main] Simulation started.")

    while running:
        dt = clock.tick(config.FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if popup.visible:
                        popup.close()
                    else:
                        running = False

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                # 1. Check HUD toolbar first
                new_scale = HUD.handle_click(event.pos)
                if new_scale is not None:
                    scene.time_scale = new_scale

                # 2. Pick satellite or planet
                elif not popup.visible:
                    ray_o, ray_d = camera.get_pick_ray(*event.pos)

                    # Try satellites
                    hit_sat = scene.pick_satellite(ray_o, ray_d)
                    if hit_sat:
                        popup.show_satellite(hit_sat)
                        sat_names = list(config.SATELLITES_DATA)
                        if hit_sat in sat_names:
                            camera.sat_idx = sat_names.index(hit_sat)

                    else:
                        # Try planets
                        hit_planet = scene.pick_planet(ray_o, ray_d)
                        if hit_planet:
                            popup.show_planet(hit_planet)
                            names = [p["name"] for p in config.PLANETS_DATA]
                            if hit_planet in names:
                                camera.planet_idx = names.index(hit_planet)

            popup.handle_event(event)
            camera.handle_event(event)

        # Update
        scene.update(dt)
        camera.update(dt, scene.planets, scene.satellites)

        # Render
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        camera.apply()
        scene.draw(camera.eye_position)
        hud.draw(camera, scene)
        popup.draw()

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
