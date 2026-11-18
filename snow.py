"""Ambient snowflakes drifting across the background."""

import math
import random

import arcade

from config import COLOR_SNOW


class SnowParticle:
    def __init__(self, width, height):
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, height)
        self.speed = random.uniform(0.8, 2.5)
        self.size = random.uniform(1.5, 4.5)
        self.drift = random.uniform(-0.5, 0.5)
        self.alpha = random.randint(130, 255)
        self.wobble = random.uniform(0, math.tau)
        self.wobble_speed = random.uniform(0.02, 0.06)

    def update(self, width, height):
        self.y -= self.speed
        self.wobble += self.wobble_speed
        self.x += self.drift + math.sin(self.wobble) * 0.4
        if self.y < -10:
            self.y = height + 10
            self.x = random.uniform(0, width)
        if self.x < -10:
            self.x = width + 10
        elif self.x > width + 10:
            self.x = -10

    def draw(self):
        arcade.draw_circle_filled(
            self.x, self.y, self.size,
            (COLOR_SNOW[0], COLOR_SNOW[1], COLOR_SNOW[2], self.alpha),
        )