"""Gradient sky, aurora, twinkling stars, and a moon."""

import math
import random

import arcade

from arcade_compat import draw_filled_rectangle
from config import (
    COLOR_AURORA_A, COLOR_AURORA_B,
    COLOR_BG_BOTTOM, COLOR_BG_TOP,
    COLOR_MOON, COLOR_STAR,
    WINDOW_HEIGHT, WINDOW_WIDTH,
)


class Background:
    def __init__(self):
        self.stars = [
            {
                "x": random.uniform(0, WINDOW_WIDTH),
                "y": random.uniform(0, WINDOW_HEIGHT),
                "size": random.uniform(0.5, 2.5),
                "phase": random.uniform(0, math.tau),
                "speed": random.uniform(0.01, 0.04),
                "base_alpha": random.randint(80, 255),
            }
            for _ in range(180)
        ]
        self.time = 0.0
        self.moon_x = WINDOW_WIDTH * 0.82
        self.moon_y = WINDOW_HEIGHT * 0.78

    def update(self, dt):
        self.time += dt
        for s in self.stars:
            s["phase"] += s["speed"]

    def draw(self):
        # Sky gradient (banded)
        bands = 24
        band_h = WINDOW_HEIGHT / bands
        for i in range(bands):
            t = i / (bands - 1)
            r = int(COLOR_BG_TOP[0] * (1 - t) + COLOR_BG_BOTTOM[0] * t)
            g = int(COLOR_BG_TOP[1] * (1 - t) + COLOR_BG_BOTTOM[1] * t)
            b = int(COLOR_BG_TOP[2] * (1 - t) + COLOR_BG_BOTTOM[2] * t)
            y = WINDOW_HEIGHT - i * band_h - band_h / 2
            draw_filled_rectangle(
                WINDOW_WIDTH / 2, y, WINDOW_WIDTH, band_h + 2, (r, g, b, 255),
            )

        # Aurora bands
        for i in range(6):
            y = WINDOW_HEIGHT * 0.62 + i * 22 + math.sin(self.time * 0.3 + i) * 15
            alpha = 20 + int(15 * math.sin(self.time * 0.5 + i * 0.7))
            alpha = max(0, min(255, alpha))
            draw_filled_rectangle(
                WINDOW_WIDTH / 2, y, WINDOW_WIDTH, 8,
                (COLOR_AURORA_A[0], COLOR_AURORA_A[1], COLOR_AURORA_A[2], alpha),
            )
        for i in range(4):
            y = WINDOW_HEIGHT * 0.42 + i * 30 + math.cos(self.time * 0.25 + i) * 20
            alpha = 15 + int(12 * math.cos(self.time * 0.4 + i))
            alpha = max(0, min(255, alpha))
            draw_filled_rectangle(
                WINDOW_WIDTH / 2, y, WINDOW_WIDTH, 6,
                (COLOR_AURORA_B[0], COLOR_AURORA_B[1], COLOR_AURORA_B[2], alpha),
            )

        # Twinkling stars
        for s in self.stars:
            a = int(s["base_alpha"] * (0.6 + 0.4 * math.sin(s["phase"])))
            a = max(0, min(255, a))
            arcade.draw_circle_filled(
                s["x"], s["y"], s["size"],
                (COLOR_STAR[0], COLOR_STAR[1], COLOR_STAR[2], a),
            )

        # Moon with soft halo + craters
        for r in range(110, 30, -10):
            a = int(6 * (110 - r) / 80)
            arcade.draw_circle_filled(
                self.moon_x, self.moon_y, r,
                (COLOR_MOON[0], COLOR_MOON[1], COLOR_MOON[2], a),
            )
        arcade.draw_circle_filled(self.moon_x, self.moon_y, 38, COLOR_MOON)
        arcade.draw_circle_filled(
            self.moon_x - 12, self.moon_y + 8, 8,
            (COLOR_MOON[0] - 25, COLOR_MOON[1] - 25, COLOR_MOON[2] - 25, 255),
        )
        arcade.draw_circle_filled(
            self.moon_x + 10, self.moon_y - 6, 6,
            (COLOR_MOON[0] - 15, COLOR_MOON[1] - 15, COLOR_MOON[2] - 15, 255),
        )