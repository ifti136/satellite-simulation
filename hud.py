"""
hud.py — NASA-themed on-screen HUD rendered as an OpenGL texture quad.
"""
import math
import numpy as np
import pygame
from OpenGL.GL import *

import config


class HUD:
    # Fonts loaded once
    _fonts_loaded = False
    _font_lg  = None
    _font_md  = None
    _font_sm  = None

    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h
        self._tex = glGenTextures(1)
        self._ensure_fonts()

    # ── Font init ─────────────────────────────────────────────────────────────

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

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, camera, satellites, earth_wp, sim_time: float) -> None:
        surf = pygame.Surface((self._w, self._h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        SAT_NAMES = ["ISS", "Hubble", "Starlink"]

        # ── Top-left panel ────────────────────────────────────────────────────
        panel_w, panel_h = 320, 140
        self._draw_panel(surf, 14, 14, panel_w, panel_h)

        mode_label = {
            config.CAM_MODE_SOLAR:     "SOLAR SYSTEM VIEW",
            config.CAM_MODE_EARTH_TPP: "EARTH — THIRD PERSON",
            config.CAM_MODE_SAT_TPP:   f"SATELLITE TPP — {SAT_NAMES[camera.sat_idx]}",
        }.get(camera.mode, "")

        self._text(surf, "NASA ORBITAL SIMULATION", 24, 24,  self._font_lg,
                   (  0, 192, 255))
        self._text(surf, mode_label,                  24, 46,  self._font_md,
                   (200, 220, 255))

        # Selected satellite data
        sat   = satellites[camera.sat_idx]
        sdata = sat.data
        y     = 68
        items = [
            ("Altitude",   f"{sdata['altitude_km']} km"),
            ("Velocity",   f"{sdata['velocity_kms']} km/s"),
            ("Inclination",f"{sdata['inclination']}°"),
            ("Period",     f"{sdata['period_min']} min"),
        ]
        for label, value in items:
            self._text(surf, f"{label:<12}: {value}", 24, y, self._font_sm,
                       (160, 200, 240))
            y += 16

        # ── Bottom key legend ─────────────────────────────────────────────────
        legend_y = self._h - 26
        keys = "[1] Solar  [2] Earth  [3] Satellite  [Tab] Next Sat  [Scroll] Zoom  [Click] Info"
        self._text(surf, keys, 10, legend_y, self._font_sm, (100, 140, 180))

        # Sim time (top-right)
        elapsed = f"T+ {int(sim_time // 60):02d}:{int(sim_time % 60):02d}"
        self._text(surf, elapsed, self._w - 110, 14, self._font_md, (0, 192, 255))

        # Upload surface as texture and blit as 2D quad
        self._upload_and_draw(surf)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_panel(surf, x, y, w, h, alpha=140):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((4, 8, 20, alpha))
        pygame.draw.rect(panel, (0, 120, 200, 200), (0, 0, w, h), 1)
        pygame.draw.line(panel, (0, 192, 255, 180), (0, 0), (w, 0), 2)
        surf.blit(panel, (x, y))

    @staticmethod
    def _text(surf, text, x, y, font, color):
        rendered = font.render(text, True, color)
        surf.blit(rendered, (x, y))

    def _upload_and_draw(self, surf: pygame.Surface) -> None:
        data = pygame.image.tostring(surf, "RGBA", True)

        glBindTexture(GL_TEXTURE_2D, self._tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA,
                     self._w, self._h, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        # Orthographic 2-D pass
        glMatrixMode(GL_PROJECTION)
        glPushMatrix(); glLoadIdentity()
        glOrtho(0, self._w, 0, self._h, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix(); glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0,       0)
        glTexCoord2f(1, 0); glVertex2f(self._w, 0)
        glTexCoord2f(1, 1); glVertex2f(self._w, self._h)
        glTexCoord2f(0, 1); glVertex2f(0,       self._h)
        glEnd()

        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glBindTexture(GL_TEXTURE_2D, 0)
