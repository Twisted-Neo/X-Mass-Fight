"""Generic particle + preset emitters for combat feedback."""

import math
import random

import arcade

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
        return (c[0], c[1], c[2], a)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def update(self):
        self.particles = [p for p in self.particles if p.update()]

    def draw(self):
        for p in self.particles:
            arcade.draw_circle_filled(p.x, p.y, p.size, p.current_color())

    # ---------------- Preset emitters ----------------

    def emit_hit(self, x, y, direction, count=18):
        for _ in range(count):
            angle = random.uniform(-1.2, 1.2)
            speed = random.uniform(4, 9)
            vx = math.cos(angle) * speed * direction + random.uniform(-1, 1)
            vy = math.sin(angle) * speed + random.uniform(0, 3)
            self.particles.append(Particle(
                x, y, vx, vy,
                random.uniform(3, 8),
                random.choice(COLOR_HIT_SPARKS),
                life=random.randint(14, 26),
                gravity=0.3,
            ))

    def emit_land(self, x, y, count=12):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-18, 18), y,
                random.uniform(-4, 4), random.uniform(0.5, 3),
                random.uniform(2, 5),
                (220, 220, 235, 255),
                life=random.randint(10, 20),
                gravity=0.15,
            ))

    def emit_jump(self, x, y, count=8):
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-10, 10), y - 10,
                random.uniform(-3, 3), random.uniform(-1, 2),
                random.uniform(2, 4),
                (200, 220, 255, 220),
                life=random.randint(8, 16),
                gravity=0.10,
            ))

    def emit_sparkle(self, x, y, count=10, color=(255, 220, 120, 255)):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1, 4)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed + 1,
                random.uniform(1, 3),
                color,
                life=random.randint(10, 20),
                gravity=0.05,
            ))

    def emit_ko(self, x, y, count=30):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(5, 14)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                random.uniform(4, 10),
                random.choice(COLOR_KO_SPARKS),
                life=random.randint(20, 40),
                gravity=0.2,
            ))