"""Stage platforms and GPU-batched holiday night sky, aurora, stars, and snow."""

import math
import random
import arcade

from assets import get_sky_backdrop_texture, get_soft_circle_texture
from config import (
    COLOR_AURORA_A, COLOR_AURORA_B,
    COLOR_PLATFORM_MAIN, COLOR_PLATFORM_MAIN_EDGE,
    COLOR_PLATFORM_SOFT, COLOR_PLATFORM_SOFT_EDGE,
    WINDOW_HEIGHT, WINDOW_WIDTH,
)


class Platform:
    def __init__(self, x: float, y: float, width: float, height: float, pass_through: bool = True):
        self.center_x = x
        self.center_y = y
        self.width = width
        self.height = height
        self.pass_through = pass_through

    @property
    def top(self) -> float:
        return self.center_y + self.height * 0.5

    @property
    def bottom(self) -> float:
        return self.center_y - self.height * 0.5

    @property
    def left(self) -> float:
        return self.center_x - self.width * 0.5

    @property
    def right(self) -> float:
        return self.center_x + self.width * 0.5

    def draw(self):
        cx, cy, w, h = self.center_x, self.center_y, self.width, self.height
        body, edge = (
            (COLOR_PLATFORM_SOFT, COLOR_PLATFORM_SOFT_EDGE)
            if self.pass_through
            else (COLOR_PLATFORM_MAIN, COLOR_PLATFORM_MAIN_EDGE)
        )
        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 6, w + 8, h + 6), (0, 0, 0, 125))
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), body)
        arcade.draw_rect_filled(arcade.XYWH(cx, cy + h * 0.5 - 4, w, 5), edge)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), edge, border_width=2)


class HolidayStage:
    """Combines pre-baked sky, batched SpriteList stars & snow, and stage platforms."""

    def __init__(self, include_platforms: bool = True, snow_count: int = 110):
        self.sky_tex = get_sky_backdrop_texture()
        circle_tex = get_soft_circle_texture()
        self.time = 0.0

        # Batched stars (1 GPU draw call)
        self.star_list = arcade.SpriteList()
        self.star_meta = []
        for _ in range(180):
            s = arcade.Sprite(circle_tex, scale=random.uniform(0.05, 0.16))
            s.center_x = random.uniform(0, WINDOW_WIDTH)
            s.center_y = random.uniform(WINDOW_HEIGHT * 0.15, WINDOW_HEIGHT)
            base_a = random.randint(100, 255)
            s.alpha = base_a
            self.star_list.append(s)
            self.star_meta.append((random.uniform(0, math.tau), random.uniform(1.2, 3.0), base_a))

        # Batched snow (1 GPU draw call)
        self.snow_list = arcade.SpriteList()
        self.snow_meta = []
        for _ in range(snow_count):
            f = arcade.Sprite(circle_tex, scale=random.uniform(0.10, 0.28))
            f.center_x = random.uniform(0, WINDOW_WIDTH)
            f.center_y = random.uniform(0, WINDOW_HEIGHT)
            f.alpha = random.randint(140, 245)
            self.snow_list.append(f)
            self.snow_meta.append([
                random.uniform(50.0, 145.0),   # fall speed px/sec
                random.uniform(-25.0, 25.0),   # base wind drift
                random.uniform(0.0, math.tau), # wobble phase
                random.uniform(1.5, 3.5),      # wobble freq
            ])

        self.platforms = [
            Platform(WINDOW_WIDTH * 0.50, 140, 1120, 50, pass_through=False),
            Platform(WINDOW_WIDTH * 0.22, 330,  340, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.78, 330,  340, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.50, 500,  400, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.50, 670,  240, 22, pass_through=True),
        ] if include_platforms else []

    def update(self, dt: float):
        self.time += dt

        for sprite, (phase, speed, base_a) in zip(self.star_list, self.star_meta):
            sprite.alpha = int(base_a * (0.65 + 0.35 * math.sin(self.time * speed + phase)))

        for sprite, meta in zip(self.snow_list, self.snow_meta):
            fall_spd, drift, phase, freq = meta
            phase += freq * dt
            meta[2] = phase
            sprite.center_y -= fall_spd * dt
            sprite.center_x += (drift + math.sin(phase) * 24.0) * dt
            if sprite.center_y < -12:
                sprite.center_y = WINDOW_HEIGHT + 12
                sprite.center_x = random.uniform(0, WINDOW_WIDTH)
            if sprite.center_x < -12:
                sprite.center_x = WINDOW_WIDTH + 12
            elif sprite.center_x > WINDOW_WIDTH + 12:
                sprite.center_x = -12

    def draw_backdrop(self):
        arcade.draw_texture_rect(
            self.sky_tex,
            arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT),
        )
        # Subtle aurora ribbons
        for i in range(5):
            y = WINDOW_HEIGHT * 0.66 + i * 24 + math.sin(self.time * 0.45 + i) * 14
            a = max(0, min(255, 22 + int(14 * math.sin(self.time * 0.7 + i * 0.8))))
            arcade.draw_rect_filled(
                arcade.XYWH(WINDOW_WIDTH * 0.5, y, WINDOW_WIDTH, 11),
                (COLOR_AURORA_A[0], COLOR_AURORA_A[1], COLOR_AURORA_A[2], a),
            )
        for i in range(3):
            y = WINDOW_HEIGHT * 0.48 + i * 32 + math.cos(self.time * 0.35 + i) * 18
            a = max(0, min(255, 18 + int(12 * math.cos(self.time * 0.6 + i))))
            arcade.draw_rect_filled(
                arcade.XYWH(WINDOW_WIDTH * 0.5, y, WINDOW_WIDTH, 9),
                (COLOR_AURORA_B[0], COLOR_AURORA_B[1], COLOR_AURORA_B[2], a),
            )
        self.star_list.draw()

    def draw_foreground(self):
        self.snow_list.draw()
        for plat in self.platforms:
            plat.draw()