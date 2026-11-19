"""GPU-batched SpriteList particles, Blast-Zone KO light beams, shockwave rings, and cached floating callouts."""

import math
import random
import arcade

from assets import get_soft_circle_texture
from config import COLOR_HIT_SPARKS, COLOR_KO_SPARKS, WINDOW_HEIGHT, WINDOW_WIDTH


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


class _BlastBeam:
    """Smash-style directional light pillar streaking inward from the blast-zone KO entry point."""

    __slots__ = ("origin_x", "origin_y", "dx", "dy", "px", "py", "accent", "life", "max_life", "length")

    def __init__(self, x: float, y: float, vx: float, vy: float, accent: tuple):
        # Anchor beam origin onto the visible arena edge closest to where the fighter exited
        ox = max(-40.0, min(WINDOW_WIDTH + 40.0, x))
        oy = max(-40.0, min(WINDOW_HEIGHT + 40.0, y))

        if y < 0.0 and abs(vy) >= abs(vx):
            oy = -20.0
            in_x, in_y = -vx * 0.25, 1.0
        elif y > WINDOW_HEIGHT and abs(vy) >= abs(vx):
            oy = WINDOW_HEIGHT + 20.0
            in_x, in_y = -vx * 0.25, -1.0
        elif x < 0.0:
            ox = -20.0
            in_x, in_y = 1.0, -vy * 0.25
        elif x > WINDOW_WIDTH:
            ox = WINDOW_WIDTH + 20.0
            in_x, in_y = -1.0, -vy * 0.25
        else:
            in_x = (WINDOW_WIDTH * 0.5) - ox
            in_y = (WINDOW_HEIGHT * 0.5) - oy

        mag = max(1e-5, math.hypot(in_x, in_y))
        self.origin_x = ox
        self.origin_y = oy
        self.dx = in_x / mag
        self.dy = in_y / mag
        self.px = -self.dy
        self.py = self.dx
        self.accent = accent[:3]
        self.life = 46
        self.max_life = 46
        self.length = 980.0

    def update(self) -> bool:
        self.life -= 1
        return self.life > 0

    def draw(self):
        t = self.life / self.max_life
        # Beam shoots inward quickly, then tapers out cleanly
        reach_scale = min(1.0, (1.0 - t) * 6.5) if t > 0.84 else 1.0
        cur_len = self.length * reach_scale
        width_mult = math.sin(t * math.pi * 0.5) ** 0.65

        end_x = self.origin_x + self.dx * cur_len
        end_y = self.origin_y + self.dy * cur_len

        # 1. Wide outer colored cone
        w_outer = 155.0 * width_mult
        tip_outer = 18.0 * width_mult
        outer_poly = (
            (self.origin_x + self.px * w_outer, self.origin_y + self.py * w_outer),
            (self.origin_x - self.px * w_outer, self.origin_y - self.py * w_outer),
            (end_x - self.px * tip_outer, end_y - self.py * tip_outer),
            (end_x + self.px * tip_outer, end_y + self.py * tip_outer),
        )
        arcade.draw_polygon_filled(outer_poly, (*self.accent, int(115 * t)))

        # 2. Bright golden-white mid beam
        w_mid = 82.0 * width_mult
        tip_mid = 8.0 * width_mult
        mid_poly = (
            (self.origin_x + self.px * w_mid, self.origin_y + self.py * w_mid),
            (self.origin_x - self.px * w_mid, self.origin_y - self.py * w_mid),
            (end_x - self.px * tip_mid, end_y - self.py * tip_mid),
            (end_x + self.px * tip_mid, end_y + self.py * tip_mid),
        )
        arcade.draw_polygon_filled(mid_poly, (255, 235, 175, int(185 * t)))

        # 3. Blinding white-hot core pillar
        w_core = 36.0 * width_mult
        core_poly = (
            (self.origin_x + self.px * w_core, self.origin_y + self.py * w_core),
            (self.origin_x - self.px * w_core, self.origin_y - self.py * w_core),
            (end_x, end_y),
        )
        arcade.draw_polygon_filled(core_poly, (255, 255, 255, int(245 * t)))

        # 4. Origin flash flare
        arcade.draw_circle_filled(self.origin_x, self.origin_y, 130.0 * width_mult, (*self.accent, int(135 * t)))
        arcade.draw_circle_filled(self.origin_x, self.origin_y, 68.0 * width_mult, (255, 255, 255, int(230 * t)))


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
        self.blast_beams: list[_BlastBeam] = []
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
        self.blast_beams = [b for b in self.blast_beams if b.update()]
        self.callouts = [c for c in self.callouts if c.update()]

    def draw(self):
        for b in self.blast_beams:
            b.draw()

        for s in self.shockwaves:
            alpha = int(255 * (s.life / s.max_life))
            arcade.draw_circle_outline(s.x, s.y, s.radius, (*s.color[:3], alpha), 3)

        self.particle_sprites.draw()

        for c in self.callouts:
            c.label.draw()

    def emit_hit(self, x: float, y: float, direction: int, is_meteor: bool = False, is_heavy: bool = False, label_override: str | None = None):
        self.shockwaves.append(_Shockwave(x, y, 86 if is_heavy else (72 if is_meteor else 54), (255, 220, 100)))
        if label_override:
            self.callouts.append(_FloatingCallout(x, y + 32, label_override, (255, 195, 75)))
        elif is_meteor:
            self.callouts.append(_FloatingCallout(x, y + 32, "METEOR!", (255, 70, 70)))
        elif is_heavy:
            self.callouts.append(_FloatingCallout(x, y + 34, "HEAVY SMASH!", (110, 215, 255)))
        else:
            self.callouts.append(_FloatingCallout(x, y + 26, "SMASH!", (255, 220, 80)))

        for _ in range(24 if is_heavy else 16):
            angle = random.uniform(-1.3, 1.3)
            speed = random.uniform(5.5, 13.5)
            vx = math.cos(angle) * speed * direction + random.uniform(-1.2, 1.2)
            vy = math.sin(angle) * speed + random.uniform(-1.0, 4.0)
            self._spawn(
                x, y, vx, vy,
                random.uniform(3.5, 8.5),
                random.choice(COLOR_HIT_SPARKS),
                life=random.randint(15, 28),
                gravity=0.34,
            )

    def emit_launch_trail(self, x: float, y: float, accent: tuple):
        """Smash-style smoke & spark plume trailing behind high-speed launched fighters."""
        self._spawn(
            x + random.uniform(-8, 8),
            y + random.uniform(-8, 8),
            random.uniform(-1.4, 1.4),
            random.uniform(-1.0, 1.6),
            random.uniform(7.5, 13.5),
            (235, 240, 250, 145),
            life=random.randint(14, 22),
            gravity=-0.04,
            drag=0.94,
        )
        if random.random() < 0.65:
            self._spawn(
                x + random.uniform(-6, 6),
                y + random.uniform(-6, 6),
                random.uniform(-2.2, 2.2),
                random.uniform(-2.2, 2.2),
                random.uniform(2.8, 5.2),
                (*accent[:3], 235),
                life=random.randint(10, 18),
                gravity=0.05,
                drag=0.95,
            )

    def emit_ledge_grab(self, x: float, y: float, accent: tuple):
        self.shockwaves.append(_Shockwave(x, y, 42, (255, 225, 110)))
        self.emit_sparkle(x, y, count=12, color=(255, 230, 120, 255))

    def emit_tech(self, x: float, y: float, accent: tuple):
        self.shockwaves.append(_Shockwave(x, y + 18, 58, accent[:3]))
        self.callouts.append(_FloatingCallout(x, y + 42, "TECH!", accent[:3]))
        self.emit_sparkle(x, y + 12, count=16, color=(*accent[:3], 255))

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

    def emit_ko(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0, accent: tuple = (255, 210, 90)):
        beam = _BlastBeam(x, y, vx, vy, accent)
        self.blast_beams.append(beam)

        clamped_x = max(60.0, min(WINDOW_WIDTH - 60.0, x))
        clamped_y = max(60.0, min(WINDOW_HEIGHT - 60.0, y))
        self.shockwaves.append(_Shockwave(clamped_x, clamped_y, 185, accent))
        self.callouts.append(_FloatingCallout(clamped_x, clamped_y + 40, "KO!", (255, 60, 60)))

        for _ in range(46):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(6.0, 18.0)
            self._spawn(
                clamped_x, clamped_y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(4.5, 11.0),
                random.choice(COLOR_KO_SPARKS),
                life=random.randint(24, 46),
                gravity=0.16,
            )
        # Inward spark stream along the KO beam axis
        for _ in range(24):
            spd = random.uniform(10.0, 26.0)
            spread = random.uniform(-3.2, 3.2)
            self._spawn(
                beam.origin_x + beam.px * random.uniform(-24, 24),
                beam.origin_y + beam.py * random.uniform(-24, 24),
                beam.dx * spd + beam.px * spread,
                beam.dy * spd + beam.py * spread,
                random.uniform(4.0, 9.0),
                (*accent[:3], 255),
                life=random.randint(18, 34),
                gravity=0.0,
                drag=0.96,
            )