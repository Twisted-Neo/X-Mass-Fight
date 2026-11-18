"""The Fighter sprite: physics, attacks, shields, charged heavy attacks, and animations."""

import arcade

from asset_loader import load_all_animations, load_attack_animations
from config import (
    AIR_ACCELERATION, AIR_FRICTION,
    ATTACK_COOLDOWN, ATTACK_DURATION, ATTACK_HITBOX_H, ATTACK_HITBOX_W,
    ATTACK_REACH, BASE_DAMAGE,
    COYOTE_TIME_FRAMES, DOUBLE_JUMP_SPEED,
    FAST_FALL_SPEED, GRAVITY,
    GROUND_ACCELERATION, GROUND_FRICTION,
    JUMP_BUFFER_FRAMES, JUMP_SPEED,
    MAX_FALL_SPEED, MAX_RUN_SPEED,
    SHIELD_MAX_HEALTH, SHIELD_DRAIN, SHIELD_REGEN,
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

        # Combat & Shield
        self.stocks = 3
        self.damage = 0.0
        self.hitstun_timer = 0
        self.invincible_timer = 0
        self.hit_flash_timer = 0
        self.shield_health = SHIELD_MAX_HEALTH
        self.shield_stun_timer = 0
        self.is_shielding = False

        # Charging heavy attack
        self.is_charging = False
        self.charge_timer = 0
        self.max_charge_frames = 120  # 2 seconds max charge

        # Input flags
        self.move_left = False
        self.move_right = False
        self.crouching = False
        self.jump_pressed = False
        self.jump_held = False
        self.attack_pressed = False
        self.charge_pressed = False
        self.charge_held = False
        self.shield_pressed = False
        self.jump_buffer_timer = 0
        self.coyote_timer = 0

        # Physics state
        self.is_grounded = False
        self.jumps_left = 2
        self.max_jumps = 2
        self.ignore_platform_timer = 0

        # Event flags for particles
        self.just_jumped = False
        self.just_double_jumped = False
        self.just_landed = False

        # Attacks & Combos
        self.is_attacking = False
        self.attack_state = "ATTACK_SIDE"
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_hitbox = None
        self.attack_has_hit = False
        self.attack_texture_index = 0
        self.charge_power_multiplier = 1.0

        # Animations
        raw_animations = load_all_animations()
        self.animations_right = raw_animations
        self.animations_left = {
            name: tuple(tex.flip_left_right() for tex in frames)
            for name, frames in raw_animations.items()
        }
        self._last_anim_set = None

        raw_attack_animations = load_attack_animations()
        self.attack_animations_right = raw_attack_animations
        self.attack_animations_left = {
            name: tuple(tex.flip_left_right() for tex in frames)
            for name, frames in raw_attack_animations.items()
        }

        self.state = "IDLE"
        self.cur_texture_index = 0
        self.animation_timer = 0.0
        self.was_airborne = False
        self.texture = self.animations_right["IDLE"][0]
        self._apply_fixed_hit_box()

    def _apply_fixed_hit_box(self):
        hw, hh = self.BODY_W / 2, self.BODY_H / 2
        points = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        self.texture = arcade.Texture(self.texture.image, hit_box_points=points)

    @property
    def width(self): return self.BODY_W
    @property
    def height(self): return self.BODY_H
    @property
    def left(self): return self.center_x - self.BODY_W / 2
    @property
    def right(self): return self.center_x + self.BODY_W / 2
    @property
    def bottom(self): return self.center_y - self.BODY_H / 2
    @property
    def top(self): return self.center_y + self.BODY_H / 2

    def update_physics(self, platforms):
        previous_bottom = self.bottom
        self.just_jumped = False
        self.just_double_jumped = False
        self.just_landed = False

        if self.invincible_timer > 0: self.invincible_timer -= 1
        if self.ignore_platform_timer > 0: self.ignore_platform_timer -= 1
        if self.jump_buffer_timer > 0: self.jump_buffer_timer -= 1
        if self.coyote_timer > 0: self.coyote_timer -= 1
        if self.attack_cooldown > 0: self.attack_cooldown -= 1
        if self.shield_stun_timer > 0: self.shield_stun_timer -= 1

        # Shield regeneration
        if not self.is_shielding and self.shield_stun_timer == 0:
            self.shield_health = min(SHIELD_MAX_HEALTH, self.shield_health + SHIELD_REGEN)

        in_hitstun = self.hitstun_timer > 0
        if in_hitstun:
            self.hitstun_timer -= 1
            self.change_x *= 0.92
            self.is_shielding = False
            self.is_charging = False
        elif self.shield_stun_timer > 0:
            self.change_x *= 0.85
            self.is_shielding = False
            self.is_charging = False
        elif self.is_shielding:
            self.change_x *= 0.5
            self.shield_health = max(0.0, self.shield_health - SHIELD_DRAIN)
            if self.shield_health <= 0:
                self.shield_stun_timer = 100
                self.is_shielding = False
        elif self.is_charging:
            self.change_x = 0
            self.charge_timer += 1
            if not self.charge_held or self.charge_timer >= self.max_release_frames():
                # Release charge attack!
                self._release_heavy_attack()
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

        if self.jump_pressed:
            self.jump_buffer_timer = JUMP_BUFFER_FRAMES
            self.jump_pressed = False

        if self.jump_buffer_timer > 0 and not in_hitstun and self.shield_stun_timer == 0 and not self.is_charging:
            standing_on_soft = any(
                p.pass_through and self.right > p.left and self.left < p.right and abs(self.bottom - p.top) <= 8
                for p in platforms
            )
            if self.crouching and self.is_grounded and standing_on_soft:
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

        was_grounded = self.is_grounded
        self.is_grounded = False
        for platform in platforms:
            overlap = self.right > platform.left and self.left < platform.right
            crossed_top = (
                self.change_y <= 0
                and previous_bottom >= platform.top - 6
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

        # Heavy Charge Input initiation
        if self.charge_pressed and not self.is_shielding and not in_hitstun and self.shield_stun_timer == 0 and self.attack_cooldown == 0 and not self.is_attacking:
            self.is_charging = True
            self.charge_timer = 0
            self.charge_pressed = False

        # Regular Attacks Input
        if self.attack_pressed and not self.is_shielding and not self.is_charging:
            if not in_hitstun and self.shield_stun_timer == 0 and self.attack_cooldown == 0 and not self.is_attacking:
                if not self.is_grounded:
                    if self.crouching:
                        self.attack_state = "ATTACK_DOWN"
                    elif self.jump_held or self.change_y > 0:
                        self.attack_state = "ATTACK_UP"
                    else:
                        self.attack_state = "ATTACK_SIDE"
                else:
                    if self.crouching:
                        self.attack_state = "ATTACK_DOWN"
                    elif self.jump_held or self.change_y > 0:
                        self.attack_state = "ATTACK_UP"
                    else:
                        self.attack_state = "ATTACK_SIDE"

                self.is_attacking = True
                self.attack_timer = ATTACK_DURATION
                self.attack_has_hit = False
                self.attack_texture_index = 0
            self.attack_pressed = False

        self.attack_hitbox = None
        if self.is_attacking:
            anim_set = self.attack_animations_right if self.facing_right else self.attack_animations_left
            frames = anim_set.get(self.attack_state, anim_set["ATTACK_SIDE"])
            elapsed = ATTACK_DURATION - self.attack_timer
            frame_duration = max(1, ATTACK_DURATION // len(frames))
            self.attack_texture_index = min(elapsed // frame_duration, len(frames) - 1)

            if not self.attack_has_hit:
                if self.attack_state == "ATTACK_UP":
                    hx, hy = self.center_x, self.center_y + self.BODY_H / 2 + 10
                    self.attack_hitbox = (hx - ATTACK_HITBOX_W / 2, hy, ATTACK_HITBOX_W, ATTACK_HITBOX_H)
                elif self.attack_state == "ATTACK_DOWN":
                    hx, hy = self.center_x, self.center_y - self.BODY_H / 2 - ATTACK_HITBOX_H - 10
                    self.attack_hitbox = (hx - ATTACK_HITBOX_W / 2, hy, ATTACK_HITBOX_W, ATTACK_HITBOX_H)
                else:
                    hx = self.center_x + (ATTACK_REACH if self.facing_right else -ATTACK_REACH)
                    hy = self.center_y
                    self.attack_hitbox = (hx - ATTACK_HITBOX_W / 2, hy - ATTACK_HITBOX_H / 2, ATTACK_HITBOX_W, ATTACK_HITBOX_H)

            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.attack_cooldown = ATTACK_COOLDOWN

    def max_release_frames(self):
        return self.max_charge_frames

    def _release_heavy_attack(self):
        self.is_charging = False
        # Calculate power scaling based on charge time (1.0 to 2.5x)
        ratio = min(1.0, self.charge_timer / self.max_charge_frames)
        self.charge_power_multiplier = 1.0 + ratio * 1.5

        self.attack_state = "ATTACK_HEAVY"
        self.is_attacking = True
        self.attack_timer = ATTACK_DURATION + 6  # Slightly longer duration for heavy
        self.attack_has_hit = False
        self.attack_texture_index = 0
        self.charge_timer = 0

    def get_current_attack_damage(self):
        base = BASE_DAMAGE
        if self.attack_state == "ATTACK_HEAVY":
            return base * 2.2 * self.charge_power_multiplier
        elif self.attack_state in ("ATTACK_UP", "ATTACK_DOWN"):
            return base * 1.4
        return base

    def update_animation(self, delta_time):
        anim_set = self.animations_right if self.facing_right else self.animations_left
        if self.hitstun_timer > 0: new_state = "HIT"
        elif not self.is_grounded: new_state = "JUMPING" if self.change_y > 0 else "FALLING"
        elif self.crouching: new_state = "SIT"
        elif abs(self.change_x) > 0.8: new_state = "WALKING"
        elif self.just_landed and "LANDING" in anim_set: new_state = "LANDING"
        else: new_state = "IDLE"

        if new_state != self.state or anim_set is not self._last_anim_set:
            self.state = new_state
            self.cur_texture_index = 0
            self.animation_timer = 0.0
            frames = anim_set.get(self.state) or anim_set["IDLE"]
            self.texture = frames[0]
            self._last_anim_set = anim_set
        else:
            frames = anim_set.get(self.state) or anim_set["IDLE"]

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
            else:
                self.cur_texture_index = (self.cur_texture_index + 1) % len(frames)
            self.texture = frames[self.cur_texture_index]

    def reset_after_ko(self, x, y):
        self.center_x, self.center_y = x, y
        self.change_x, self.change_y = 0, 0
        self.damage = 0.0
        self.hitstun_timer = 0
        self.invincible_timer = 90
        self.hit_flash_timer = 0
        self.shield_health = SHIELD_MAX_HEALTH
        self.color = self.base_color
        self.is_grounded = False
        self.jumps_left = self.max_jumps
        self.is_attacking = False
        self.is_charging = False
        self.attack_hitbox = None
        self.attack_has_hit = False
        self.state = "IDLE"