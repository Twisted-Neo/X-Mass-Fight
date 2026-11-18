"""Main game view — camera, HUD, match flow, combat resolution."""

import math
import random

import arcade

from arcade_compat import (
    draw_filled_rectangle, draw_line,
    draw_rectangle_outline, draw_sprite, draw_text,
)
from background import Background
from config import (
    ATTACK_DURATION, ATTACK_REACH,
    BASE_DAMAGE, BASE_KNOCKBACK_X, BASE_KNOCKBACK_Y,
    BLAST_ZONE, DEBUG_HITBOXES,
    HITSTOP_FRAMES, HITSTUN_BASE, INVINCIBLE_HIT_FRAMES,
    KNOCKBACK_DAMAGE_SCALE,
    MAX_FRAME_TIME, MAX_STEPS_PER_FRAME, PHYSICS_STEP,
    COLOR_BG_TOP, COLOR_GOLD, COLOR_HITBOX_DEBUG, COLOR_HIT_FLASH,
    COLOR_HUD_BG, COLOR_HUD_BORDER, COLOR_HUD_P1, COLOR_HUD_P2,
    COLOR_SWIPE, COLOR_TEXT, COLOR_TEXT_DIM,
    HEART_CHAR, WINDOW_HEIGHT, WINDOW_WIDTH,
)
from fighter import Fighter
from game_platform import Platform
from particle import ParticleSystem
from snow import SnowParticle


class XMassFightView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = COLOR_BG_TOP
        self.setup()

    def setup(self):
        self.p1 = Fighter(
            WINDOW_WIDTH * 0.30, 400, "Player 1", COLOR_HUD_P1, facing=1,
        )
        self.p2 = Fighter(
            WINDOW_WIDTH * 0.70, 400, "Player 2", COLOR_HUD_P2, facing=-1,
        )

        self.platforms = [
            Platform(WINDOW_WIDTH / 2,       140, 1000, 50, pass_through=False),
            Platform(WINDOW_WIDTH * 0.20,    320,  320, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.80,    320,  320, 22, pass_through=True),
            Platform(WINDOW_WIDTH / 2,       480,  380, 22, pass_through=True),
            Platform(WINDOW_WIDTH / 2,       640,  220, 22, pass_through=True),
        ]

        self.snow = [SnowParticle(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(100)]
        self.particles = ParticleSystem()
        self.background = Background()

        self.accumulator = 0.0
        self.screen_shake = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0
        self.hitstop_timer = 0

        self.intro_timer = 100
        self.game_state = "INTRO"    # INTRO → PLAYING → OVER
        self.game_over_text = None
        self.game_over_subtext = None

    def on_show_view(self):
        try:
            arcade.set_background_color(COLOR_BG_TOP)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # UPDATE — fixed timestep with accumulator
    # ------------------------------------------------------------------

    def on_update(self, delta_time):
        delta_time = min(delta_time, MAX_FRAME_TIME)

        # Cosmetic updates run every frame (framerate-independent)
        self.background.update(delta_time)
        for flake in self.snow:
            flake.update(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.particles.update()

        # Screen shake decays over real time
        if self.screen_shake > 0:
            self.shake_offset_x = random.uniform(
                -self.screen_shake, self.screen_shake,
            )
            self.shake_offset_y = random.uniform(
                -self.screen_shake, self.screen_shake,
            )
            self.screen_shake = max(0.0, self.screen_shake - delta_time * 60)
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

        if self.game_state == "OVER":
            return

        # Fixed-step game logic
        self.accumulator += delta_time
        steps = 0
        while (self.accumulator >= PHYSICS_STEP
               and steps < MAX_STEPS_PER_FRAME):
            self.accumulator -= PHYSICS_STEP
            self._game_step()
            steps += 1

        self._handle_blast_zones()

    def _game_step(self):
        if self.game_state == "INTRO":
            self.intro_timer -= 1
            if self.intro_timer <= 0:
                self.game_state = "PLAYING"
            return

        # Hitstop freezes physics but flashes still decay
        if self.hitstop_timer > 0:
            self.hitstop_timer -= 1
            for f in (self.p1, self.p2):
                if f.hit_flash_timer > 0:
                    f.hit_flash_timer -= 1
                    if f.hit_flash_timer == 0:
                        f.color = f.base_color
            return

        self.p1.update_physics(self.platforms)
        self.p2.update_physics(self.platforms)

        # Emit movement particles
        for f in (self.p1, self.p2):
            if f.just_landed:
                self.particles.emit_land(f.center_x, f.bottom)
            if f.just_jumped:
                self.particles.emit_jump(f.center_x, f.bottom)
            if f.just_double_jumped:
                self.particles.emit_sparkle(f.center_x, f.bottom)

        self.p1.update_animation(PHYSICS_STEP)
        self.p2.update_animation(PHYSICS_STEP)

        self._check_attack_collisions(self.p1, self.p2)
        self._check_attack_collisions(self.p2, self.p1)

    # ------------------------------------------------------------------
    # COMBAT
    # ------------------------------------------------------------------

    def _check_attack_collisions(self, attacker, defender):
        if not attacker.attack_hitbox or attacker.attack_has_hit:
            return
        if defender.invincible_timer > 0 or self.game_state != "PLAYING":
            return

        hx, hy, hw, hh = attacker.attack_hitbox
        if not (defender.right > hx and defender.left < hx + hw
                and defender.top > hy and defender.bottom < hy + hh):
            return

        # Damage + scaling knockback
        defender.damage += BASE_DAMAGE
        scale = 1.0 + defender.damage * KNOCKBACK_DAMAGE_SCALE
        direction = 1 if attacker.facing_right else -1
        defender.change_x = BASE_KNOCKBACK_X * scale * direction
        defender.change_y = BASE_KNOCKBACK_Y * scale
        defender.hitstun_timer = int(HITSTUN_BASE * scale)
        defender.is_grounded = False
        defender.invincible_timer = INVINCIBLE_HIT_FRAMES

        # Feedback
        self.hitstop_timer = HITSTOP_FRAMES
        defender.hit_flash_timer = 6
        defender.color = COLOR_HIT_FLASH
        self.screen_shake = 12.0

        contact_x = defender.left if attacker.facing_right else defender.right
        self.particles.emit_hit(contact_x, defender.center_y, direction)

        attacker.attack_has_hit = True
        attacker.attack_hitbox = None

    # ------------------------------------------------------------------
    # BLAST ZONES
    # ------------------------------------------------------------------

    def _is_out(self, p):
        return (
            p.center_y < -BLAST_ZONE
            or p.center_y > WINDOW_HEIGHT + BLAST_ZONE
            or p.center_x < -BLAST_ZONE
            or p.center_x > WINDOW_WIDTH + BLAST_ZONE
        )

    def _handle_blast_zones(self):
        if self.game_state != "PLAYING":
            return
        if self.hitstop_timer > 0:
            return

        p1_out = self._is_out(self.p1)
        p2_out = self._is_out(self.p2)

        if p1_out and p2_out:
            self.p1.stocks -= 1
            self.p2.stocks -= 1
            self.particles.emit_ko(self.p1.center_x, self.p1.center_y)
            self.particles.emit_ko(self.p2.center_x, self.p2.center_y)
            self.screen_shake = 20.0
            if self.p1.stocks <= 0 and self.p2.stocks <= 0:
                self._end_game("DRAW", "No winners today.")
            elif self.p1.stocks <= 0:
                self._end_game("PLAYER 2 WINS", "A flawless holiday performance.")
            elif self.p2.stocks <= 0:
                self._end_game("PLAYER 1 WINS", "A flawless holiday performance.")
            else:
                self._respawn(self.p1)
                self._respawn(self.p2)
            return

        if p1_out:
            self._single_ko(self.p1, self.p2)
        elif p2_out:
            self._single_ko(self.p2, self.p1)

    def _single_ko(self, victim, survivor):
        victim.stocks -= 1
        self.particles.emit_ko(victim.center_x, victim.center_y)
        self.screen_shake = 20.0
        if victim.stocks <= 0:
            self._end_game(
                f"{survivor.player_name.upper()} WINS",
                "The season is over — champion crowned.",
            )
            return
        self._respawn(victim)

    def _respawn(self, player):
        x = WINDOW_WIDTH * 0.30 if player is self.p1 else WINDOW_WIDTH * 0.70
        player.reset_after_ko(x, 500)
        self.particles.emit_sparkle(player.center_x, player.center_y, count=20)

    def _end_game(self, title, subtext):
        self.game_over_text = title
        self.game_over_subtext = subtext
        self.game_state = "OVER"

    # ------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------

    def _apply_shake_viewport(self):
        sx, sy = self.shake_offset_x, self.shake_offset_y
        try:
            arcade.set_viewport(-sx, WINDOW_WIDTH - sx, -sy, WINDOW_HEIGHT - sy)
        except Exception:
            pass

    def _clear_shake_viewport(self):
        try:
            arcade.set_viewport(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        except Exception:
            pass

    def on_draw(self):
        self.clear()

        self.background.draw()

        self._apply_shake_viewport()
        try:
            for flake in self.snow:
                flake.draw()
            for platform in self.platforms:
                platform.draw()

            draw_sprite(self.p1)
            draw_sprite(self.p2)

            self._draw_attack_effects()
            self.particles.draw()

            if DEBUG_HITBOXES:
                for f in (self.p1, self.p2):
                    if f.attack_hitbox:
                        x, y, w, h = f.attack_hitbox
                        draw_rectangle_outline(
                            x + w / 2, y + h / 2, w, h,
                            COLOR_HITBOX_DEBUG, 2,
                        )

            self._draw_blast_zone_glow()
        finally:
            self._clear_shake_viewport()

        self._draw_hud()
        self._draw_intro()
        self._draw_game_over()

    def _draw_attack_effects(self):
        for fighter in (self.p1, self.p2):
            if not fighter.is_attacking:
                continue
            progress = fighter.attack_timer / ATTACK_DURATION
            if progress <= 0:
                continue
            hx = fighter.center_x + (ATTACK_REACH if fighter.facing_right
                                      else -ATTACK_REACH)
            hy = fighter.center_y
            alpha = int(200 * progress)
            if alpha <= 0:
                continue
            r = 55 * (1.0 + (1.0 - progress) * 0.2)
            base_ang = 0.0 if fighter.facing_right else math.pi
            for i in range(6):
                t = i / 5
                ang = base_ang + (-0.7 + t * 1.4)
                sx = hx + math.cos(ang) * r * 0.2
                sy = hy + math.sin(ang) * r * 0.8
                ex = hx + math.cos(ang) * r
                ey = hy + math.sin(ang) * r
                draw_line(
                    sx, sy, ex, ey,
                    (COLOR_SWIPE[0], COLOR_SWIPE[1], COLOR_SWIPE[2], alpha),
                    3 + int((1 - progress) * 3),
                )

    def _draw_blast_zone_glow(self):
        for p in (self.p1, self.p2):
            if (p.center_x < -80 or p.center_x > WINDOW_WIDTH + 80
                    or p.center_y < -80 or p.center_y > WINDOW_HEIGHT + 80):
                for i in range(3):
                    a = 40 - i * 12
                    draw_filled_rectangle(
                        WINDOW_WIDTH / 2, 6 + i * 6, WINDOW_WIDTH, 12,
                        (255, 60, 60, max(0, a)),
                    )

    def _draw_hud(self):
        self._draw_player_hud(self.p1, "PLAYER 1", COLOR_HUD_P1, left=True)
        self._draw_player_hud(self.p2, "PLAYER 2", COLOR_HUD_P2, left=False)
        self._draw_legend()

    def _draw_player_hud(self, player, label, accent, left):
        pw, ph = 400, 130
        cx = pw / 2 + 20 if left else WINDOW_WIDTH - pw / 2 - 20
        cy = ph / 2 + 20

        draw_filled_rectangle(cx, cy, pw, ph, COLOR_HUD_BG)
        draw_rectangle_outline(cx, cy, pw, ph, accent, 4)

        inner_l = cx - pw / 2 + 25
        inner_r = cx + pw / 2 - 25
        top_y = cy + ph / 2 - 28
        mid_y = cy - 5

        dmg = int(player.damage)
        if dmg < 50:
            dmg_col = (140, 230, 140, 255)
        elif dmg < 100:
            dmg_col = (240, 220, 100, 255)
        elif dmg < 150:
            dmg_col = (250, 160, 80, 255)
        else:
            dmg_col = (255, 80, 80, 255)

        hearts = (HEART_CHAR + " ") * player.stocks

        if left:
            draw_text(label, inner_l, top_y, accent, 18, bold=True)
            draw_text("STOCKS", inner_r, top_y, COLOR_TEXT_DIM, 11,
                      anchor_x="right")
            draw_text(hearts, inner_r, mid_y, COLOR_GOLD, 24,
                      anchor_x="right", bold=True)
            draw_text(f"{dmg}%", inner_l, mid_y - 2, dmg_col, 32, bold=True)
        else:
            draw_text(label, inner_r, top_y, accent, 18,
                      anchor_x="right", bold=True)
            draw_text("STOCKS", inner_l, top_y, COLOR_TEXT_DIM, 11)
            draw_text(hearts, inner_l, mid_y, COLOR_GOLD, 24, bold=True)
            draw_text(f"{dmg}%", inner_r, mid_y - 2, dmg_col, 32,
                      anchor_x="right", bold=True)

    def _draw_legend(self):
        bar_y = WINDOW_HEIGHT - 36
        draw_filled_rectangle(
            WINDOW_WIDTH / 2, bar_y, WINDOW_WIDTH - 60, 50,
            (10, 12, 22, 180),
        )
        draw_rectangle_outline(
            WINDOW_WIDTH / 2, bar_y, WINDOW_WIDTH - 60, 50,
            COLOR_HUD_BORDER, 2,
        )
        draw_text(
            "P1:  A / D  move    S  crouch    W or Space  jump    F  attack",
            40, bar_y - 5, COLOR_TEXT, 13,
        )
        draw_text(
            "P2:  Left / Right  move    Down  crouch    "
            "Up or RShift  jump    Enter  attack",
            WINDOW_WIDTH - 40, bar_y - 5, COLOR_TEXT, 13, anchor_x="right",
        )

    def _draw_intro(self):
        if self.game_state != "INTRO":
            return
        if self.intro_timer > 70:
            text = "3"
        elif self.intro_timer > 45:
            text = "2"
        elif self.intro_timer > 20:
            text = "1"
        else:
            text = "GO!"
        draw_text(
            text, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2,
            COLOR_GOLD, 140, anchor_x="center", bold=True,
        )

    def _draw_game_over(self):
        if self.game_state != "OVER":
            return
        draw_filled_rectangle(
            WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2,
            WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 160),
        )
        draw_text(
            self.game_over_text,
            WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 50,
            COLOR_GOLD, 64, anchor_x="center", bold=True,
        )
        if self.game_over_subtext:
            draw_text(
                self.game_over_subtext,
                WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 10,
                COLOR_TEXT, 22, anchor_x="center",
            )
        draw_text(
            "Press R to restart",
            WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 100,
            COLOR_TEXT_DIM, 20, anchor_x="center",
        )

    # ------------------------------------------------------------------
    # CONTROLS
    # ------------------------------------------------------------------

    def on_key_press(self, key, modifiers):
        if self.game_state == "OVER":
            if key == arcade.key.R:
                self.setup()
            return

        if key == arcade.key.A:
            self.p1.move_left = True
        elif key == arcade.key.D:
            self.p1.move_right = True
        elif key == arcade.key.S:
            self.p1.crouching = True
        elif key in (arcade.key.SPACE, arcade.key.W):
            self.p1.jump_pressed = True
        elif key == arcade.key.F:
            self.p1.attack_pressed = True
        elif key == arcade.key.LEFT:
            self.p2.move_left = True
        elif key == arcade.key.RIGHT:
            self.p2.move_right = True
        elif key == arcade.key.DOWN:
            self.p2.crouching = True
        elif key in (arcade.key.UP, arcade.key.RSHIFT):
            self.p2.jump_pressed = True
        elif key == arcade.key.ENTER:
            self.p2.attack_pressed = True

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.p1.move_left = False
        elif key == arcade.key.D:
            self.p1.move_right = False
        elif key == arcade.key.S:
            self.p1.crouching = False
        elif key in (arcade.key.SPACE, arcade.key.W):
            self.p1.jump_pressed = False
        elif key == arcade.key.LEFT:
            self.p2.move_left = False
        elif key == arcade.key.RIGHT:
            self.p2.move_right = False
        elif key == arcade.key.DOWN:
            self.p2.crouching = False
        elif key in (arcade.key.UP, arcade.key.RSHIFT):
            self.p2.jump_pressed = False
            