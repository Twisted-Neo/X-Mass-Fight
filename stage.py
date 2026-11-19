"""Overhauled holiday arena: parallax mountain backdrop, twinkling lights, icicles, deep under-hull, and ledge markers."""

import math
import random
import arcade

from assets import get_sky_backdrop_texture, get_soft_circle_texture
from config import (
    COLOR_AURORA_A, COLOR_AURORA_B, COLOR_GOLD,
    COLOR_PLATFORM_MAIN, COLOR_PLATFORM_MAIN_EDGE,
    COLOR_PLATFORM_SOFT, COLOR_PLATFORM_SOFT_EDGE,
    WINDOW_HEIGHT, WINDOW_WIDTH,
)

_BULB_COLORS = (
    (255, 80, 90),
    (85, 235, 145),
    (255, 215, 75),
    (95, 185, 255),
)


class Platform:
    def __init__(self, x: float, y: float, width: float, height: float, pass_through: bool = True):
        self.center_x = x
        self.center_y = y
        self.width = width
        self.height = height
        self.pass_through = pass_through

        # Precompute icicle geometry so building static shapes is fast and deterministic
        rng = random.Random(int(x * 13 + y * 7 + width))
        self.icicles = []
        ix = self.left + 22.0
        while ix < self.right - 22.0:
            self.icicles.append((ix, rng.uniform(12.0, 28.0 if not pass_through else 15.0), rng.uniform(4.0, 7.0)))
            ix += rng.uniform(28.0, 52.0)

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

    def build_static_shapes(self, shapes: arcade.shape_list.ShapeElementList):
        """Appends all non-animated platform geometry into a single GPU-batched ShapeElementList."""
        cx, cy, w, h = self.center_x, self.center_y, self.width, self.height

        if not self.pass_through:
            # Deep tapered winter-fortress under-hull for off-stage recovery space & visual depth
            hull_outline = (
                (self.left + 10, self.bottom),
                (self.right - 10, self.bottom),
                (self.right - 113, self.bottom - 107),
                (cx + 197, self.bottom - 177),
                (cx, self.bottom - 207),
                (cx - 197, self.bottom - 177),
                (self.left + 113, self.bottom - 107),
            )
            hull = (
                (self.left + 12, self.bottom),
                (self.right - 12, self.bottom),
                (self.right - 115, self.bottom - 105),
                (cx + 195, self.bottom - 175),
                (cx, self.bottom - 205),
                (cx - 195, self.bottom - 175),
                (self.left + 115, self.bottom - 105),
            )
            mid_hull = (
                (self.left + 64, self.bottom - 4),
                (self.right - 64, self.bottom - 4),
                (self.right - 155, self.bottom - 92),
                (cx + 150, self.bottom - 152),
                (cx, self.bottom - 176),
                (cx - 150, self.bottom - 152),
                (self.left + 155, self.bottom - 92),
            )
            core_hull = (
                (cx - 210, self.bottom - 12),
                (cx + 210, self.bottom - 12),
                (cx + 105, self.bottom - 118),
                (cx, self.bottom - 142),
                (cx - 105, self.bottom - 118),
            )
            shapes.append(arcade.shape_list.create_polygon(hull_outline, (75, 98, 145, 190)))
            shapes.append(arcade.shape_list.create_polygon(hull, (20, 24, 44, 248)))
            shapes.append(arcade.shape_list.create_polygon(mid_hull, (30, 38, 66, 240)))
            shapes.append(arcade.shape_list.create_polygon(core_hull, (44, 58, 96, 225)))

            # Main crimson festive deck + border
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, cy, w + 4, h + 4, COLOR_PLATFORM_MAIN_EDGE))
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, cy, w, h, COLOR_PLATFORM_MAIN))
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, cy - h * 0.25, w - 8, h * 0.42, (135, 22, 38, 255)))

            # Candy-cane diagonal accent blocks along the trim
            stripe_step = 44.0
            sx = self.left + 26.0
            idx = 0
            while sx < self.right - 26.0:
                if idx % 2 == 0:
                    shapes.append(arcade.shape_list.create_rectangle_filled(sx, cy, 16, h - 10, (245, 245, 250, 175)))
                sx += stripe_step
                idx += 1

            # Thick snow blanket along the top surface
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, self.top - 4, w + 4, 9, (240, 247, 255, 255)))
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, self.top - 9, w - 10, 4, (185, 215, 245, 220)))

            # Hanging icicles
            for ix, length, half_base in self.icicles:
                tri = (
                    (ix - half_base, self.bottom),
                    (ix + half_base, self.bottom),
                    (ix, self.bottom - length),
                )
                shapes.append(arcade.shape_list.create_polygon(tri, (195, 230, 255, 200)))
        else:
            # Soft pass-through floating holiday platform
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, cy - 5, w + 6, h + 4, (0, 0, 0, 115)))
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, cy, w + 4, h + 4, COLOR_PLATFORM_SOFT_EDGE))
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, cy, w, h, COLOR_PLATFORM_SOFT))
            shapes.append(arcade.shape_list.create_rectangle_filled(cx, self.top - 3, w + 4, 6, (235, 246, 255, 245)))

            for ix, length, half_base in self.icicles:
                tri = (
                    (ix - half_base * 0.8, self.bottom),
                    (ix + half_base * 0.8, self.bottom),
                    (ix, self.bottom - length * 0.75),
                )
                shapes.append(arcade.shape_list.create_polygon(tri, (185, 235, 235, 175)))

    def draw_dynamic(self, time: float = 0.0):
        """Draws only the animated ledge grip markers."""
        if self.pass_through:
            return
        grip_pulse = int(190 + 65 * math.sin(time * 5.0))
        grip_col = (COLOR_GOLD[0], COLOR_GOLD[1], COLOR_GOLD[2], grip_pulse)
        for edge_x, sign in ((self.left, 1), (self.right, -1)):
            arcade.draw_rect_filled(arcade.XYWH(edge_x + sign * 8, self.top - 3, 18, 7), grip_col)
            arcade.draw_rect_filled(arcade.XYWH(edge_x + sign * 2, self.top - 12, 6, 22), grip_col)


def _build_ridge_shapes(peaks: tuple[tuple[float, float], ...], color: tuple) -> arcade.shape_list.ShapeElementList:
    """Decomposes a mountain skyline into strictly convex vertical trapezoids for ShapeElementList."""
    shapes = arcade.shape_list.ShapeElementList()
    for (x1, y1), (x2, y2) in zip(peaks, peaks[1:]):
        quad = ((x1, 0), (x1, y1), (x2, y2), (x2, 0))
        shapes.append(arcade.shape_list.create_polygon(quad, color))
    return shapes


class HolidayStage:
    """Combines pre-baked sky, batched parallax mountains, batched stars/snow/lights, and static stage geometry."""

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
            s.center_y = random.uniform(WINDOW_HEIGHT * 0.18, WINDOW_HEIGHT)
            base_a = random.randint(100, 255)
            s.alpha = base_a
            self.star_list.append(s)
            self.star_meta.append((random.uniform(0, math.tau), random.uniform(1.2, 3.0), base_a))

        # Batched snow (1 GPU draw call)
        self.snow_list = arcade.SpriteList()
        self.snow_meta = []
        for _ in range(snow_count):
            f = arcade.Sprite(circle_tex, scale=random.uniform(0.10, 0.28))
            f.center_x = random.uniform(-300, WINDOW_WIDTH + 300)
            f.center_y = random.uniform(-80, WINDOW_HEIGHT + 300)
            f.alpha = random.randint(140, 245)
            self.snow_list.append(f)
            self.snow_meta.append([
                random.uniform(50.0, 145.0),
                random.uniform(-25.0, 25.0),
                random.uniform(0.0, math.tau),
                random.uniform(1.5, 3.5),
            ])

        # Batched parallax mountain ranges (2 GPU draw calls)
        far_peaks = (
            (-120, 230), (180, 390), (460, 250), (760, 450),
            (1080, 270), (1420, 430), (1740, 260), (2040, 370),
        )
        self.far_mountain_shapes = _build_ridge_shapes(far_peaks, (18, 22, 46, 220))
        for peak_x, peak_y in ((180, 390), (760, 450), (1420, 430)):
            cap = ((peak_x, peak_y), (peak_x - 68, peak_y - 46), (peak_x + 68, peak_y - 46))
            self.far_mountain_shapes.append(arcade.shape_list.create_polygon(cap, (195, 215, 245, 95)))

        near_peaks = (
            (-120, 150), (310, 265), (640, 165), (960, 290),
            (1310, 175), (1660, 275), (2040, 160),
        )
        self.near_mountain_shapes = _build_ridge_shapes(near_peaks, (13, 16, 36, 240))

        self.platforms = [
            Platform(WINDOW_WIDTH * 0.50, 195, 1120, 50, pass_through=False),
            Platform(WINDOW_WIDTH * 0.22, 385,  340, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.78, 385,  340, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.50, 555,  400, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.50, 725,  240, 22, pass_through=True),
        ] if include_platforms else []

        # Batched static platforms + batched twinkling holiday bulbs (2 GPU draw calls total)
        self.static_stage_shapes = arcade.shape_list.ShapeElementList()
        self.bulb_list = arcade.SpriteList()
        self.bulb_meta = []

        for plat in self.platforms:
            plat.build_static_shapes(self.static_stage_shapes)
            if not plat.pass_through:
                bulb_x = plat.left + 28.0
                b_idx = 0
                while bulb_x < plat.right - 28.0:
                    col = _BULB_COLORS[b_idx % len(_BULB_COLORS)]
                    by = plat.bottom - 5.0 - abs(math.sin(b_idx * 0.65)) * 5.0

                    halo = arcade.Sprite(circle_tex, scale=18.0 / 28.0)
                    halo.center_x, halo.center_y = bulb_x, by
                    halo.color = col

                    core = arcade.Sprite(circle_tex, scale=8.4 / 28.0)
                    core.center_x, core.center_y = bulb_x, by
                    core.color = col

                    self.bulb_list.append(halo)
                    self.bulb_list.append(core)
                    self.bulb_meta.append((halo, core, b_idx))

                    bulb_x += 46.0
                    b_idx += 1

    def update(self, dt: float):
        self.time += dt

        for sprite, (phase, speed, base_a) in zip(self.star_list, self.star_meta):
            sprite.alpha = int(base_a * (0.65 + 0.35 * math.sin(self.time * speed + phase)))

        for halo, core, b_idx in self.bulb_meta:
            pulse = 0.65 + 0.35 * math.sin(self.time * 4.2 + b_idx * 0.9)
            halo.alpha = int(55 * pulse)
            core.alpha = int(180 + 75 * pulse)

        for sprite, meta in zip(self.snow_list, self.snow_meta):
            fall_spd, drift, phase, freq = meta
            phase += freq * dt
            meta[2] = phase
            sprite.center_y -= fall_spd * dt
            sprite.center_x += (drift + math.sin(phase) * 24.0) * dt
            if sprite.center_y < -220:
                sprite.center_y = WINDOW_HEIGHT + 320
                sprite.center_x = random.uniform(-360, WINDOW_WIDTH + 360)
            if sprite.center_x < -380:
                sprite.center_x = WINDOW_WIDTH + 380
            elif sprite.center_x > WINDOW_WIDTH + 380:
                sprite.center_x = -380

    def draw_backdrop(self, cam_x: float = WINDOW_WIDTH * 0.5, cam_y: float = WINDOW_HEIGHT * 0.5):
        arcade.draw_texture_rect(
            self.sky_tex,
            arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT),
        )

        px = (cam_x - WINDOW_WIDTH * 0.5) * 0.08
        py = (cam_y - WINDOW_HEIGHT * 0.5) * 0.05

        # Subtle aurora ribbons
        for i in range(5):
            y = WINDOW_HEIGHT * 0.68 + i * 24 + math.sin(self.time * 0.45 + i) * 14 - py * 0.4
            a = max(0, min(255, 22 + int(14 * math.sin(self.time * 0.7 + i * 0.8))))
            arcade.draw_rect_filled(
                arcade.XYWH(WINDOW_WIDTH * 0.5, y, WINDOW_WIDTH, 11),
                (COLOR_AURORA_A[0], COLOR_AURORA_A[1], COLOR_AURORA_A[2], a),
            )
        for i in range(3):
            y = WINDOW_HEIGHT * 0.52 + i * 32 + math.cos(self.time * 0.35 + i) * 18 - py * 0.4
            a = max(0, min(255, 18 + int(12 * math.cos(self.time * 0.6 + i))))
            arcade.draw_rect_filled(
                arcade.XYWH(WINDOW_WIDTH * 0.5, y, WINDOW_WIDTH, 9),
                (COLOR_AURORA_B[0], COLOR_AURORA_B[1], COLOR_AURORA_B[2], a),
            )

        self.star_list.draw()

        self.far_mountain_shapes.center_x = -px
        self.far_mountain_shapes.center_y = -py
        self.far_mountain_shapes.draw()

        self.near_mountain_shapes.center_x = -px * 1.6
        self.near_mountain_shapes.center_y = -py * 1.4
        self.near_mountain_shapes.draw()

    def draw_foreground(self):
        self.snow_list.draw()
        if self.platforms:
            self.static_stage_shapes.draw()
            self.bulb_list.draw()
            for plat in self.platforms:
                plat.draw_dynamic(self.time)

    def draw_fighter_shadows(self, fighters: tuple):
        """Projects a soft ground shadow onto the highest platform directly beneath each fighter."""
        for f in fighters:
            if f.is_ko_waiting or f.is_ledge_hanging:
                continue
            best_top = None
            best_plat = None
            for plat in self.platforms:
                if plat.left + 6 <= f.hurt_center_x <= plat.right - 6 and plat.top <= f.hurt_bottom + 8:
                    if best_top is None or plat.top > best_top:
                        best_top = plat.top
                        best_plat = plat

            if best_top is None or best_plat is None:
                continue

            dist = max(0.0, f.hurt_bottom - best_top)
            if dist > 420.0:
                continue

            fade = 1.0 - (dist / 420.0)
            shadow_w = max(18.0, f.body_width * (0.55 + 0.55 * fade))
            shadow_h = max(5.0, 12.0 * (0.45 + 0.55 * fade))
            alpha = int(145 * (fade ** 1.3))
            arcade.draw_ellipse_filled(f.hurt_center_x, best_top + 1.5, shadow_w, shadow_h, (8, 10, 22, alpha))