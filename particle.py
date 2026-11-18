"""Rich particle system supporting shockwaves, sparks, smoke, and floating text popups."""

import math
import random

import arcade

from arcade_compat import draw_text
from config import COLOR_HIT_SPARKS, COLOR_KO_SPARKS


class Particle:
    def __init__(self, x, y, vx, vy, size, color, life, gravity=0.0, drag=0.98):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.size = size
        self.color = color
        self.life = life
        self.max_life = life
        self.gravity = gravity
        self.drag = drag

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy -= self.gravity
        self.vx *= self.drag
        self.life -= 1
        return self.life > 0

    def current_color(self):
        a = int(255 * (self.life / self.max_life))
        c = self.color
        return (c[0], c[1], c[2], max(0, min(255, a)))


class Shockwave:
    def __init__(self, x, y, max_radius, color):
        self.x, self.y = x, y
        self.radius = 5.0
        self.max_radius = max_radius
        self.color = color
        self.life = 15
        self.max_life = 15

    def update(self):
        self.radius += (self.max_radius - self.radius) * 0.25
        self.life -= 1
        return self.life > 0

    def draw(self):
        alpha = int(255 * (self.life / self.max_life))
        c = self.color
        arcade.draw_circle_outline(self.x, self.y, self.radius, (c[0], c[1], c[2], alpha), 3)


class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 40
        self.max_life = 40

    def update(self):
        self.y += 1.5
        self.life -= 1
        return self.life > 0

    def draw(self):
        alpha = int(255 * (self.life / self.max_life))
        c = self.color
        draw_text(self.text, self.x, self.y, (c[0], c[1], c[2], alpha), 22, anchor_x="center", bold=True)


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.shockwaves = []
        self.floating_texts = []

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        self.shockwaves = [s for s in self.shockwaves if s.update()]
        self.floating_texts = [f for f in self.floating_texts if f.update()]

    def draw(self):
        for s in self.shockwaves:
            s.draw()
        for p in self.particles:
            arcade.draw_circle_filled(p.x, p.y, p.size, p.current_color())
        for f in self.floating_texts:
            f.draw()

    def emit_hit(self, x, y, direction, is_meteor=False, count=22):
        self.shockwaves.append(Shockwave(x, y, 70 if is_meteor else 50, (255, 220, 100, 255)))
        if is_meteor:
            self.floating_texts.append(FloatingText(x, y + 30, "METEOR!", (255, 60, 60, 255)))
        else:
            self.floating_texts.append(FloatingText(x, y + 25, "SMASH!", (255, 220, 80, 255)))

        for _ in range(count):
            angle = random.uniform(-1.5, 1.5)
            speed = random.uniform(5, 12)
            vx = math.cos(angle) * speed * direction + random.uniform(-1, 1)
            vy = math.sin(angle) * speed + random.uniform(-1, 4)
            self.particles.append(Particle(
                x, y, vx, vy,
                random.uniform(3, 9),
                random.choice(COLOR_HIT_SPARKS),
                life=random.randint(15, 30),
                gravity=0.35,
            ))

    def emit_land(self, x, y, count=14):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-22, 22), y,
                random.uniform(-5, 5), random.uniform(0.5, 3.5),
                random.uniform(2, 5),
                (230, 230, 245, 220),
                life=random.randint(10, 22),
                gravity=0.15,
            ))

    def emit_jump(self, x, y, count=10):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-12, 12), y - 10,
                random.uniform(-3, 3), random.uniform(-1.5, 2),
                random.uniform(2, 4.5),
                (200, 225, 255, 230),
                life=random.randint(8, 18),
                gravity=0.10,
            ))

    def emit_sparkle(self, x, y, count=12, color=(255, 230, 130, 255)):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.5, 5)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed + 1,
                random.uniform(1.5, 3.5),
                color,
                life=random.randint(12, 24),
                gravity=0.05,
            ))

    def emit_ko(self, x, y, count=40):
        self.shockwaves.append(Shockwave(x, y, 150, (255, 100, 100, 255)))
        self.floating_texts.append(FloatingText(x, y + 40, "KO!", (255, 50, 50, 255)))
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(6, 16)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(4, 11),
                random.choice(COLOR_KO_SPARKS),
                life=random.randint(25, 45),
                gravity=0.22,
            ))