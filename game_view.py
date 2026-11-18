"""Main game views: Title Screen, Controls, Match View with charged attack effects and correct rendering scale."""

import math
import random
import arcade

from arcade_compat import (
    draw_filled_rectangle,
    draw_rectangle_outline, draw_sprite, draw_text, draw_texture_rectangle,
)
from background import Background
from config import (
    ATTACK_REACH, BASE_KNOCKBACK_X, BASE_KNOCKBACK_Y,
    BLAST_ZONE, DEBUG_HITBOXES,
    HITSTOP_FRAMES, HITSTUN_BASE, INVINCIBLE_HIT_FRAMES,
    KNOCKBACK_DAMAGE_SCALE,
    MAX_FRAME_TIME, MAX_STEPS_PER_FRAME, PHYSICS_STEP,
    COLOR_BG_TOP, COLOR_GOLD, COLOR_HITBOX_DEBUG, COLOR_HIT_FLASH,
    COLOR_HUD_BG, COLOR_HUD_BORDER, COLOR_HUD_P1, COLOR_HUD_P2,
    COLOR_SHIELD, COLOR_TEXT, COLOR_TEXT_DIM,
    HEART_CHAR, WINDOW_HEIGHT, WINDOW_WIDTH,
)
from fighter import Fighter
from game_platform import Platform
from particle import ParticleSystem
from snow import SnowParticle


class TitleScreenView(arcade.View):
    def __init__(self):
        super().__init__()
        self.snow = [SnowParticle(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(120)]
        self.background = Background()
        self.selected_option = 0
        self.options = ["START BATTLE", "CONTROLS", "QUIT"]

    def on_update(self, dt):
        self.background.update(dt)
        for flake in self.snow: flake.update(WINDOW_WIDTH, WINDOW_HEIGHT)

    def on_draw(self):
        self.clear()
        self.background.draw()
        for flake in self.snow: flake.draw()

        draw_text("X-MASS-FIGHT", WINDOW_WIDTH / 2, WINDOW_HEIGHT * 0.68, COLOR_GOLD, 84, anchor_x="center", bold=True)
        draw_text("HOLIDAY BRAWL - ULTIMATE EDITION", WINDOW_WIDTH / 2, WINDOW_HEIGHT * 0.58, COLOR_TEXT, 28, anchor_x="center")

        for i, opt in enumerate(self.options):
            col = COLOR_GOLD if i == self.selected_option else COLOR_TEXT_DIM
            scale_text = f"> {opt} <" if i == self.selected_option else opt
            draw_text(scale_text, WINDOW_WIDTH / 2, WINDOW_HEIGHT * 0.38 - i * 65, col, 32, anchor_x="center", bold=(i == self.selected_option))

        draw_text("Press ENTER / SPACE to Select  |  W/S or Up/Down to Navigate", WINDOW_WIDTH / 2, 60, COLOR_TEXT_DIM, 18, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.UP, arcade.key.W):
            self.selected_option = (self.selected_option - 1) % len(self.options)
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.selected_option = (self.selected_option + 1) % len(self.options)
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            if self.selected_option == 0: self.window.show_view(XMassFightView())
            elif self.selected_option == 1: self.window.show_view(ControlsView())
            elif self.selected_option == 2: arcade.exit()


class ControlsView(arcade.View):
    def __init__(self):
        super().__init__()
        self.snow = [SnowParticle(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(80)]
        self.background = Background()

    def on_update(self, dt):
        self.background.update(dt)
        for flake in self.snow: flake.update(WINDOW_WIDTH, WINDOW_HEIGHT)

    def on_draw(self):
        self.clear()
        self.background.draw()
        for flake in self.snow: flake.draw()

        draw_text("CONTROLS & HOW TO PLAY", WINDOW_WIDTH / 2, WINDOW_HEIGHT * 0.82, COLOR_GOLD, 48, anchor_x="center", bold=True)

        box_w, box_h = 780, 440
        draw_filled_rectangle(WINDOW_WIDTH * 0.30, WINDOW_HEIGHT * 0.48, box_w, box_h, COLOR_HUD_BG)
        draw_rectangle_outline(WINDOW_WIDTH * 0.30, WINDOW_HEIGHT * 0.48, box_w, box_h, COLOR_HUD_P1, 3)

        draw_text("PLAYER 1 CONTROLS", WINDOW_WIDTH * 0.30, WINDOW_HEIGHT * 0.65, COLOR_HUD_P1, 24, anchor_x="center", bold=True)
        p1_text = (
            "Move: A / D\n"
            "Jump: W or Space\n"
            "Crouch: S\n"
            "Attack: F\n"
            "Heavy Charge: Hold G (White -> Red -> Blue)\n"
            "Shield: E\n"
            "Pass Platform: S + Jump"
        )
        draw_text(p1_text, WINDOW_WIDTH * 0.30 - 350, WINDOW_HEIGHT * 0.54, COLOR_TEXT, 17)

        draw_filled_rectangle(WINDOW_WIDTH * 0.70, WINDOW_HEIGHT * 0.48, box_w, box_h, COLOR_HUD_BG)
        draw_rectangle_outline(WINDOW_WIDTH * 0.70, WINDOW_HEIGHT * 0.48, box_w, box_h, COLOR_HUD_P2, 3)

        draw_text("PLAYER 2 CONTROLS", WINDOW_WIDTH * 0.70, WINDOW_HEIGHT * 0.65, COLOR_HUD_P2, 24, anchor_x="center", bold=True)
        p2_text = (
            "Move: Left / Right Arrows\n"
            "Jump: Up Arrow or RShift\n"
            "Crouch: Down Arrow\n"
            "Attack: Enter\n"
            "Heavy Charge: Hold . (Period) or RShift\n"
            "Shield: / (Slash)\n"
            "Pass Platform: Down + Jump"
        )
        draw_text(p2_text, WINDOW_WIDTH * 0.70 - 350, WINDOW_HEIGHT * 0.54, COLOR_TEXT, 17)

        draw_text("Press ESC to return to Title", WINDOW_WIDTH / 2, 50, COLOR_TEXT_DIM, 20, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE: self.window.show_view(TitleScreenView())


class XMassFightView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = COLOR_BG_TOP
        self.setup()

    def setup(self):
        self.p1 = Fighter(WINDOW_WIDTH * 0.30, 400, "Player 1", COLOR_HUD_P1, facing=1)
        self.p2 = Fighter(WINDOW_WIDTH * 0.70, 400, "Player 2", COLOR_HUD_P2, facing=-1)

        self.platforms = [
            Platform(WINDOW_WIDTH / 2,       140, 1100, 50, pass_through=False),
            Platform(WINDOW_WIDTH * 0.22,    330,  340, 22, pass_through=True),
            Platform(WINDOW_WIDTH * 0.78,    330,  340, 22, pass_through=True),
            Platform(WINDOW_WIDTH / 2,       500,  400, 22, pass_through=True),
            Platform(WINDOW_WIDTH / 2,       670,  240, 22, pass_through=True),
        ]

        self.snow = [SnowParticle(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(100)]
        self.particles = ParticleSystem()
        self.background = Background()

        self.accumulator = 0.0
        self.screen_shake = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0
        self.hitstop_timer = 0

        self.intro_timer = 120
        self.game_state = "INTRO"
        self.is_paused = False
        self.game_over_text = None
        self.game_over_subtext = None

    def on_update(self, delta_time):
        delta_time = min(delta_time, MAX_FRAME_TIME)
        if self.is_paused or self.game_state == "OVER": return

        self.background.update(delta_time)
        for flake in self.snow: flake.update(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.particles.update()

        if self.screen_shake > 0:
            self.shake_offset_x = random.uniform(-self.screen_shake, self.screen_shake)
            self.shake_offset_y = random.uniform(-self.screen_shake, self.screen_shake)
            self.screen_shake = max(0.0, self.screen_shake - delta_time * 65)
        else:
            self.shake_offset_x, self.shake_offset_y = 0.0, 0.0

        self.accumulator += delta_time
        steps = 0
        while self.accumulator >= PHYSICS_STEP and steps < MAX_STEPS_PER_FRAME:
            self.accumulator -= PHYSICS_STEP
            self._game_step()
            steps += 1

        self._handle_blast_zones()

    def _game_step(self):
        if self.game_state == "INTRO":
            self.intro_timer -= 1
            if self.intro_timer <= 0: self.game_state = "PLAYING"
            return

        if self.hitstop_timer > 0:
            self.hitstop_timer -= 1
            for f in (self.p1, self.p2):
                if f.hit_flash_timer > 0:
                    f.hit_flash_timer -= 1
                    if f.hit_flash_timer == 0: f.color = f.base_color
            return

        self.p1.update_physics(self.platforms)
        self.p2.update_physics(self.platforms)

        for f in (self.p1, self.p2):
            if f.just_landed: self.particles.emit_land(f.center_x, f.bottom)
            if f.just_jumped: self.particles.emit_jump(f.center_x, f.bottom)
            if f.just_double_jumped: self.particles.emit_sparkle(f.center_x, f.bottom)

        self.p1.update_animation(PHYSICS_STEP)
        self.p2.update_animation(PHYSICS_STEP)

        self._check_attack_collisions(self.p1, self.p2)
        self._check_attack_collisions(self.p2, self.p1)

    def _check_attack_collisions(self, attacker, defender):
        if not attacker.attack_hitbox or attacker.attack_has_hit: return
        if defender.invincible_timer > 0 or self.game_state != "PLAYING": return

        hx, hy, hw, hh = attacker.attack_hitbox
        if not (defender.right > hx and defender.left < hx + hw and defender.top > hy and defender.bottom < hy + hh):
            return

        if defender.is_shielding and defender.shield_stun_timer == 0:
            attacker.attack_has_hit = True
            attacker.attack_hitbox = None
            defender.shield_health = max(0.0, defender.shield_health - 18.0)
            self.particles.emit_sparkle(defender.center_x, defender.center_y, count=8, color=(100, 180, 255, 255))
            if defender.shield_health <= 0:
                defender.shield_stun_timer = 100
                defender.is_shielding = False
                self.screen_shake = 15.0
            return

        attack_damage = attacker.get_current_attack_damage()
        defender.damage += attack_damage
        scale = 1.0 + defender.damage * KNOCKBACK_DAMAGE_SCALE
        direction = 1 if attacker.facing_right else -1

        is_heavy = (attacker.attack_state == "ATTACK_HEAVY")
        is_meteor = (attacker.attack_state == "ATTACK_DOWN")

        if is_heavy:
            mult = attacker.charge_power_multiplier
            defender.change_x = BASE_KNOCKBACK_X * scale * 1.8 * mult * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 1.5 * mult
        elif is_meteor:
            defender.change_x = BASE_KNOCKBACK_X * scale * 0.4 * direction
            defender.change_y = -BASE_KNOCKBACK_Y * scale * 1.8
        else:
            defender.change_x = BASE_KNOCKBACK_X * scale * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale

        defender.hitstun_timer = int(HITSTUN_BASE * scale * (1.5 if is_heavy else 1.0))
        defender.is_grounded = False
        defender.invincible_timer = INVINCIBLE_HIT_FRAMES

        self.hitstop_timer = HITSTOP_FRAMES + (4 if is_heavy else 0)
        defender.hit_flash_timer = 6
        defender.color = COLOR_HIT_FLASH
        self.screen_shake = 22.0 if is_heavy else (16.0 if is_meteor else 12.0)

        contact_x = defender.left if attacker.facing_right else defender.right
        self.particles.emit_hit(contact_x, defender.center_y, direction, is_meteor=is_meteor)

        attacker.attack_has_hit = True
        attacker.attack_hitbox = None

    def _is_out(self, p):
        return (p.center_y < -BLAST_ZONE or p.center_y > WINDOW_HEIGHT + BLAST_ZONE or
                p.center_x < -BLAST_ZONE or p.center_x > WINDOW_WIDTH + BLAST_ZONE)

    def _handle_blast_zones(self):
        if self.game_state != "PLAYING" or self.hitstop_timer > 0: return

        p1_out, p2_out = self._is_out(self.p1), self._is_out(self.p2)
        if p1_out and p2_out:
            self.p1.stocks -= 1
            self.p2.stocks -= 1
            self.particles.emit_ko(self.p1.center_x, self.p1.center_y)
            self.particles.emit_ko(self.p2.center_x, self.p2.center_y)
            self.screen_shake = 25.0
            if self.p1.stocks <= 0 and self.p2.stocks <= 0: self._end_game("DRAW", "No survivors.")
            elif self.p1.stocks <= 0: self._end_game("PLAYER 2 WINS", "Flawless triumph.")
            else: self._end_game("PLAYER 1 WINS", "Flawless triumph.")
            return

        if p1_out: self._single_ko(self.p1, self.p2)
        elif p2_out: self._single_ko(self.p2, self.p1)

    def _single_ko(self, victim, survivor):
        victim.stocks -= 1
        self.particles.emit_ko(victim.center_x, victim.center_y)
        self.screen_shake = 22.0
        if victim.stocks <= 0:
            self._end_game(f"{survivor.player_name.upper()} WINS", "Winter champion crowned.")
            return
        self._respawn(victim)

    def _respawn(self, player):
        x = WINDOW_WIDTH * 0.30 if player is self.p1 else WINDOW_WIDTH * 0.70
        player.reset_after_ko(x, 520)
        self.particles.emit_sparkle(player.center_x, player.center_y, count=25)

    def _end_game(self, title, subtext):
        self.game_over_text = title
        self.game_over_subtext = subtext
        self.game_state = "OVER"

    def _apply_shake_viewport(self):
        sx, sy = self.shake_offset_x, self.shake_offset_y
        try: arcade.set_viewport(-sx, WINDOW_WIDTH - sx, -sy, WINDOW_HEIGHT - sy)
        except Exception: pass

    def _clear_shake_viewport(self):
        try: arcade.set_viewport(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        except Exception: pass

    def on_draw(self):
        self.clear()
        self.background.draw()

        self._apply_shake_viewport()
        try:
            for flake in self.snow: flake.draw()
            for platform in self.platforms: platform.draw()

            # Shields
            for p in (self.p1, self.p2):
                if p.is_shielding:
                    arcade.draw_circle_filled(p.center_x, p.center_y, 55, COLOR_SHIELD)
                    arcade.draw_circle_outline(p.center_x, p.center_y, 55, (150, 210, 255, 220), 3)

            draw_sprite(self.p1)
            draw_sprite(self.p2)

            self._draw_charge_effects()
            self._draw_attack_effects()
            self.particles.draw()

            if DEBUG_HITBOXES:
                for f in (self.p1, self.p2):
                    if f.attack_hitbox:
                        x, y, w, h = f.attack_hitbox
                        draw_rectangle_outline(x + w / 2, y + h / 2, w, h, COLOR_HITBOX_DEBUG, 2)
        finally:
            self._clear_shake_viewport()

        self._draw_hud()
        self._draw_intro()
        self._draw_pause_menu()
        self._draw_game_over()

    def _draw_charge_effects(self):
        """Draws 2-frame charge lightning animation at the character's feet (white -> red -> blue) with appropriate scale."""
        for fighter in (self.p1, self.p2):
            if not fighter.is_charging:
                continue

            ratio = fighter.charge_timer / fighter.max_charge_frames
            if ratio < 0.35:
                stage = "WHITE"
            elif ratio < 0.75:
                stage = "RED"
            else:
                stage = "BLUE"

            frames = fighter.attack_animations_right.get(f"CHARGE_{stage}", [])
            if not frames:
                continue

            frame_idx = (fighter.charge_timer // 8) % len(frames)
            tex = frames[frame_idx]

            # Position at the front of the character's feet with clean proportional scaling
            feet_x = fighter.center_x + (22 if fighter.facing_right else -22)
            feet_y = fighter.bottom + 14

            draw_texture_rectangle(feet_x, feet_y, 56, 56, tex)

    def _draw_attack_effects(self):
        for fighter in (self.p1, self.p2):
            if not fighter.is_attacking: continue
            anim_set = fighter.attack_animations_right if fighter.facing_right else fighter.attack_animations_left
            frames = anim_set.get(fighter.attack_state, anim_set["ATTACK_SIDE"])
            idx = min(fighter.attack_texture_index, len(frames) - 1)
            tex = frames[idx]

            if fighter.attack_state == "ATTACK_UP":
                hx, hy = fighter.center_x, fighter.center_y + fighter.BODY_H / 2 + 25
            elif fighter.attack_state == "ATTACK_DOWN":
                hx, hy = fighter.center_x, fighter.center_y - fighter.BODY_H / 2 - 25
            else:
                hx = fighter.center_x + (ATTACK_REACH if fighter.facing_right else -ATTACK_REACH)
                hy = fighter.center_y

            draw_texture_rectangle(hx, hy, 84, 84, tex)

    def _draw_hud(self):
        self._draw_player_hud(self.p1, "PLAYER 1", COLOR_HUD_P1, left=True)
        self._draw_player_hud(self.p2, "PLAYER 2", COLOR_HUD_P2, left=False)
        self._draw_legend()

    def _draw_player_hud(self, player, label, accent, left):
        pw, ph = 420, 140
        cx = pw / 2 + 25 if left else WINDOW_WIDTH - pw / 2 - 25
        cy = ph / 2 + 25

        draw_filled_rectangle(cx, cy, pw, ph, COLOR_HUD_BG)
        draw_rectangle_outline(cx, cy, pw, ph, accent, 4)

        inner_l = cx - pw / 2 + 25
        inner_r = cx + pw / 2 - 25
        top_y = cy + ph / 2 - 28
        mid_y = cy - 5

        dmg = int(player.damage)
        if dmg < 50: dmg_col = (140, 235, 140, 255)
        elif dmg < 100: dmg_col = (240, 220, 100, 255)
        elif dmg < 150: dmg_col = (250, 160, 80, 255)
        else: dmg_col = (255, 75, 75, 255)

        hearts = (HEART_CHAR + " ") * player.stocks

        if left:
            draw_text(label, inner_l, top_y, accent, 18, bold=True)
            draw_text("STOCKS", inner_r, top_y, COLOR_TEXT_DIM, 11, anchor_x="right")
            draw_text(hearts, inner_r, mid_y, COLOR_GOLD, 24, anchor_x="right", bold=True)
            draw_text(f"{dmg}%", inner_l, mid_y - 2, dmg_col, 32, bold=True)
        else:
            draw_text(label, inner_r, top_y, accent, 18, anchor_x="right", bold=True)
            draw_text("STOCKS", inner_l, top_y, COLOR_TEXT_DIM, 11)
            draw_text(hearts, inner_l, mid_y, COLOR_GOLD, 24, bold=True)
            draw_text(f"{dmg}%", inner_r, mid_y - 2, dmg_col, 32, anchor_x="right", bold=True)

        bar_w = pw - 50
        bar_x = cx
        bar_y = cy - ph / 2 + 16
        pct = max(0.0, player.shield_health / 100.0)
        draw_filled_rectangle(bar_x, bar_y, bar_w, 8, (40, 45, 60, 255))
        draw_filled_rectangle(bar_x - bar_w / 2 + (bar_w * pct) / 2, bar_y, bar_w * pct, 8, (100, 180, 255, 255))
        draw_rectangle_outline(bar_x, bar_y, bar_w, 8, (150, 200, 255, 200), 1)

    def _draw_legend(self):
        bar_y = WINDOW_HEIGHT - 36
        draw_filled_rectangle(WINDOW_WIDTH / 2, bar_y, WINDOW_WIDTH - 60, 48, (10, 12, 22, 190))
        draw_rectangle_outline(WINDOW_WIDTH / 2, bar_y, WINDOW_WIDTH - 60, 48, COLOR_HUD_BORDER, 2)
        draw_text("P1: A/D Move | W/Space Jump | S Crouch | F Attack | Hold G Heavy | E Shield", 40, bar_y - 5, COLOR_TEXT, 13)
        draw_text("P2: Left/Right Move | Up/RShift Jump | Down Crouch | Enter Attack | Hold . Heavy | / Shield", WINDOW_WIDTH - 40, bar_y - 5, COLOR_TEXT, 13, anchor_x="right")

    def _draw_intro(self):
        if self.game_state != "INTRO": return
        text = "3" if self.intro_timer > 80 else ("2" if self.intro_timer > 45 else ("1" if self.intro_timer > 15 else "FIGHT!"))
        draw_text(text, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, COLOR_GOLD, 130, anchor_x="center", bold=True)

    def _draw_pause_menu(self):
        if not self.is_paused: return
        draw_filled_rectangle(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 170))
        draw_text("PAUSED", WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 60, COLOR_GOLD, 64, anchor_x="center", bold=True)
        draw_text("Press ESC to Resume  |  Press R to Restart  |  Press Q to Quit to Menu", WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 20, COLOR_TEXT, 22, anchor_x="center")

    def _draw_game_over(self):
        if self.game_state != "OVER": return
        draw_filled_rectangle(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 180))
        draw_text(self.game_over_text, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 60, COLOR_GOLD, 64, anchor_x="center", bold=True)
        if self.game_over_subtext:
            draw_text(self.game_over_subtext, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2, COLOR_TEXT, 24, anchor_x="center")
        draw_text("Press R to Restart  |  Press Q for Main Menu", WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 90, COLOR_TEXT_DIM, 20, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            if self.game_state == "PLAYING": self.is_paused = not self.is_paused
            return

        if self.is_paused:
            if key == arcade.key.R: self.setup()
            elif key == arcade.key.Q: self.window.show_view(TitleScreenView())
            return

        if self.game_state == "OVER":
            if key == arcade.key.R: self.setup()
            elif key == arcade.key.Q: self.window.show_view(TitleScreenView())
            return

        # P1 Controls
        if key == arcade.key.A: self.p1.move_left = True
        elif key == arcade.key.D: self.p1.move_right = True
        elif key == arcade.key.S: self.p1.crouching = True
        elif key in (arcade.key.SPACE, arcade.key.W):
            self.p1.jump_pressed = True
            self.p1.jump_held = True
        elif key == arcade.key.F: self.p1.attack_pressed = True
        elif key == arcade.key.G:
            self.p1.charge_pressed = True
            self.p1.charge_held = True
        elif key == arcade.key.E: self.p1.is_shielding = True

        # P2 Controls
        elif key == arcade.key.LEFT: self.p2.move_left = True
        elif key == arcade.key.RIGHT: self.p2.move_right = True
        elif key == arcade.key.DOWN: self.p2.crouching = True
        elif key in (arcade.key.UP, arcade.key.RSHIFT):
            self.p2.jump_pressed = True
            self.p2.jump_held = True
        elif key == arcade.key.ENTER: self.p2.attack_pressed = True
        elif key == arcade.key.PERIOD:
            self.p2.charge_pressed = True
            self.p2.charge_held = True
        elif key == arcade.key.SLASH: self.p2.is_shielding = True

    def on_key_release(self, key, modifiers):
        # P1 Controls
        if key == arcade.key.A: self.p1.move_left = False
        elif key == arcade.key.D: self.p1.move_right = False
        elif key == arcade.key.S: self.p1.crouching = False
        elif key in (arcade.key.SPACE, arcade.key.W):
            self.p1.jump_pressed = False
            self.p1.jump_held = False
        elif key == arcade.key.G: self.p1.charge_held = False
        elif key == arcade.key.E: self.p1.is_shielding = False

        # P2 Controls
        elif key == arcade.key.LEFT: self.p2.move_left = False
        elif key == arcade.key.RIGHT: self.p2.move_right = False
        elif key == arcade.key.DOWN: self.p2.crouching = False
        elif key in (arcade.key.UP, arcade.key.RSHIFT):
            self.p2.jump_pressed = False
            self.p2.jump_held = False
        elif key == arcade.key.PERIOD: self.p2.charge_held = False
        elif key == arcade.key.SLASH: self.p2.is_shielding = False