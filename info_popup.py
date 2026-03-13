"""
info_popup.py — Floating glass-card satellite info popup.
Shown when the user clicks on a satellite in Solar view.
"""
import pygame
from OpenGL.GL import *

import config


class InfoPopup:
    WIDTH  = 380
    HEIGHT = 270

    def __init__(self, screen_w: int, screen_h: int):
        self._sw = screen_w
        self._sh = screen_h
        self.visible   = False
        self._sat_name = None
        self._tex      = glGenTextures(1)

        pygame.font.init()
        try:
            self._font_title = pygame.font.SysFont("monospace", 17, bold=True)
            self._font_body  = pygame.font.SysFont("monospace", 13)
            self._font_small = pygame.font.SysFont("monospace", 11)
        except Exception:
            self._font_title = pygame.font.Font(None, 20)
            self._font_body  = pygame.font.Font(None, 16)
            self._font_small = pygame.font.Font(None, 13)

    # ── API ───────────────────────────────────────────────────────────────────

    def show(self, sat_name: str) -> None:
        self._sat_name = sat_name
        self.visible   = True

    def close(self) -> None:
        self.visible = False

    def handle_event(self, event) -> None:
        if not self.visible:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if close button hit (top-right corner of popup)
            px = (self._sw - self.WIDTH)  // 2
            py = (self._sh - self.HEIGHT) // 2
            cx, cy, cr = px + self.WIDTH - 18, py + 16, 10
            mx, my = event.pos
            if (mx - cx)**2 + (my - cy)**2 < cr**2:
                self.close()

    def draw(self) -> None:
        if not self.visible or self._sat_name is None:
            return
        data = config.SATELLITES_DATA.get(self._sat_name)
        if data is None:
            return

        surf = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Background glass card
        bg = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        bg.fill((5, 12, 35, 210))
        surf.blit(bg, (0, 0))

        # Accent borders
        pygame.draw.rect(surf, (0, 140, 220, 220), (0, 0, self.WIDTH, self.HEIGHT), 1)
        pygame.draw.line(surf, (0, 220, 255, 230), (0, 0), (self.WIDTH, 0), 3)
        pygame.draw.line(surf, (0, 220, 255, 180), (0, 0), (0, self.HEIGHT), 2)

        # NASA logo circle (top-left)
        pygame.draw.circle(surf, (0, 80, 160, 200), (22, 22), 14)
        pygame.draw.circle(surf, (0, 200, 255, 200), (22, 22), 14, 2)

        # Title
        t_surf = self._font_title.render(data["full_name"], True, (0, 200, 255))
        surf.blit(t_surf, (44, 12))

        # Operator tag
        op_surf = self._font_small.render(f"Operator: {data['operator']}", True, (120, 160, 200))
        surf.blit(op_surf, (44, 34))

        # Separator line
        pygame.draw.line(surf, (0, 100, 180, 160), (12, 52), (self.WIDTH - 12, 52), 1)

        # Key-value data rows
        rows = [
            ("Launched",    data["launched"]),
            ("Altitude",    f"{data['altitude_km']} km"),
            ("Velocity",    f"{data['velocity_kms']} km/s"),
            ("Inclination", f"{data['inclination']}°"),
            ("Period",      f"{data['period_min']} min"),
        ]
        y = 60
        for label, val in rows:
            label_s = self._font_small.render(f"{label:<12}", True, (100, 160, 210))
            val_s   = self._font_body .render(val,            True, (220, 235, 255))
            surf.blit(label_s, (16, y))
            surf.blit(val_s,   (130, y - 1))
            y += 18

        # Separator
        pygame.draw.line(surf, (0, 100, 180, 120), (12, y + 2), (self.WIDTH - 12, y + 2), 1)
        y += 8

        # Description (wrap at ~50 chars)
        for line in data["description"].split("\n"):
            ds = self._font_small.render(line.strip(), True, (150, 180, 220))
            surf.blit(ds, (16, y))
            y += 15

        # Close button ×
        pygame.draw.circle(surf, (20, 50, 100, 200), (self.WIDTH - 18, 16), 10)
        pygame.draw.circle(surf, (0, 180, 255, 200), (self.WIDTH - 18, 16), 10, 1)
        xs = self._font_body.render("×", True, (200, 220, 255))
        surf.blit(xs, (self.WIDTH - 23, 8))

        # Render to screen
        px = (self._sw - self.WIDTH)  // 2
        py = (self._sh - self.HEIGHT) // 2
        self._blit_to_gl(surf, px, py)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _blit_to_gl(self, surf: pygame.Surface, px: int, py: int) -> None:
        data = pygame.image.tostring(surf, "RGBA", True)

        glBindTexture(GL_TEXTURE_2D, self._tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                     self.WIDTH, self.HEIGHT, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix(); glLoadIdentity()
        glOrtho(0, self._sw, 0, self._sh, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix(); glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)

        # Flip py because OpenGL Y=0 is bottom
        gy = self._sh - py - self.HEIGHT

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(px,               gy)
        glTexCoord2f(1, 0); glVertex2f(px + self.WIDTH,  gy)
        glTexCoord2f(1, 1); glVertex2f(px + self.WIDTH,  gy + self.HEIGHT)
        glTexCoord2f(0, 1); glVertex2f(px,               gy + self.HEIGHT)
        glEnd()

        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW);  glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
