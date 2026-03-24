"""
hud.py — NASA-themed HUD with time-control toolbar.

Layout
------
  Top-left panel   : mode + selected object data
  Top-right        : sim clock
  Bottom toolbar   : PAUSE | 1× | 10× | 50× speed buttons  +  key legend
"""
import math
import pygame
from OpenGL.GL import *
import config


class HUD:
    _fonts_loaded = False
    _font_lg = _font_md = _font_sm = None

    # Time-control button rects (screen coords, populated in draw())
    _btn_rects: list = []

    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h
        self._tex = glGenTextures(1)
        self._ensure_fonts()

    @classmethod
    def _ensure_fonts(cls):
        if cls._fonts_loaded:
            return
        pygame.font.init()
        try:
            cls._font_lg = pygame.font.SysFont("monospace", 18, bold=True)
            cls._font_md = pygame.font.SysFont("monospace", 14)
            cls._font_sm = pygame.font.SysFont("monospace", 12)
        except Exception:
            cls._font_lg = pygame.font.Font(None, 22)
            cls._font_md = pygame.font.Font(None, 17)
            cls._font_sm = pygame.font.Font(None, 14)
        cls._fonts_loaded = True

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self, camera, scene) -> None:
        surf = pygame.Surface((self._w, self._h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        self._draw_info_panel(surf, camera, scene)
        self._draw_clock(surf, scene.sim_time)
        self._draw_toolbar(surf, scene.time_scale)
        self._draw_legend(surf)

        self._upload_and_draw(surf)

    # ── Info panel (top-left) ─────────────────────────────────────────────────

    def _draw_info_panel(self, surf, camera, scene):
        panel_w, panel_h = 310, 148
        self._panel(surf, 14, 14, panel_w, panel_h)

        self._text(surf, "NASA ORBITAL SIMULATION", 24, 24,
                   self._font_lg, (0, 192, 255))

        mode_labels = {
            config.CAM_MODE_SOLAR:  "SOLAR SYSTEM VIEW",
            config.CAM_MODE_PLANET: f"PLANET TPP — {config.PLANETS_DATA[camera.planet_idx]['name'].upper()}",
            config.CAM_MODE_SAT_TPP: f"SATELLITE TPP — {list(config.SATELLITES_DATA)[camera.sat_idx]}",
        }
        self._text(surf, mode_labels.get(camera.mode, ""), 24, 46,
                   self._font_md, (180, 210, 255))

        y = 68
        if camera.mode == config.CAM_MODE_SAT_TPP:
            sat_name = list(config.SATELLITES_DATA)[camera.sat_idx]
            sdata = config.SATELLITES_DATA[sat_name]
            rows = [
                ("Altitude",    f"{sdata['altitude_km']} km"),
                ("Velocity",    f"{sdata['velocity_kms']} km/s"),
                ("Inclination", f"{sdata['inclination']}°"),
                ("Period",      f"{sdata['period_min']} min"),
                ("Operator",    sdata["operator"][:28]),
            ]
        elif camera.mode == config.CAM_MODE_PLANET:
            pdata = config.PLANETS_DATA[camera.planet_idx]
            rows = [
                ("Radius",  f"{pdata['radius']:.2f} Earth R"),
                ("Tilt",    f"{pdata['tilt']:.1f}°"),
                ("Moons",   str(len(pdata.get('moons', [])))),
                ("Rings",   "Yes" if pdata.get("rings") else "No"),
            ]
        else:
            rows = [
                ("Planets", "8"),
                ("Satellites", "3 (Earth orbit)"),
                ("Drag", "Rotate view"),
                ("Scroll", "Zoom"),
            ]

        for label, val in rows:
            self._text(surf, f"{label:<12}: {val}", 24, y, self._font_sm,
                       (140, 190, 230))
            y += 16

    # ── Sim clock (top-right) ─────────────────────────────────────────────────

    def _draw_clock(self, surf, sim_time: float):
        h  = int(sim_time // 3600)
        m  = int((sim_time % 3600) // 60)
        s  = int(sim_time % 60)
        elapsed = f"T+  {h:02d}:{m:02d}:{s:02d}"
        self._text(surf, elapsed, self._w - 145, 14, self._font_md, (0, 192, 255))

    # ── Toolbar (bottom) ──────────────────────────────────────────────────────

    def _draw_toolbar(self, surf, current_scale: float):
        bar_h  = 36
        bar_y  = self._h - bar_h - 4
        bar_w  = self._w
        bar = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        bar.fill((4, 8, 22, 180))
        pygame.draw.line(bar, (0, 120, 200, 180), (0, 0), (bar_w, 0), 1)
        surf.blit(bar, (0, bar_y))

        # Speed buttons
        btn_w, btn_h = 72, 24
        btn_y = bar_y + (bar_h - btn_h) // 2
        start_x = 16
        HUD._btn_rects = []

        for i, (scale, label) in enumerate(
                zip(config.TIME_SCALES, config.TIME_SCALE_LABELS)):
            bx = start_x + i * (btn_w + 8)
            active = abs(scale - current_scale) < 0.01
            bg_col = (0, 140, 240, 200) if active else (10, 20, 50, 180)
            bd_col = (0, 200, 255, 220) if active else (0, 80, 160, 180)
            txt_col = (255, 255, 255) if active else (140, 180, 220)

            btn = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            btn.fill(bg_col)
            pygame.draw.rect(btn, bd_col, (0, 0, btn_w, btn_h), 1)
            lbl = self._font_sm.render(label, True, txt_col)
            btn.blit(lbl, ((btn_w - lbl.get_width())//2,
                           (btn_h - lbl.get_height())//2))
            surf.blit(btn, (bx, btn_y))
            HUD._btn_rects.append(pygame.Rect(bx, btn_y, btn_w, btn_h))

        # Legend on the right side of toolbar
        legend = "[1] Solar  [2] Planet  [3] Sat  [Tab] Next  [Esc] Quit"
        lx = start_x + len(config.TIME_SCALES) * (btn_w + 8) + 20
        self._text(surf, legend, lx, btn_y + 5, self._font_sm, (90, 130, 170))

    def _draw_legend(self, surf):
        pass  # legend is now in toolbar

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _panel(surf, x, y, w, h, alpha=145):
        p = pygame.Surface((w, h), pygame.SRCALPHA)
        p.fill((4, 8, 20, alpha))
        pygame.draw.rect(p, (0, 120, 200, 200), (0, 0, w, h), 1)
        pygame.draw.line(p, (0, 192, 255, 180), (0, 0), (w, 0), 2)
        surf.blit(p, (x, y))

    @staticmethod
    def _text(surf, text, x, y, font, color):
        surf.blit(font.render(text, True, color), (x, y))

    # ── GL blit ───────────────────────────────────────────────────────────────

    def _upload_and_draw(self, surf: pygame.Surface) -> None:
        data = pygame.image.tostring(surf, "RGBA", True)
        glBindTexture(GL_TEXTURE_2D, self._tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self._w, self._h,
                     0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, self._w, 0, self._h, -1, 1)
        glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex2f(0,       0)
        glTexCoord2f(1,0); glVertex2f(self._w, 0)
        glTexCoord2f(1,1); glVertex2f(self._w, self._h)
        glTexCoord2f(0,1); glVertex2f(0,       self._h)
        glEnd()
        glDisable(GL_BLEND); glDisable(GL_TEXTURE_2D); glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION); glPopMatrix()
        glMatrixMode(GL_MODELVIEW);  glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)

    # ── Hit-test for toolbar clicks ───────────────────────────────────────────

    @staticmethod
    def handle_click(pos) -> float | None:
        """
        Returns the new time_scale if a toolbar button was clicked, else None.
        """
        for i, rect in enumerate(HUD._btn_rects):
            if rect.collidepoint(pos):
                return config.TIME_SCALES[i]
        return None
