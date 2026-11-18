"""GPU-batched SpriteList particles, shockwave rings, and cached floating callouts."""

import math
import random
import arcade

from assets import get_soft_circle_texture
from config import COLOR_HIT_SPARKS, COLOR_KO_SPARKS


class _Shockwave:
    __slots__ = ("x", "y", "radius", "max_radius", "color", "life", "max_life")

    def __init__(self, x: float, y: float, max_radius: float, color: tuple):
        self.x = x
        self.y = y
        self.radius = 8.0
        self.max_radius = max_radius
        self.color = color
        self.life = 15
        self.max_life = 15

    def update(self) -> bool:
        self.radius += (self.max_radius - self.radius) * 0.26
        self.life -= 1
        return self.life > 0


class _FloatingCallout:
    __slots__ = ("label", "life", "max_life", "rgb")

    def __init__(self, x: float, y: float, text: str, rgb: tuple):
        self.rgb = rgb
        self.life = 38
        self.max_life = 38
        self.label = arcade.Text(
            text, x, y, (*rgb, 255),
            font_size=22, anchor_x="center", bold=True,
        )

    def update(self) -> bool:
        self.label.y += 1.6
        self.life -= 1
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        self.label.color = (*self.rgb, alpha)
        return self.life > 0


class EffectSystem:
    def __init__(self):
        self.circle_tex = get_soft_circle_texture()
        self.particle_sprites = arcade.SpriteList()
        self.particle_data = []  # [vx, vy, gravity, drag, life, max_life]
        self.shockwaves: list[_Shockwave] = []
        self.callouts: list[_FloatingCallout] = []

    def _spawn(self, x: float, y: float, vx: float, vy: float, radius: float, color: tuple, life: int, gravity: float = 0.0, drag: float = 0.98):
        sp = arcade.Sprite(self.circle_tex, scale=max(0.06, radius / 14.0))
        sp.center_x = x
        sp.center_y = y
        sp.color = color[:3]
        sp.alpha = color[3] if len(color) > 3 else 255
        self.particle_sprites.append(sp)
        self.particle_data.append([vx, vy, gravity, drag, life, life])

    def update(self):
        # Update batched particles in reverse for O(1) swap-pop removal
        i = len(self.particle_data) - 1
        while i >= 0:
            data = self.particle_data[i]
            sp = self.particle_sprites[i]
            sp.center_x += data[0]
            sp.center_y += data[1]
            data[1] -= data[2]
            data[0] *= data[3]
            data[4] -= 1
            if data[4] <= 0:
                sp.remove_from_sprite_lists()
                self.particle_data.pop(i)
            else:
                sp.alpha = int(255 * (data[4] / data[5]))
            i -= 1

        self.shockwaves = [s for s in self.shockwaves if s.update()]
        self.callouts = [c for c in self.callouts if c.update()]

    def draw(self):
        for s in self.shockwaves:
            alpha = int(255 * (s.life / s.max_life))
            arcade.draw_circle_outline(s.x, s.y, s.radius, (*s.color[:3], alpha), 3)

        self.particle_sprites.draw()

        for c in self.callouts:
            c.label.draw()

    def emit_hit(self, x: float, y: float, direction: int, is_meteor: bool = False, is_heavy: bool = False):
        self.shockwaves.append(_Shockwave(x, y, 80 if is_heavy else (68 if is_meteor else 52), (255, 220, 100)))
        if is_meteor:
            self.callouts.append(_FloatingCallout(x, y + 32, "METEOR!", (255, 70, 70)))
        elif is_heavy:
            self.callouts.append(_FloatingCallout(x, y + 34, "HEAVY SMASH!", (110, 215, 255)))
        else:
            self.callouts.append(_FloatingCallout(x, y + 26, "SMASH!", (255, 220, 80)))

        for _ in range(22 if is_heavy else 16):
            angle = random.uniform(-1.3, 1.3)
            speed = random.uniform(5.5, 13.0)
            vx = math.cos(angle) * speed * direction + random.uniform(-1.2, 1.2)
            vy = math.sin(angle) * speed + random.uniform(-1.0, 4.0)
            self._spawn(
                x, y, vx, vy,
                random.uniform(3.5, 8.5),
                random.choice(COLOR_HIT_SPARKS),
                life=random.randint(15, 28),
                gravity=0.34,
            )

    def emit_land(self, x: float, y: float):
        for _ in range(10):
            self._spawn(
                x + random.uniform(-22, 22), y,
                random.uniform(-4.5, 4.5), random.uniform(0.6, 3.2),
                random.uniform(2.5, 5.0),
                (230, 235, 250, 210),
                life=random.randint(10, 20),
                gravity=0.14,
            )

    def emit_jump(self, x: float, y: float):
        for _ in range(8):
            self._spawn(
                x + random.uniform(-14, 14), y - 6,
                random.uniform(-2.8, 2.8), random.uniform(-1.2, 1.8),
                random.uniform(2.2, 4.5),
                (200, 225, 255, 220),
                life=random.randint(8, 16),
                gravity=0.08,
            )

    def emit_sparkle(self, x: float, y: float, count: int = 12, color: tuple = (255, 230, 130, 255)):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.5, 5.0)
            self._spawn(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed + 1.0,
                random.uniform(2.0, 4.0),
                color,
                life=random.randint(12, 24),
                gravity=0.05,
            )

    def emit_shield_break(self, x: float, y: float):
        self.shockwaves.append(_Shockwave(x, y, 95, (110, 190, 255)))
        self.callouts.append(_FloatingCallout(x, y + 36, "SHIELD BREAK!", (110, 200, 255)))
        self.emit_sparkle(x, y, count=24, color=(130, 205, 255, 255))

    def emit_ko(self, x: float, y: float):
        clamped_x = max(80.0, min(1840.0, x))
        clamped_y = max(80.0, min(1000.0, y))
        self.shockwaves.append(_Shockwave(clamped_x, clamped_y, 160, (255, 100, 100)))
        self.callouts.append(_FloatingCallout(clamped_x, clamped_y + 40, "KO!", (255, 60, 60)))
        for _ in range(36):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(6.0, 16.0)
            self._spawn(
                clamped_x, clamped_y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(4.5, 10.5),
                random.choice(COLOR_KO_SPARKS),
                life=random.randint(24, 44),
                gravity=0.20,
            )