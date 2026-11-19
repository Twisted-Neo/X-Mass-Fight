"""Fighter entity: standardized hurtbox, character weapons, mid-air double-slash Dash Attack, Ledge Grab, DI, and launch."""

import math
import arcade

from assets import get_fighter_animations, get_texture_bottom_pad, get_vfx_animations
from characters import CharacterSpec, WeaponHitboxSpec, get_character_spec
from config import (
    AIR_ACCEL, AIR_FRICTION,
    ATTACK_ACTIVE_END, ATTACK_ACTIVE_START, ATTACK_COOLDOWN,
    ATTACK_DASH_DURATION, ATTACK_DASH_SLASH1_DMG_MULT, ATTACK_DASH_SLASH2_DMG_MULT,
    ATTACK_DASH_SPEED_X, ATTACK_DASH_SPEED_Y,
    ATTACK_DURATION, ATTACK_SIDE_1_DURATION, ATTACK_SIDE_2_DURATION,
    BASE_DAMAGE, BODY_ANIM_SPECS, COYOTE_TIME_FRAMES, DI_INFLUENCE_STRENGTH,
    DROP_THROUGH_FRAMES, DOUBLE_JUMP_SPEED, FAST_FALL_SPEED,
    FIGHTER_HURTBOX_H, FIGHTER_HURTBOX_W, GRAVITY,
    GROUND_ACCEL, GROUND_FRICTION, JUMP_BUFFER_FRAMES, JUMP_SPEED,
    LAUNCH_FRAME_DURATION, LAUNCH_LOCKOUT_BASE_FRAMES,
    LAUNCH_LOCKOUT_FRAMES_PER_DMG, LAUNCH_LOCKOUT_MAX_FRAMES,
    LAUNCH_LOCKOUT_MIN_FRAMES,
    LEDGE_GRAB_BOTTOM_PAD, LEDGE_GRAB_INNER_X, LEDGE_GRAB_OUTER_X, LEDGE_GRAB_TOP_PAD,
    LEDGE_INVULN_FRAMES, LEDGE_MAX_HANG_FRAMES, LEDGE_REGRAB_COOLDOWN,
    MAX_CHARGE_FRAMES, MAX_FALL_SPEED,
    MAX_RUN_SPEED, RESPAWN_INVULN_FRAMES, SHIELD_DRAIN,
    SHIELD_MAX_HEALTH, SHIELD_REGEN, SHORT_HOP_MULTIPLIER,
    SIDE_COMBO_DAMAGE_MULT, SIDE_COMBO_WINDOW_FRAMES,
    STARTING_STOCKS,
)


class Fighter(arcade.Sprite):
    def __init__(
        self,
        x: float,
        y: float,
        name: str,
        accent_color: tuple,
        facing: int = 1,
        char_id: str = "Xteve",
        sprite_tint: tuple = (255, 255, 255, 255),
    ):
        self.spec: CharacterSpec = get_character_spec(char_id)
        self.char_id = self.spec.char_id
        self.anims = get_fighter_animations(self.char_id)
        self.vfx = get_vfx_animations(self.char_id)

        idle_tex = self.anims["RIGHT"]["IDLE"][0]
        super().__init__(idle_tex)

        self.base_scale = self.spec.visual_height / max(1, idle_tex.height)
        self.scale = (self.base_scale, self.base_scale)
        self.player_name = name
        self.accent_color = accent_color
        self.base_color = accent_color
        self.sprite_tint = sprite_tint
        self.color = sprite_tint
        self.facing_right = facing >= 0

        # Subtle bouncy squash & stretch spring state (1.0 = neutral)
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.squash_vel_y = 0.0
        self._bounce_phase = 0.0

        # Animation state (initialized before _sync_sprite_to_hurtbox)
        self.anim_state = "IDLE"
        self.anim_timer = 0.0
        self.anim_index = 0

        # Canonical uniform character hurtbox center (identical dimensions for every character)
        self.hurt_center_x = x
        self.hurt_center_y = y
        self._sync_sprite_to_hurtbox()

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
        self.tech_buffer_timer = 0

        # Match & combat state
        self.stocks = STARTING_STOCKS
        self.damage = 0.0
        self.is_grounded = False
        self.jumps_remaining = 2
        self.air_dash_available = True
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.drop_through_timer = 0
        self.landing_timer = 0

        # Ledge hang state
        self.is_ledge_hanging = False
        self.ledge_side = 0       # -1 = left corner of platform, +1 = right corner
        self.ledge_plat = None
        self.ledge_hang_timer = 0
        self.ledge_regrab_timer = 0

        # Delayed KO respawn state
        self.is_ko_waiting = False
        self.respawn_timer = 0

        self.hitstun_timer = 0
        self.hit_flash_timer = 0
        self.invincible_timer = 0
        self.respawn_invuln_timer = 0

        # Match stats
        self.kos_scored = 0
        self.damage_dealt_total = 0.0
        self.peak_launch_speed = 0.0

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

        # Attacks, Side Combo, Air Dash Attack & Heavy Charge
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

        # One-frame event flags for particles
        self.just_landed = False
        self.just_jumped = False
        self.just_double_jumped = False
        self.just_teched = False
        self.just_grabbed_ledge = False

    # --- Standardized Character Hurtbox Properties (Same Size for All Characters) ---
    @property
    def body_width(self) -> float:
        return FIGHTER_HURTBOX_W

    @property
    def body_height(self) -> float:
        return FIGHTER_HURTBOX_H

    @property
    def hurt_left(self) -> float:
        return self.hurt_center_x - FIGHTER_HURTBOX_W * 0.5

    @property
    def hurt_right(self) -> float:
        return self.hurt_center_x + FIGHTER_HURTBOX_W * 0.5

    @property
    def hurt_bottom(self) -> float:
        return self.hurt_center_y - FIGHTER_HURTBOX_H * 0.5

    @property
    def hurt_top(self) -> float:
        return self.hurt_center_y + FIGHTER_HURTBOX_H * 0.5

    @property
    def is_dash_second_slash(self) -> bool:
        return self.attack_state == "ATTACK_DASH" and self.attack_timer >= (ATTACK_DASH_DURATION // 2)

    def _impulse_squash(self, target_y: float, vel_y: float = 0.0):
        """Applies a subtle squash (<1.0) or stretch (>1.0) impulse to the spring."""
        self.squash_y = max(0.84, min(1.16, target_y))
        self.squash_vel_y = vel_y

    def _update_squash_stretch(self, dt: float):
        """Updates the subtle bouncy spring and keeps horizontal/vertical volume balanced."""
        self._bounce_phase += dt

        if self.launch_active:
            target_y = 1.0
        elif self.is_ledge_hanging:
            target_y = 1.0 + math.sin(self._bounce_phase * 4.5) * 0.015
        elif self.crouching and self.is_grounded:
            target_y = 0.92
        elif self.is_charging:
            charge_pct = min(1.0, self.charge_timer / max(1, MAX_CHARGE_FRAMES))
            target_y = 0.93 - 0.04 * charge_pct
        elif self.is_shielding:
            target_y = 0.96
        elif self.is_grounded and abs(self.change_x) > 0.8:
            target_y = 1.0 + math.sin(self._bounce_phase * 22.0) * 0.028
        elif self.is_grounded and self.anim_state == "IDLE":
            direction_key = "RIGHT" if self.facing_right else "LEFT"
            idle_frames = self.anims[direction_key]["IDLE"]
            idle_dur = BODY_ANIM_SPECS["IDLE"][3]
            progress = (self.anim_index + self.anim_timer / max(1e-6, idle_dur)) / max(1, len(idle_frames))
            target_y = 1.0 + math.sin(progress * math.tau) * 0.014
        else:
            target_y = 1.0

        stiffness = 0.24
        damping = 0.74
        self.squash_vel_y = (self.squash_vel_y + (target_y - self.squash_y) * stiffness) * damping
        self.squash_y = max(0.84, min(1.16, self.squash_y + self.squash_vel_y))
        self.squash_x = max(0.86, min(1.15, 1.0 - (self.squash_y - 1.0) * 0.75))

    def _sync_sprite_to_hurtbox(self):
        """Aligns the lowest opaque pixel of the sprite to the uniform hurtbox bottom and applies squash/stretch."""
        scale_y = self.base_scale * self.squash_y
        self.scale = (self.base_scale * self.squash_x, scale_y)
        pad_px = get_texture_bottom_pad(self.texture) if self.texture is not None else 0
        state_offset = 0.0
        if self.spec.state_ground_offsets:
            state_offset = self.spec.state_ground_offsets.get(self.anim_state, 0.0)
        self.center_x = self.hurt_center_x
        self.bottom = self.hurt_bottom - pad_px * scale_y + state_offset * self.squash_y

    def get_weapon_spec(self, state: str | None = None) -> WeaponHitboxSpec:
        key = state or self.attack_state
        return self.spec.weapons[key]

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

    def trigger_tech_window(self):
        self.tech_buffer_timer = 14

    def _release_ledge(self, regrab_cooldown: int = LEDGE_REGRAB_COOLDOWN):
        self.is_ledge_hanging = False
        self.ledge_side = 0
        self.ledge_plat = None
        self.ledge_hang_timer = 0
        self.ledge_regrab_timer = max(self.ledge_regrab_timer, regrab_cooldown)

    def start_launch(self, damage_dealt: float):
        """Enters the 3-stage launch animation with control lockout scaled by hit damage."""
        self._release_ledge(regrab_cooldown=20)
        self.is_shielding = False
        self.is_charging = False
        self.is_attacking = False
        self.attack_hitbox = None
        self.side_combo_window = 0
        self.side_combo_buffered = False
        self.air_dash_available = True
        self._impulse_squash(0.86, -0.02)

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
        self.is_ko_waiting = False
        self.respawn_timer = 0
        self._release_ledge(regrab_cooldown=0)
        self.hurt_center_x = x
        self.hurt_center_y = y
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.squash_vel_y = 0.0
        self._sync_sprite_to_hurtbox()
        self.change_x = 0.0
        self.change_y = 0.0
        self.damage = 0.0
        self.jumps_remaining = 2
        self.air_dash_available = True
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
        self.color = self.sprite_tint
        self.alpha = 255

    def get_current_attack_damage(self) -> float:
        w_mult = self.get_weapon_spec().damage_mult
        if self.attack_state == "ATTACK_HEAVY":
            return BASE_DAMAGE * 1.9 * self.charge_power_multiplier * w_mult
        if self.attack_state == "ATTACK_DASH":
            mult = ATTACK_DASH_SLASH2_DMG_MULT if self.is_dash_second_slash else ATTACK_DASH_SLASH1_DMG_MULT
            return BASE_DAMAGE * mult * w_mult
        if self.attack_state == "ATTACK_SIDE_2":
            return BASE_DAMAGE * SIDE_COMBO_DAMAGE_MULT * w_mult
        if self.attack_state == "ATTACK_DOWN":
            return BASE_DAMAGE * 1.25 * w_mult
        if self.attack_state == "ATTACK_UP":
            return BASE_DAMAGE * 1.15 * w_mult
        return BASE_DAMAGE * w_mult

    def _current_attack_duration(self) -> int:
        if self.attack_state == "ATTACK_SIDE_1":
            return ATTACK_SIDE_1_DURATION
        if self.attack_state == "ATTACK_SIDE_2":
            return ATTACK_SIDE_2_DURATION
        if self.attack_state == "ATTACK_DASH":
            return ATTACK_DASH_DURATION
        return ATTACK_DURATION

    def _update_ledge_hang(self) -> bool:
        """Handles hanging on a main-stage corner and all 4 Smash-style ledge get-up options."""
        if not self.is_ledge_hanging or self.ledge_plat is None:
            return False

        plat = self.ledge_plat
        inward = -self.ledge_side  # +1 if hanging on left edge, -1 if hanging on right edge
        self.facing_right = inward > 0
        self.change_x = 0.0
        self.change_y = 0.0
        self.jumps_remaining = 2
        self.air_dash_available = True

        if self.ledge_side == -1:
            self.hurt_center_x = plat.left - FIGHTER_HURTBOX_W * 0.5 - 2.0
        else:
            self.hurt_center_x = plat.right + FIGHTER_HURTBOX_W * 0.5 + 2.0
        self.hurt_center_y = plat.top - FIGHTER_HURTBOX_H * 0.5 - 6.0

        self.ledge_hang_timer -= 1

        # 1. Ledge Jump
        if self.jump_pressed:
            self.jump_pressed = False
            self._release_ledge(regrab_cooldown=24)
            self.change_y = JUMP_SPEED * 0.96
            self.change_x = inward * 4.8
            self.jumps_remaining = 1
            self.just_jumped = True
            self._impulse_squash(1.13, 0.015)
            self._sync_sprite_to_hurtbox()
            return True

        # 2. Ledge Get-Up Attack
        if self.attack_pressed:
            self.attack_pressed = False
            self._release_ledge(regrab_cooldown=24)
            self.hurt_center_x = (plat.left + 26.0) if inward > 0 else (plat.right - 26.0)
            self.hurt_center_y = plat.top + FIGHTER_HURTBOX_H * 0.5
            self.is_grounded = True
            self.invincible_timer = max(self.invincible_timer, 14)
            self._start_attack("ATTACK_SIDE_1")
            self._sync_sprite_to_hurtbox()
            return True

        # 3. Normal Ledge Climb (hold toward stage)
        pressing_inward = (inward > 0 and self.move_right) or (inward < 0 and self.move_left)
        pressing_outward = (inward > 0 and self.move_left) or (inward < 0 and self.move_right)

        if pressing_inward:
            self._release_ledge(regrab_cooldown=20)
            self.hurt_center_x = (plat.left + 28.0) if inward > 0 else (plat.right - 28.0)
            self.hurt_center_y = plat.top + FIGHTER_HURTBOX_H * 0.5
            self.is_grounded = True
            self.invincible_timer = max(self.invincible_timer, 14)
            self._impulse_squash(0.92, -0.01)
            self._sync_sprite_to_hurtbox()
            return True

        # 4. Ledge Drop (hold down, press away, or max hang timeout)
        if self.crouching or pressing_outward or self.ledge_hang_timer <= 0:
            self._release_ledge(regrab_cooldown=LEDGE_REGRAB_COOLDOWN)
            self.change_y = -2.5
            self._sync_sprite_to_hurtbox()
            return True

        self._sync_sprite_to_hurtbox()
        return True

    def update_physics(self, platforms: list, opponent: "Fighter | None" = None):
        self.just_landed = False
        self.just_jumped = False
        self.just_double_jumped = False
        self.just_teched = False
        self.just_grabbed_ledge = False

        if self.is_ko_waiting:
            self.attack_hitbox = None
            return

        # Tick passive timers
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.respawn_invuln_timer > 0:
            self.respawn_invuln_timer -= 1
            self.alpha = 110 if (self.respawn_invuln_timer // 4) % 2 == 0 else 255
            if self.attack_pressed or self.charge_pressed:
                self.respawn_invuln_timer = 0
                self.invincible_timer = 0
                self.alpha = 255
        else:
            self.alpha = 255

        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= 1
            if self.hit_flash_timer == 0:
                self.color = self.sprite_tint

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
        if self.tech_buffer_timer > 0:
            self.tech_buffer_timer -= 1
        if self.ledge_regrab_timer > 0:
            self.ledge_regrab_timer -= 1

        # Handle active ledge hang before standard movement
        if self.is_ledge_hanging:
            self._update_ledge_hang()
            return

        # --- Hard-hit Launch Lockout, DI & Ground Tech Handling ---
        if self.launch_active:
            if self.hitstun_timer > 0:
                self.hitstun_timer -= 1

            if not self.is_grounded:
                di_x = (1 if self.move_right else 0) - (1 if self.move_left else 0)
                di_y = (1 if self.up_held else 0) - (1 if self.crouching else 0)
                self.change_x += di_x * DI_INFLUENCE_STRENGTH
                self.change_y += di_y * DI_INFLUENCE_STRENGTH * 0.85

            if self.launch_lock_timer > 0:
                self.launch_lock_timer -= 1
                self.jump_pressed = False
                self.attack_pressed = False
                self.charge_pressed = False
            elif self.hitstun_timer == 0 and self._has_any_active_input():
                self.launch_active = False

            if self.launch_active:
                if self.is_grounded:
                    self.change_x *= GROUND_FRICTION
                    if abs(self.change_x) < 0.15:
                        self.change_x = 0.0
                else:
                    self.change_x *= 0.992
                self._apply_gravity_and_move(platforms, allow_fast_fall=False, opponent=opponent)

                if self.just_landed and self.tech_buffer_timer > 0:
                    self.launch_active = False
                    self.launch_lock_timer = 0
                    self.hitstun_timer = 0
                    self.tech_buffer_timer = 0
                    self.invincible_timer = 18
                    self.just_teched = True
                    self._impulse_squash(1.12, 0.02)
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
            self.air_dash_available = True
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

        # Standard hitstun locks actions (with subtle DI)
        if self.hitstun_timer > 0:
            self.hitstun_timer -= 1
            di_x = (1 if self.move_right else 0) - (1 if self.move_left else 0)
            self.change_x += di_x * (DI_INFLUENCE_STRENGTH * 0.75)
            self.is_shielding = False
            self.is_charging = False
            self.is_attacking = False
            self.side_combo_window = 0
            self.side_combo_buffered = False
            self.attack_hitbox = None
            self.air_dash_available = True
            self._apply_gravity_and_move(platforms, allow_fast_fall=False, opponent=opponent)
            return

        # Shield logic (grounded only)
        can_shield = (
            self.shield_held
            and self.is_grounded
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

        # Heavy Charge (Grounded ONLY) vs. Mid-Air Double-Slash Dash Attack (Airborne)
        if self.charge_pressed and not self.is_attacking and not self.is_shielding and self.attack_cooldown == 0:
            if self.is_grounded:
                self.is_charging = True
                self.charge_timer = 0
                self.side_combo_window = 0
            elif self.air_dash_available:
                self._start_dash_attack()
        self.charge_pressed = False

        if self.is_charging:
            if not self.is_grounded:
                # Walked/pushed off platform while charging -> cancel charge cleanly
                self.is_charging = False
                self.charge_timer = 0
            elif self.charge_held and self.charge_timer < MAX_CHARGE_FRAMES:
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

        # Update active attack & character-specific weapon hitbox window
        if self.is_attacking:
            self.attack_timer += 1
            duration = self._current_attack_duration()

            if self.attack_state == "ATTACK_DASH":
                half = duration // 2
                # Transition from Slash 1 -> vertically flipped Slash 2
                if self.attack_timer == half:
                    self.attack_has_hit = False
                    self.attack_hitbox = None
                    dir_sign = 1 if self.facing_right else -1
                    self.change_x = dir_sign * (ATTACK_DASH_SPEED_X * 0.85)
                    self.change_y = max(self.change_y, ATTACK_DASH_SPEED_Y * 0.55)
                    self._impulse_squash(1.08, 0.01)

                in_slash_1 = ATTACK_ACTIVE_START <= self.attack_timer <= (half - 2)
                in_slash_2 = (half + 1) <= self.attack_timer <= (duration - 2)
                if (in_slash_1 or in_slash_2) and not self.attack_has_hit:
                    self._update_attack_hitbox()
                else:
                    self.attack_hitbox = None
            else:
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

        if self.is_attacking and self.attack_state == "ATTACK_DASH":
            # Maintain crisp air-dash momentum during the double-slash recovery
            self.change_x *= 0.94
        else:
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
            self._impulse_squash(1.07, 0.01)
        # Normal / Double Jump
        elif self.jump_buffer_timer > 0 and not self.is_shielding and not self.is_charging:
            if self.coyote_timer > 0:
                self.change_y = JUMP_SPEED
                self.is_grounded = False
                self.coyote_timer = 0
                self.jumps_remaining = 1
                self.jump_buffer_timer = 0
                self.just_jumped = True
                self._impulse_squash(1.13, 0.015)
            elif self.jumps_remaining > 0:
                self.change_y = DOUBLE_JUMP_SPEED
                self.jumps_remaining -= 1
                self.jump_buffer_timer = 0
                self.just_double_jumped = True
                self._impulse_squash(1.11, 0.015)

        # Short-hop cut when jump button is released early
        if not self.jump_held and self.change_y > JUMP_SPEED * SHORT_HOP_MULTIPLIER:
            self.change_y *= 0.85

        self._apply_gravity_and_move(platforms, allow_fast_fall=True, opponent=opponent)

    def _start_dash_attack(self):
        """Mid-air Heavy button action: horizontal/upward recovery dash + double-slash arc."""
        if self.move_right and not self.move_left:
            self.facing_right = True
        elif self.move_left and not self.move_right:
            self.facing_right = False

        dir_sign = 1 if self.facing_right else -1
        self.air_dash_available = False
        self.side_combo_window = 0
        self.side_combo_buffered = False
        self.change_x = dir_sign * ATTACK_DASH_SPEED_X
        self.change_y = max(self.change_y * 0.35 + ATTACK_DASH_SPEED_Y, ATTACK_DASH_SPEED_Y)
        self._start_attack("ATTACK_DASH")
        self._impulse_squash(0.88, -0.015)

    def _start_attack(self, state: str):
        self.is_attacking = True
        self.attack_state = state
        self.attack_timer = 0
        self.attack_has_hit = False
        self.attack_hitbox = None

        # Subtle forward/vertical attack lunge squash & stretch
        if state == "ATTACK_UP":
            self._impulse_squash(1.10, 0.01)
        elif state == "ATTACK_DOWN":
            self._impulse_squash(1.08, 0.01)
        elif state == "ATTACK_HEAVY":
            self._impulse_squash(0.90, 0.015)
        else:
            self._impulse_squash(0.94, 0.01)

    def _update_attack_hitbox(self):
        """Builds this character's weapon hitbox anchored to the standardized character hurtbox center."""
        w_spec = self.get_weapon_spec()
        cx = self.hurt_center_x + (w_spec.reach if self.facing_right else -w_spec.reach)
        cy = self.hurt_center_y + w_spec.offset_y
        self.attack_hitbox = (cx - w_spec.width * 0.5, cy - w_spec.height * 0.5, w_spec.width, w_spec.height)

    def _try_grab_ledge(self, platforms: list, opponent: "Fighter | None" = None) -> bool:
        """Checks if an airborne fighter can snap onto a main-stage corner ledge."""
        if self.is_grounded or self.ledge_regrab_timer > 0 or self.crouching:
            return False
        if self.hitstun_timer > 0 or self.launch_active:
            return False
        if self.change_y > 4.5:
            return False

        for plat in platforms:
            if plat.pass_through:
                continue

            # Left ledge of main stage
            left_taken = (
                opponent is not None
                and opponent.is_ledge_hanging
                and opponent.ledge_plat is plat
                and opponent.ledge_side == -1
            )
            if not left_taken:
                if (plat.left - LEDGE_GRAB_OUTER_X) <= self.hurt_right <= (plat.left + LEDGE_GRAB_INNER_X):
                    if (plat.top - LEDGE_GRAB_BOTTOM_PAD) <= self.hurt_top <= (plat.top + LEDGE_GRAB_TOP_PAD):
                        self._attach_to_ledge(plat, side=-1)
                        return True

            # Right ledge of main stage
            right_taken = (
                opponent is not None
                and opponent.is_ledge_hanging
                and opponent.ledge_plat is plat
                and opponent.ledge_side == 1
            )
            if not right_taken:
                if (plat.right - LEDGE_GRAB_INNER_X) <= self.hurt_left <= (plat.right + LEDGE_GRAB_OUTER_X):
                    if (plat.top - LEDGE_GRAB_BOTTOM_PAD) <= self.hurt_top <= (plat.top + LEDGE_GRAB_TOP_PAD):
                        self._attach_to_ledge(plat, side=1)
                        return True

        return False

    def _attach_to_ledge(self, plat, side: int):
        self.is_ledge_hanging = True
        self.ledge_plat = plat
        self.ledge_side = side
        self.ledge_hang_timer = LEDGE_MAX_HANG_FRAMES
        self.is_attacking = False
        self.attack_hitbox = None
        self.is_charging = False
        self.is_shielding = False
        self.change_x = 0.0
        self.change_y = 0.0
        self.jumps_remaining = 2
        self.air_dash_available = True
        self.facing_right = side == -1
        self.invincible_timer = max(self.invincible_timer, LEDGE_INVULN_FRAMES)
        self.just_grabbed_ledge = True
        self._impulse_squash(0.92, -0.01)

        if side == -1:
            self.hurt_center_x = plat.left - FIGHTER_HURTBOX_W * 0.5 - 2.0
        else:
            self.hurt_center_x = plat.right + FIGHTER_HURTBOX_W * 0.5 + 2.0
        self.hurt_center_y = plat.top - FIGHTER_HURTBOX_H * 0.5 - 6.0

    def _apply_gravity_and_move(self, platforms: list, allow_fast_fall: bool = True, opponent: "Fighter | None" = None):
        is_dashing = self.is_attacking and self.attack_state == "ATTACK_DASH"
        grav = GRAVITY * 0.35 if is_dashing else GRAVITY
        fast_falling = allow_fast_fall and not is_dashing and self.crouching and not self.is_grounded and self.change_y < 0
        max_fall = FAST_FALL_SPEED if fast_falling else MAX_FALL_SPEED
        self.change_y = max(-max_fall, self.change_y - grav)

        prev_bottom = self.hurt_bottom
        was_grounded = self.is_grounded
        impact_vy = abs(self.change_y)

        # Horizontal step + solid side collision using standardized character hurtbox
        self.hurt_center_x += self.change_x
        for plat in platforms:
            if plat.pass_through:
                continue
            if self.hurt_top > plat.bottom + 4 and self.hurt_bottom < plat.top - 4:
                if self.hurt_right > plat.left and self.hurt_left < plat.right:
                    if self.change_x > 0:
                        self.hurt_center_x = plat.left - FIGHTER_HURTBOX_W * 0.5
                    elif self.change_x < 0:
                        self.hurt_center_x = plat.right + FIGHTER_HURTBOX_W * 0.5
                    self.change_x = 0.0

        # Vertical step + platform landing using standardized character hurtbox
        self.hurt_center_y += self.change_y
        self.is_grounded = False

        for plat in platforms:
            if self.hurt_right <= plat.left + 4 or self.hurt_left >= plat.right - 4:
                continue

            if plat.pass_through:
                if self.drop_through_timer > 0:
                    continue
                if self.change_y <= 0 and prev_bottom >= plat.top - 8 and self.hurt_bottom <= plat.top:
                    self.hurt_center_y = plat.top + FIGHTER_HURTBOX_H * 0.5
                    self.change_y = 0.0
                    self.is_grounded = True
            else:
                if self.change_y <= 0 and prev_bottom >= plat.top - 10 and self.hurt_bottom <= plat.top:
                    self.hurt_center_y = plat.top + FIGHTER_HURTBOX_H * 0.5
                    self.change_y = 0.0
                    self.is_grounded = True
                elif self.change_y > 0 and self.hurt_top >= plat.bottom and prev_bottom < plat.bottom:
                    self.hurt_center_y = plat.bottom - FIGHTER_HURTBOX_H * 0.5
                    self.change_y = 0.0

        if not self.is_grounded:
            self._try_grab_ledge(platforms, opponent=opponent)

        if self.is_grounded and not was_grounded:
            self.just_landed = True
            self.landing_timer = 7
            self.air_dash_available = True
            impact_ratio = min(1.0, impact_vy / max(1.0, MAX_FALL_SPEED))
            self._impulse_squash(0.93 - 0.07 * impact_ratio, -0.015)

        self._sync_sprite_to_hurtbox()

    def _update_launch_animation(self, dt: float):
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
        self._update_squash_stretch(dt)
        self._sync_sprite_to_hurtbox()

    def update_animation(self, dt: float):
        if self.is_ko_waiting:
            return

        if self.launch_active:
            self._update_launch_animation(dt)
            return

        if self.hitstun_timer > 0:
            desired = "HIT"
        elif self.is_ledge_hanging:
            desired = "JUMPING"
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
        self._update_squash_stretch(dt)
        self._sync_sprite_to_hurtbox()

    @property
    def attack_vfx_key(self) -> str:
        if self.attack_state in ("ATTACK_SIDE_1", "ATTACK_SIDE_2"):
            return "ATTACK_SIDE"
        if self.attack_state == "ATTACK_DASH":
            return "ATTACK_DASH_2" if self.is_dash_second_slash else "ATTACK_DASH_1"
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

        if self.attack_state == "ATTACK_DASH":
            half = max(1, duration // 2)
            local_t = (self.attack_timer % half) / half
            return min(len(frames) - 1, int(local_t * len(frames)))

        return int(progress * len(frames))