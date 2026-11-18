"""Fighter entity: platform-fighter physics, 2-hit side combo, charging, and damage-scaled launch."""

import arcade

from assets import get_fighter_animations, get_vfx_animations
from config import (
    AIR_ACCEL, AIR_FRICTION,
    ATTACK_ACTIVE_END, ATTACK_ACTIVE_START, ATTACK_COOLDOWN, ATTACK_DURATION,
    ATTACK_HITBOX_H, ATTACK_HITBOX_W, ATTACK_REACH,
    ATTACK_SIDE_1_DURATION, ATTACK_SIDE_2_DURATION,
    BASE_DAMAGE, BODY_ANIM_SPECS, COYOTE_TIME_FRAMES, DROP_THROUGH_FRAMES,
    DOUBLE_JUMP_SPEED, FAST_FALL_SPEED, GRAVITY, GROUND_ACCEL, GROUND_FRICTION,
    JUMP_BUFFER_FRAMES, JUMP_SPEED, LAUNCH_FRAME_DURATION,
    LAUNCH_LOCKOUT_BASE_FRAMES, LAUNCH_LOCKOUT_FRAMES_PER_DMG,
    LAUNCH_LOCKOUT_MAX_FRAMES, LAUNCH_LOCKOUT_MIN_FRAMES,
    MAX_CHARGE_FRAMES, MAX_FALL_SPEED, MAX_RUN_SPEED, RESPAWN_INVULN_FRAMES,
    SHIELD_DRAIN, SHIELD_MAX_HEALTH, SHIELD_REGEN, SHORT_HOP_MULTIPLIER,
    SIDE_COMBO_DAMAGE_MULT, SIDE_COMBO_HITBOX_MULT, SIDE_COMBO_WINDOW_FRAMES,
    STARTING_STOCKS, TARGET_FIGHTER_HEIGHT,
)


class Fighter(arcade.Sprite):
    def __init__(self, x: float, y: float, name: str, tint_color: tuple, facing: int = 1):
        self.anims = get_fighter_animations()
        self.vfx = get_vfx_animations()

        idle_tex = self.anims["RIGHT"]["IDLE"][0]
        super().__init__(idle_tex)

        self.scale = TARGET_FIGHTER_HEIGHT / max(1, idle_tex.height)
        self.center_x = x
        self.center_y = y
        self.player_name = name
        self.base_color = tint_color
        self.color = tint_color
        self.facing_right = facing >= 0

        # Input flags
        self.move_left = False
        self.move_right = False
        self.up_held = False
        self.crouching = False
        self.jump_pressed = False
        self.jump_held = False
        self.attack_pressed = False
        self.charge_pressed = False
        self.charge_held = False
        self.shield_held = False

        # Match & combat state
        self.stocks = STARTING_STOCKS
        self.damage = 0.0
        self.is_grounded = False
        self.jumps_remaining = 2
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.drop_through_timer = 0
        self.landing_timer = 0

        self.hitstun_timer = 0
        self.hit_flash_timer = 0
        self.invincible_timer = 0
        self.respawn_invuln_timer = 0

        # Hard-hit Launch state machine
        self.launch_active = False
        self.launch_stage = "ASCENT"   # "ASCENT" (0..3) -> "DESCENT" (4..11) -> "GROUNDED" (12..23)
        self.launch_lock_timer = 0
        self.launch_frame = 0
        self.launch_anim_timer = 0.0

        # Shield
        self.shield_health = SHIELD_MAX_HEALTH
        self.shield_stun_timer = 0
        self.is_shielding = False

        # Attacks, Side Combo & Heavy Charge
        self.is_attacking = False
        self.attack_state = "ATTACK_SIDE_1"
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_has_hit = False
        self.attack_hitbox = None
        self.side_combo_window = 0
        self.side_combo_buffered = False

        self.is_charging = False
        self.charge_timer = 0
        self.charge_power_multiplier = 1.0

        # Animation state
        self.anim_state = "IDLE"
        self.anim_timer = 0.0
        self.anim_index = 0

        # One-frame event flags for particles
        self.just_landed = False
        self.just_jumped = False
        self.just_double_jumped = False

    @property
    def body_width(self) -> float:
        return self.width * 0.72

    @property
    def body_height(self) -> float:
        return self.height * 0.92

    def _has_any_active_input(self) -> bool:
        return (
            self.move_left
            or self.move_right
            or self.up_held
            or self.crouching
            or self.jump_pressed
            or self.jump_held
            or self.attack_pressed
            or self.charge_pressed
            or self.charge_held
            or self.shield_held
        )

    def start_launch(self, damage_dealt: float):
        """Enters the 3-stage launch animation with control lockout scaled by hit damage.
        If already in the launched condition, keeps the current lockout timer running without resetting it.
        """
        self.is_shielding = False
        self.is_charging = False
        self.is_attacking = False
        self.attack_hitbox = None
        self.side_combo_window = 0
        self.side_combo_buffered = False

        if self.launch_active:
            self.launch_stage = "ASCENT"
            self.launch_frame = 0
            self.launch_anim_timer = 0.0
            return

        raw_frames = int(LAUNCH_LOCKOUT_BASE_FRAMES + damage_dealt * LAUNCH_LOCKOUT_FRAMES_PER_DMG)
        self.launch_lock_timer = max(LAUNCH_LOCKOUT_MIN_FRAMES, min(LAUNCH_LOCKOUT_MAX_FRAMES, raw_frames))
        self.launch_active = True
        self.launch_stage = "ASCENT"
        self.launch_frame = 0
        self.launch_anim_timer = 0.0

    def reset_after_ko(self, x: float, y: float):
        self.center_x = x
        self.center_y = y
        self.change_x = 0.0
        self.change_y = 0.0
        self.damage = 0.0
        self.jumps_remaining = 2
        self.is_grounded = False
        self.hitstun_timer = 0
        self.hit_flash_timer = 0
        self.invincible_timer = RESPAWN_INVULN_FRAMES
        self.respawn_invuln_timer = RESPAWN_INVULN_FRAMES
        self.launch_active = False
        self.launch_lock_timer = 0
        self.shield_health = SHIELD_MAX_HEALTH
        self.shield_stun_timer = 0
        self.is_shielding = False
        self.is_attacking = False
        self.side_combo_window = 0
        self.side_combo_buffered = False
        self.is_charging = False
        self.charge_timer = 0
        self.attack_hitbox = None
        self.color = self.base_color
        self.alpha = 255

    def get_current_attack_damage(self) -> float:
        if self.attack_state == "ATTACK_HEAVY":
            return BASE_DAMAGE * 1.9 * self.charge_power_multiplier
        if self.attack_state == "ATTACK_SIDE_2":
            return BASE_DAMAGE * SIDE_COMBO_DAMAGE_MULT
        if self.attack_state == "ATTACK_DOWN":
            return BASE_DAMAGE * 1.25
        if self.attack_state == "ATTACK_UP":
            return BASE_DAMAGE * 1.15
        return BASE_DAMAGE

    def _current_attack_duration(self) -> int:
        if self.attack_state == "ATTACK_SIDE_1":
            return ATTACK_SIDE_1_DURATION
        if self.attack_state == "ATTACK_SIDE_2":
            return ATTACK_SIDE_2_DURATION
        return ATTACK_DURATION

    def update_physics(self, platforms: list):
        self.just_landed = False
        self.just_jumped = False
        self.just_double_jumped = False

        # Tick passive timers
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.respawn_invuln_timer > 0:
            self.respawn_invuln_timer -= 1
            self.alpha = 110 if (self.respawn_invuln_timer // 4) % 2 == 0 else 255
        else:
            self.alpha = 255

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
            if self.hit_flash_timer == 0:
                self.color = self.base_color

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.side_combo_window > 0:
            self.side_combo_window -= 1
        if self.drop_through_timer > 0:
            self.drop_through_timer -= 1
        if self.landing_timer > 0:
            self.landing_timer -= 1
        if self.shield_stun_timer > 0:
            self.shield_stun_timer -= 1

        # --- Hard-hit Launch Lockout Handling ---
        if self.launch_active:
            if self.hitstun_timer > 0:
                self.hitstun_timer -= 1

            if self.launch_lock_timer > 0:
                self.launch_lock_timer -= 1
                # Discard single-press triggers during the damage-scaled lockout
                self.jump_pressed = False
                self.attack_pressed = False
                self.charge_pressed = False
            elif self.hitstun_timer == 0 and self._has_any_active_input():
                # Cancel launch animation & restore control once lockout expires and player gives input
                self.launch_active = False

            if self.launch_active:
                if self.is_grounded:
                    self.change_x *= GROUND_FRICTION
                    if abs(self.change_x) < 0.15:
                        self.change_x = 0.0
                else:
                    self.change_x *= 0.992
                self._apply_gravity_and_move(platforms, allow_fast_fall=False)
                return

        # Jump buffer & coyote time
        if self.jump_pressed:
            self.jump_buffer_timer = JUMP_BUFFER_FRAMES
            self.jump_pressed = False
        elif self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= 1

        if self.is_grounded:
            self.coyote_timer = COYOTE_TIME_FRAMES
            self.jumps_remaining = 2
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        # Standard hitstun locks actions
        if self.hitstun_timer > 0:
            self.hitstun_timer -= 1
            self.is_shielding = False
            self.is_charging = False
            self.is_attacking = False
            self.side_combo_window = 0
            self.side_combo_buffered = False
            self.attack_hitbox = None
            self._apply_gravity_and_move(platforms, allow_fast_fall=False)
            return

        # Shield logic
        can_shield = (
            self.shield_held
            and self.shield_stun_timer == 0
            and not self.is_attacking
            and not self.is_charging
        )
        if can_shield and self.shield_health > 0:
            self.is_shielding = True
            self.side_combo_window = 0
            self.shield_health = max(0.0, self.shield_health - SHIELD_DRAIN)
            if self.shield_health <= 0:
                self.shield_stun_timer = 110
                self.is_shielding = False
        else:
            self.is_shielding = False
            if self.shield_stun_timer == 0:
                self.shield_health = min(SHIELD_MAX_HEALTH, self.shield_health + SHIELD_REGEN)

        # Heavy charge logic
        if self.charge_pressed and not self.is_attacking and not self.is_shielding and self.attack_cooldown == 0:
            self.is_charging = True
            self.charge_timer = 0
            self.side_combo_window = 0
        self.charge_pressed = False

        if self.is_charging:
            if self.charge_held and self.charge_timer < MAX_CHARGE_FRAMES:
                self.charge_timer += 1
            else:
                ratio = self.charge_timer / MAX_CHARGE_FRAMES
                self.charge_power_multiplier = 1.0 + ratio * 1.15
                self.is_charging = False
                self._start_attack("ATTACK_HEAVY")

        # Directional Attack & 2-Hit Side Combo Trigger
        if self.attack_pressed:
            self.attack_pressed = False
            if self.is_attacking and self.attack_state == "ATTACK_SIDE_1" and self.attack_timer >= 4:
                self.side_combo_buffered = True
            elif not self.is_attacking and not self.is_charging and not self.is_shielding:
                if self.side_combo_window > 0 and not self.up_held and not (self.crouching and not self.is_grounded):
                    self.side_combo_window = 0
                    self._start_attack("ATTACK_SIDE_2")
                elif self.attack_cooldown == 0:
                    self.side_combo_window = 0
                    if self.up_held:
                        self._start_attack("ATTACK_UP")
                    elif self.crouching and not self.is_grounded:
                        self._start_attack("ATTACK_DOWN")
                    else:
                        self._start_attack("ATTACK_SIDE_1")

        # Update active attack & hitbox window
        if self.is_attacking:
            self.attack_timer += 1
            duration = self._current_attack_duration()
            active_end = min(ATTACK_ACTIVE_END, duration - 1)

            if ATTACK_ACTIVE_START <= self.attack_timer <= active_end and not self.attack_has_hit:
                self._update_attack_hitbox()
            else:
                self.attack_hitbox = None

            if self.attack_timer >= duration:
                finished_state = self.attack_state
                self.is_attacking = False
                self.attack_hitbox = None

                if finished_state == "ATTACK_SIDE_1":
                    if self.side_combo_buffered:
                        self.side_combo_buffered = False
                        self.side_combo_window = 0
                        self._start_attack("ATTACK_SIDE_2")
                    else:
                        self.side_combo_window = SIDE_COMBO_WINDOW_FRAMES
                else:
                    self.attack_cooldown = ATTACK_COOLDOWN

        # Horizontal movement
        move_dir = (1 if self.move_right else 0) - (1 if self.move_left else 0)
        if self.is_shielding or self.is_charging:
            move_dir = 0

        if move_dir != 0 and not self.is_attacking:
            self.facing_right = move_dir > 0

        accel = GROUND_ACCEL if self.is_grounded else AIR_ACCEL
        friction = GROUND_FRICTION if self.is_grounded else AIR_FRICTION

        if move_dir != 0:
            self.change_x += move_dir * accel
            self.change_x = max(-MAX_RUN_SPEED, min(MAX_RUN_SPEED, self.change_x))
        else:
            self.change_x *= friction
            if abs(self.change_x) < 0.15:
                self.change_x = 0.0

        # Drop-through soft platforms (Crouch + Jump)
        if self.crouching and self.jump_buffer_timer > 0 and self.is_grounded:
            self.drop_through_timer = DROP_THROUGH_FRAMES
            self.is_grounded = False
            self.jump_buffer_timer = 0
            self.change_y = -4.0
        # Normal / Double Jump
        elif self.jump_buffer_timer > 0 and not self.is_shielding and not self.is_charging:
            if self.coyote_timer > 0:
                self.change_y = JUMP_SPEED
                self.is_grounded = False
                self.coyote_timer = 0
                self.jumps_remaining = 1
                self.jump_buffer_timer = 0
                self.just_jumped = True
            elif self.jumps_remaining > 0:
                self.change_y = DOUBLE_JUMP_SPEED
                self.jumps_remaining -= 1
                self.jump_buffer_timer = 0
                self.just_double_jumped = True

        # Short-hop cut when jump button is released early
        if not self.jump_held and self.change_y > JUMP_SPEED * SHORT_HOP_MULTIPLIER:
            self.change_y *= 0.85

        self._apply_gravity_and_move(platforms, allow_fast_fall=True)

    def _start_attack(self, state: str):
        self.is_attacking = True
        self.attack_state = state
        self.attack_timer = 0
        self.attack_has_hit = False
        self.attack_hitbox = None

    def _update_attack_hitbox(self):
        if self.attack_state == "ATTACK_UP":
            hx = self.center_x - ATTACK_HITBOX_W * 0.50
            hy = self.center_y + self.body_height * 0.22
            self.attack_hitbox = (hx, hy, ATTACK_HITBOX_W, ATTACK_HITBOX_H * 1.15)
        elif self.attack_state == "ATTACK_DOWN":
            hx = self.center_x - ATTACK_HITBOX_W * 0.50
            hy = self.center_y - self.body_height * 0.22 - ATTACK_HITBOX_H * 1.15
            self.attack_hitbox = (hx, hy, ATTACK_HITBOX_W, ATTACK_HITBOX_H * 1.15)
        elif self.attack_state == "ATTACK_SIDE_2":
            reach = ATTACK_REACH * 1.22
            hw = ATTACK_HITBOX_W * SIDE_COMBO_HITBOX_MULT
            hh = ATTACK_HITBOX_H * SIDE_COMBO_HITBOX_MULT
            cx = self.center_x + (reach if self.facing_right else -reach)
            self.attack_hitbox = (cx - hw * 0.5, self.center_y - hh * 0.5, hw, hh)
        else:
            mult = 1.28 if self.attack_state == "ATTACK_HEAVY" else 1.0
            reach = ATTACK_REACH * (1.20 if self.attack_state == "ATTACK_HEAVY" else 1.0)
            hw = ATTACK_HITBOX_W * mult
            hh = ATTACK_HITBOX_H * mult
            cx = self.center_x + (reach if self.facing_right else -reach)
            self.attack_hitbox = (cx - hw * 0.5, self.center_y - hh * 0.5, hw, hh)

    def _apply_gravity_and_move(self, platforms: list, allow_fast_fall: bool = True):
        fast_falling = allow_fast_fall and self.crouching and not self.is_grounded and self.change_y < 0
        max_fall = FAST_FALL_SPEED if fast_falling else MAX_FALL_SPEED
        self.change_y = max(-max_fall, self.change_y - GRAVITY)

        prev_bottom = self.bottom
        was_grounded = self.is_grounded

        # Horizontal step + solid side collision
        self.center_x += self.change_x
        for plat in platforms:
            if plat.pass_through:
                continue
            if self.top > plat.bottom + 4 and self.bottom < plat.top - 4:
                if self.right > plat.left and self.left < plat.right:
                    if self.change_x > 0:
                        self.right = plat.left
                    elif self.change_x < 0:
                        self.left = plat.right
                    self.change_x = 0.0

        # Vertical step + platform landing
        self.center_y += self.change_y
        self.is_grounded = False

        for plat in platforms:
            if self.right <= plat.left + 4 or self.left >= plat.right - 4:
                continue

            if plat.pass_through:
                if self.drop_through_timer > 0:
                    continue
                if self.change_y <= 0 and prev_bottom >= plat.top - 8 and self.bottom <= plat.top:
                    self.bottom = plat.top
                    self.change_y = 0.0
                    self.is_grounded = True
            else:
                if self.change_y <= 0 and prev_bottom >= plat.top - 10 and self.bottom <= plat.top:
                    self.bottom = plat.top
                    self.change_y = 0.0
                    self.is_grounded = True
                elif self.change_y > 0 and self.top >= plat.bottom and prev_bottom < plat.bottom:
                    self.top = plat.bottom
                    self.change_y = 0.0

        if self.is_grounded and not was_grounded:
            self.just_landed = True
            self.landing_timer = 7

    def _update_launch_animation(self, dt: float):
        """
        3-stage Xteve-Launch.png (24 frames: indices 0..23):
          1. ASCENT:   Play first 4 frames (0..3), freeze at frame 3 while moving upwards.
          2. DESCENT:  When falling (change_y < 0), play next 8 frames (4..11), freeze at frame 11.
          3. GROUNDED: Once touching the ground, play remaining frames (12..23) and hold on 23.
        """
        direction_key = "RIGHT" if self.facing_right else "LEFT"
        frames = self.anims[direction_key]["LAUNCH"]
        total = len(frames)

        self.launch_anim_timer += dt
        advance = False
        if self.launch_anim_timer >= LAUNCH_FRAME_DURATION:
            self.launch_anim_timer -= LAUNCH_FRAME_DURATION
            advance = True

        if self.launch_stage == "ASCENT":
            if advance and self.launch_frame < 3:
                self.launch_frame += 1
            if self.launch_frame >= 3 and (self.change_y < 0 or self.is_grounded):
                self.launch_stage = "DESCENT"
                self.launch_frame = 4
                self.launch_anim_timer = 0.0

        elif self.launch_stage == "DESCENT":
            if advance and self.launch_frame < 11:
                self.launch_frame += 1
            if self.is_grounded and self.launch_frame >= 11:
                self.launch_stage = "GROUNDED"
                self.launch_frame = 12
                self.launch_anim_timer = 0.0

        elif self.launch_stage == "GROUNDED":
            if advance and self.launch_frame < total - 1:
                self.launch_frame += 1

        self.anim_state = "LAUNCH"
        self.texture = frames[min(self.launch_frame, total - 1)]

    def update_animation(self, dt: float):
        if self.launch_active:
            self._update_launch_animation(dt)
            return

        if self.hitstun_timer > 0:
            desired = "HIT"
        elif not self.is_grounded:
            desired = "JUMPING" if self.change_y > 1.5 else "FALLING"
        elif self.landing_timer > 0 and abs(self.change_x) < 1.5:
            desired = "LANDING"
        elif self.crouching or self.is_charging:
            desired = "SIT"
        elif abs(self.change_x) > 0.6:
            desired = "WALKING"
        else:
            desired = "IDLE"

        if desired != self.anim_state:
            self.anim_state = desired
            self.anim_timer = 0.0
            self.anim_index = 0

        direction_key = "RIGHT" if self.facing_right else "LEFT"
        frames = self.anims[direction_key][self.anim_state]
        frame_duration = BODY_ANIM_SPECS[self.anim_state][3]

        if len(frames) > 1:
            self.anim_timer += dt
            if self.anim_timer >= frame_duration:
                self.anim_timer -= frame_duration
                self.anim_index = (self.anim_index + 1) % len(frames)

        self.texture = frames[self.anim_index % len(frames)]

    @property
    def attack_vfx_key(self) -> str:
        if self.attack_state in ("ATTACK_SIDE_1", "ATTACK_SIDE_2"):
            return "ATTACK_SIDE"
        return self.attack_state

    @property
    def attack_texture_index(self) -> int:
        direction_key = "RIGHT" if self.facing_right else "LEFT"
        frames = self.vfx[direction_key][self.attack_vfx_key]
        duration = max(1, self._current_attack_duration())
        progress = min(0.999, self.attack_timer / duration)

        if self.attack_state == "ATTACK_SIDE_1":
            return min(4, int(progress * 5))

        if self.attack_state == "ATTACK_SIDE_2":
            remaining = max(1, len(frames) - 5)
            return min(len(frames) - 1, 5 + int(progress * remaining))

        return int(progress * len(frames))