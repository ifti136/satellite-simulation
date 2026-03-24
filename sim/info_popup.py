"""
info_popup.py — Floating info card for satellites and planets.
"""
import pygame
from OpenGL.GL import *
import config


class InfoPopup:
    WIDTH  = 400
    HEIGHT = 280

    def __init__(self, screen_w: int, screen_h: int):
        self._sw = screen_w
        self._sh = screen_h
        self.visible  = False
        self._subject = None   # satellite name str or planet data dict
        self._tex     = glGenTextures(1)
        pygame.font.init()
        try:
            self._font_title = pygame.font.SysFont("monospace", 17, bold=True)
            self._font_body  = pygame.font.SysFont("monospace", 13)
            self._font_small = pygame.font.SysFont("monospace", 11)
        except Exception:
            self._font_title = pygame.font.Font(None, 20)
            self._font_body  = pygame.font.Font(None, 16)
            self._font_small = pygame.font.Font(None, 13)

    def show_satellite(self, name: str) -> None:
        self._subject = ("sat", name)
        self.visible  = True

    def show_planet(self, name: str) -> None:
        self._subject = ("planet", name)
        self.visible  = True

    def close(self) -> None:
        self.visible = False

    def handle_event(self, event) -> None:
        if not self.visible:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            px = (self._sw - self.WIDTH)  // 2
            py = (self._sh - self.HEIGHT) // 2
            cx, cy = px + self.WIDTH - 18, py + 16
            mx, my = event.pos
            if (mx-cx)**2 + (my-cy)**2 < 100:
                self.close()

    def draw(self) -> None:
        if not self.visible or self._subject is None:
            return
        kind, key = self._subject
        if kind == "sat":
            self._draw_satellite(key)
        else:
            self._draw_planet(key)

    # ── Satellite card ────────────────────────────────────────────────────────

    def _draw_satellite(self, name: str) -> None:
        data = config.SATELLITES_DATA.get(name)
        if not data:
            return
        surf = self._base_surface()
        self._font_title.render(data["full_name"], True, (0,200,255))
        self._blit_title(surf, data["full_name"], data.get("operator",""))
        rows = [
            ("Launched",    data["launched"]),
            ("Altitude",    f"{data['altitude_km']} km"),
            ("Velocity",    f"{data['velocity_kms']} km/s"),
            ("Inclination", f"{data['inclination']}°"),
            ("Period",      f"{data['period_min']} min"),
        ]
        y = self._blit_rows(surf, rows, 60)
        self._blit_desc(surf, data["description"], y + 8)
        self._close_btn(surf)
        self._blit_to_gl(surf)

    # ── Planet card ───────────────────────────────────────────────────────────

    def _draw_planet(self, name: str) -> None:
        data = next((p for p in config.PLANETS_DATA if p["name"] == name), None)
        if not data:
            return
        surf = self._base_surface()
        self._blit_title(surf, data["name"], "Solar System Planet")
        rows = [
            ("Radius",  f"{data['radius']:.2f} × Earth"),
            ("Tilt",    f"{data['tilt']:.1f}°"),
            ("Orbit R", f"{data['orbit_radius']:.0f} sim units"),
            ("Moons",   str(len(data.get("moons", [])))),
            ("Rings",   "Yes" if data.get("rings") else "No"),
        ]
        self._blit_rows(surf, rows, 60)
        self._close_btn(surf)
        self._blit_to_gl(surf)

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _base_surface(self) -> pygame.Surface:
        surf = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        surf.fill((0,0,0,0))
        bg = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        bg.fill((5, 12, 35, 215))
        surf.blit(bg, (0,0))
        pygame.draw.rect(surf, (0,140,220,220), (0,0,self.WIDTH,self.HEIGHT), 1)
        pygame.draw.line(surf, (0,220,255,230), (0,0), (self.WIDTH,0), 3)
        pygame.draw.line(surf, (0,220,255,180), (0,0), (0,self.HEIGHT), 2)
        pygame.draw.circle(surf, (0,80,160,200), (22,22), 14)
        pygame.draw.circle(surf, (0,200,255,200), (22,22), 14, 2)
        return surf

    def _blit_title(self, surf, title, subtitle):
        surf.blit(self._font_title.render(title,    True, (0,200,255)), (44, 12))
        surf.blit(self._font_small.render(subtitle, True, (110,150,190)), (44, 34))
        pygame.draw.line(surf, (0,100,180,160), (12,52), (self.WIDTH-12,52), 1)

    def _blit_rows(self, surf, rows, y_start) -> int:
        y = y_start
        for label, val in rows:
            surf.blit(self._font_small.render(f"{label:<12}", True, (90,150,200)), (16, y))
            surf.blit(self._font_body .render(val,            True, (215,230,255)), (130, y-1))
            y += 18
        return y

    def _blit_desc(self, surf, desc: str, y: int) -> None:
        pygame.draw.line(surf, (0,100,180,120), (12,y), (self.WIDTH-12,y), 1)
        y += 6
        for line in desc.split("\n"):
            surf.blit(self._font_small.render(line.strip(), True, (140,170,210)), (16, y))
            y += 15

    def _close_btn(self, surf) -> None:
        pygame.draw.circle(surf, (20,50,100,200), (self.WIDTH-18,16), 10)
        pygame.draw.circle(surf, (0,180,255,200), (self.WIDTH-18,16), 10, 1)
        surf.blit(self._font_body.render("×", True, (200,220,255)), (self.WIDTH-23, 8))

    def _blit_to_gl(self, surf: pygame.Surface) -> None:
        data = pygame.image.tostring(surf, "RGBA", True)
        glBindTexture(GL_TEXTURE_2D, self._tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.WIDTH, self.HEIGHT,
                     0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        px = (self._sw - self.WIDTH)  // 2
        py = (self._sh - self.HEIGHT) // 2
        gy = self._sh - py - self.HEIGHT

        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, self._sw, 0, self._sh, -1, 1)
        glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex2f(px,              gy)
        glTexCoord2f(1,0); glVertex2f(px+self.WIDTH,   gy)
        glTexCoord2f(1,1); glVertex2f(px+self.WIDTH,   gy+self.HEIGHT)
        glTexCoord2f(0,1); glVertex2f(px,              gy+self.HEIGHT)
        glEnd()
        glDisable(GL_BLEND); glDisable(GL_TEXTURE_2D); glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW);  glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
