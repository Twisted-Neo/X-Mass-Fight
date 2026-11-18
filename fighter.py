"""The Fighter sprite: physics, attack state, animation state machine."""

import arcade

from asset_loader import load_all_animations
from config import (
    AIR_ACCELERATION, AIR_FRICTION,
    ATTACK_COOLDOWN, ATTACK_DURATION, ATTACK_HITBOX_H, ATTACK_HITBOX_W,
    ATTACK_REACH,
    COYOTE_TIME_FRAMES, DOUBLE_JUMP_SPEED,
    FAST_FALL_SPEED, GRAVITY,
    GROUND_ACCELERATION, GROUND_FRICTION,
    JUMP_BUFFER_FRAMES, JUMP_SPEED,
    MAX_FALL_SPEED, MAX_RUN_SPEED,
    ANIM_SPEED, PHYSICS_STEP,
)


class Fighter(arcade.Sprite):
    BODY_W = 64
    BODY_H = 128

    def __init__(self, x, y, player_name, tint_color, facing=1):
        super().__init__()

        self.player_name = player_name
        self.center_x = x
        self.center_y = y
        self.base_scale = 0.5
        self.scale = self.base_scale
        self.base_color = tint_color
        self.color = tint_color
        self.facing_right = facing > 0

        # Combat
        self.stocks = 3
        self.damage = 0.0
        self.hitstun_timer = 0
        self.invincible_timer = 0
        self.hit_flash_timer = 0

        # Input
        self.move_left = False
        self.move_right = False
        self.crouching = False
        self.jump_pressed = False
        self.attack_pressed = False
        self.jump_buffer_timer = 0
        self.coyote_timer = 0

        # Physics state
        self.is_grounded = False
        self.jumps_left = 2
        self.max_jumps = 2
        self.ignore_platform_timer = 0

        # One-frame flags for the view (particles)
        self.just_jumped = False
        self.just_double_jumped = False
        self.just_landed = False

        # Attack
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_hitbox = None
        self.attack_has_hit = False

        # Load right-facing and create left-facing (flipped) animation sets
        raw_animations = load_all_animations()
        self.animations_right = raw_animations
        self.animations_left = {
            name: tuple(tex.flip_left_right() for tex in frames)
            for name, frames in raw_animations.items()
        }
        self._last_anim_set = None

        self.state = "IDLE"
        self.cur_texture_index = 0
        self.animation_timer = 0.0
        self.was_airborne = False
        self.texture = self.animations_right["IDLE"][0]
        self._apply_fixed_hit_box()

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------

    def _apply_fixed_hit_box(self):
        hw, hh = self.BODY_W / 2, self.BODY_H / 2
        points = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]

        self.texture = arcade.Texture(
            self.texture.image,
            hit_box_points=points
        )

    @property
    def width(self):
        return self.BODY_W

    @property
    def height(self):
        return self.BODY_H

    @property
    def left(self):
        return self.center_x - self.BODY_W / 2

    @property
    def right(self):
        return self.center_x + self.BODY_W / 2

    @property
    def bottom(self):
        return self.center_y - self.BODY_H / 2

    @property
    def top(self):
        return self.center_y + self.BODY_H / 2

    def update_physics(self, platforms):
        previous_bottom = self.bottom
        self.just_jumped = False
        self.just_double_jumped = False
        self.just_landed = False

        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.ignore_platform_timer > 0:
            self.ignore_platform_timer -= 1
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1
        if self.coyote_timer > 0:
            self.coyote_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        in_hitstun = self.hitstun_timer > 0
        if in_hitstun:
            self.hitstun_timer -= 1
            self.change_x *= 0.92
        else:
            accel = GROUND_ACCELERATION if self.is_grounded else AIR_ACCELERATION
            fric = GROUND_FRICTION if self.is_grounded else AIR_FRICTION
            if self.move_left and not self.move_right:
                self.change_x -= accel
                self.facing_right = False
            elif self.move_right and not self.move_left:
                self.change_x += accel
                self.facing_right = True
            else:
                self.change_x *= fric
                if abs(self.change_x) < 0.15:
                    self.change_x = 0.0
            self.change_x = max(-MAX_RUN_SPEED, min(MAX_RUN_SPEED, self.change_x))

        # Jump input with buffer + coyote time
        if self.jump_pressed:
            self.jump_buffer_timer = JUMP_BUFFER_FRAMES
            self.jump_pressed = False

        if self.jump_buffer_timer > 0 and not in_hitstun:
            standing_on_soft = any(
                p.pass_through
                and self.right > p.left and self.left < p.right
                and abs(self.bottom - p.top) <= 8
                for p in platforms
            )
            if self.crouching and self.is_grounded and standing_on_soft:
                # Drop through
                self.ignore_platform_timer = 12
                self.is_grounded = False
                self.change_y = -2.0
                self.jump_buffer_timer = 0
            elif self.is_grounded or self.coyote_timer > 0:
                self.change_y = JUMP_SPEED
                self.is_grounded = False
                self.jumps_left = self.max_jumps - 1
                self.coyote_timer = 0
                self.jump_buffer_timer = 0
                self.just_jumped = True
            elif self.jumps_left > 0:
                self.change_y = DOUBLE_JUMP_SPEED
                self.jumps_left -= 1
                self.jump_buffer_timer = 0
                self.just_double_jumped = True

        if not self.is_grounded:
            max_fall = FAST_FALL_SPEED if self.crouching else MAX_FALL_SPEED
            self.change_y = max(self.change_y - GRAVITY, -max_fall)

        self.center_x += self.change_x
        self.center_y += self.change_y

        # Landing detection
        was_grounded = self.is_grounded
        self.is_grounded = False
        for platform in platforms:
            overlap = self.right > platform.left and self.left < platform.right
            crossed_top = (
                self.change_y <= 0
                and previous_bottom >= platform.top - 5
                and self.bottom <= platform.top
            )
            if not overlap or not crossed_top:
                continue
            if platform.pass_through and self.ignore_platform_timer > 0:
                continue
            self.center_y = platform.top + self.height / 2
            self.change_y = 0
            self.is_grounded = True
            self.jumps_left = self.max_jumps
            self.coyote_timer = COYOTE_TIME_FRAMES
            if not was_grounded:
                self.just_landed = True
            break

        # Attack input
        if self.attack_pressed:
            if (not self.is_attacking
                    and not in_hitstun
                    and self.attack_cooldown == 0):
                self.is_attacking = True
                self.attack_timer = ATTACK_DURATION
                self.attack_has_hit = False
            self.attack_pressed = False

        self.attack_hitbox = None
        if self.is_attacking:
            if not self.attack_has_hit:
                hx = self.center_x + (ATTACK_REACH if self.facing_right
                                       else -ATTACK_REACH)
                hy = self.center_y
                self.attack_hitbox = (
                    hx - ATTACK_HITBOX_W / 2,
                    hy - ATTACK_HITBOX_H / 2,
                    ATTACK_HITBOX_W,
                    ATTACK_HITBOX_H,
                )
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.attack_cooldown = ATTACK_COOLDOWN

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def update_animation(self, delta_time):
        anim_set = (
            self.animations_right if self.facing_right else self.animations_left
        )

        # --- State selection ---
        if self.hitstun_timer > 0:
            new_state = "HIT"
        elif not self.is_grounded:
            new_state = "JUMPING" if self.change_y > 0 else "FALLING"
        elif self.crouching:
            new_state = "SIT"
        elif abs(self.change_x) > 0.8:
            new_state = "WALKING"
        elif (self.state == "LANDING"
              and self.cur_texture_index
                  < len(anim_set["LANDING"]) - 1):
            new_state = "LANDING"
        elif self.just_landed and "LANDING" in anim_set:
            new_state = "LANDING"
        else:
            new_state = "IDLE"

        self.was_airborne = not self.is_grounded

        # --- State transition or direction change ---
        if new_state != self.state or anim_set is not self._last_anim_set:
            self.state = new_state
            self.cur_texture_index = 0
            self.animation_timer = 0.0
            frames = anim_set.get(self.state) or anim_set["IDLE"]
            self.texture = frames[0]
            self._last_anim_set = anim_set
        else:
            frames = anim_set.get(self.state) or anim_set["IDLE"]

        # --- Frame advancement ---
        speed = ANIM_SPEED.get(self.state, 0.08)
        steps_per_frame = max(1, round(speed / PHYSICS_STEP))

        self.animation_timer += 1
        while self.animation_timer >= steps_per_frame:
            self.animation_timer -= steps_per_frame

            if self.state == "LANDING":
                if self.cur_texture_index < len(frames) - 1:
                    self.cur_texture_index += 1
                else:
                    self.state = "IDLE"
                    self.cur_texture_index = 0
                    frames = anim_set["IDLE"]
            else:
                self.cur_texture_index = (
                    self.cur_texture_index + 1
                ) % len(frames)

            self.texture = frames[self.cur_texture_index]

    # ------------------------------------------------------------------
    # Respawn
    # ------------------------------------------------------------------

    def reset_after_ko(self, x, y):
        self.center_x = x
        self.center_y = y
        self.change_x = 0
        self.change_y = 0
        self.damage = 0.0
        self.hitstun_timer = 0
        self.invincible_timer = 90
        self.hit_flash_timer = 0
        self.color = self.base_color
        self.is_grounded = False
        self.jumps_left = self.max_jumps
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.is_attacking = False
        self.attack_hitbox = None
        self.attack_has_hit = False
        self.attack_cooldown = 0
        self.state = "IDLE"
        self.cur_texture_index = 0
        self.animation_timer = 0.0