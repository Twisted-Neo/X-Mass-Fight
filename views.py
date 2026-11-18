"""Arcade 3.x Views: TitleView, ControlsView, and FightView with Camera2D screen shake."""

import math
import random
import arcade

from config import (
    ATTACK_REACH, BASE_KNOCKBACK_X, BASE_KNOCKBACK_Y, BLAST_ZONE,
    COLOR_GOLD, COLOR_HITBOX_DEBUG, COLOR_HIT_FLASH, COLOR_HUD_BG,
    COLOR_HUD_P1, COLOR_HUD_P2, COLOR_SHIELD, COLOR_SHIELD_RIM,
    COLOR_TEXT, COLOR_TEXT_DIM, DEBUG_HITBOXES,
    HITSTOP_FRAMES, HITSTUN_BASE, HIT_FLASH_FRAMES, INVINCIBLE_HIT_FRAMES,
    KNOCKBACK_DAMAGE_SCALE, LAUNCH_SPEED_THRESHOLD, MAX_CHARGE_FRAMES,
    MAX_FRAME_TIME, MAX_STEPS_PER_FRAME, PHYSICS_STEP,
    SIDE_COMBO_KB_MULT, WINDOW_HEIGHT, WINDOW_WIDTH,
)
from effects import EffectSystem
from fighter import Fighter
from hud import MatchHUD
from stage import HolidayStage


class TitleView(arcade.View):
    def __init__(self):
        super().__init__()
        self.stage = HolidayStage(include_platforms=False, snow_count=130)
        self.options = ["START BATTLE", "CONTROLS", "QUIT"]
        self.selected = 0

        self.title_lbl = arcade.Text(
            "X-MASS-FIGHT", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.68, COLOR_GOLD,
            font_size=84, anchor_x="center", bold=True,
        )
        self.sub_lbl = arcade.Text(
            "HOLIDAY BRAWL - ULTIMATE EDITION", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.58, COLOR_TEXT,
            font_size=28, anchor_x="center",
        )
        self.hint_lbl = arcade.Text(
            "W/S or Up/Down: Navigate   |   Enter / Space: Select",
            WINDOW_WIDTH * 0.5, 60, COLOR_TEXT_DIM, font_size=18, anchor_x="center",
        )
        self.option_lbls = [
            arcade.Text(opt, WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.39 - i * 68, COLOR_TEXT_DIM, 32, anchor_x="center")
            for i, opt in enumerate(self.options)
        ]
        self._refresh_menu_labels()

    def _refresh_menu_labels(self):
        for i, lbl in enumerate(self.option_lbls):
            active = i == self.selected
            lbl.text = f"> {self.options[i]} <" if active else self.options[i]
            lbl.color = COLOR_GOLD if active else COLOR_TEXT_DIM
            lbl.bold = active

    def on_update(self, delta_time: float):
        self.stage.update(min(delta_time, MAX_FRAME_TIME))

    def on_draw(self):
        self.clear()
        self.stage.draw_backdrop()
        self.stage.draw_foreground()
        self.title_lbl.draw()
        self.sub_lbl.draw()
        for lbl in self.option_lbls:
            lbl.draw()
        self.hint_lbl.draw()

    def on_key_press(self, key: int, modifiers: int):
        if key in (arcade.key.UP, arcade.key.W):
            self.selected = (self.selected - 1) % len(self.options)
            self._refresh_menu_labels()
        elif key in (arcade.key.DOWN, arcade.key.S):
            self.selected = (self.selected + 1) % len(self.options)
            self._refresh_menu_labels()
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            if self.selected == 0:
                self.window.show_view(FightView())
            elif self.selected == 1:
                self.window.show_view(ControlsView())
            else:
                arcade.exit()


class ControlsView(arcade.View):
    def __init__(self):
        super().__init__()
        self.stage = HolidayStage(include_platforms=False, snow_count=90)
        self.header = arcade.Text(
            "CONTROLS & MECHANICS", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.83, COLOR_GOLD,
            font_size=48, anchor_x="center", bold=True,
        )
        self.p1_head = arcade.Text("PLAYER 1", WINDOW_WIDTH * 0.30, WINDOW_HEIGHT * 0.66, COLOR_HUD_P1, 26, anchor_x="center", bold=True)
        self.p1_body = arcade.Text(
            "Move: A / D\n"
            "Jump / Double Jump: W or Space (Tap for Short Hop)\n"
            "Crouch / Fast Fall: S\n"
            "Drop Through Platform: S + Jump\n"
            "Side Attack (2-Hit Combo): F -> F\n"
            "Up Slash / Air Meteor: W + F  |  S + F (Air)\n"
            "Heavy Smash Charge: Hold G  (White -> Red -> Blue)\n"
            "Shield: E",
            WINDOW_WIDTH * 0.30 - 340, WINDOW_HEIGHT * 0.56, COLOR_TEXT, 16, multiline=True, width=680,
        )
        self.p2_head = arcade.Text("PLAYER 2", WINDOW_WIDTH * 0.70, WINDOW_HEIGHT * 0.66, COLOR_HUD_P2, 26, anchor_x="center", bold=True)
        self.p2_body = arcade.Text(
            "Move: Left / Right Arrows\n"
            "Jump / Double Jump: Up Arrow or RShift (Tap for Short Hop)\n"
            "Crouch / Fast Fall: Down Arrow\n"
            "Drop Through Platform: Down + Jump\n"
            "Side Attack (2-Hit Combo): - -> -\n"
            "Up Slash / Air Meteor: Up + -  |  Down + - (Air)\n"
            "Heavy Smash Charge: Hold .  (White -> Red -> Blue)\n"
            "Shield: ,",
            WINDOW_WIDTH * 0.70 - 340, WINDOW_HEIGHT * 0.56, COLOR_TEXT, 16, multiline=True, width=680,
        )
        self.footer = arcade.Text("Press ESC or ENTER to return", WINDOW_WIDTH * 0.5, 55, COLOR_TEXT_DIM, 20, anchor_x="center")

    def on_update(self, delta_time: float):
        self.stage.update(min(delta_time, MAX_FRAME_TIME))

    def on_draw(self):
        self.clear()
        self.stage.draw_backdrop()
        self.stage.draw_foreground()
        self.header.draw()

        for cx, accent in ((WINDOW_WIDTH * 0.30, COLOR_HUD_P1), (WINDOW_WIDTH * 0.70, COLOR_HUD_P2)):
            arcade.draw_rect_filled(arcade.XYWH(cx, WINDOW_HEIGHT * 0.48, 760, 440), COLOR_HUD_BG)
            arcade.draw_rect_outline(arcade.XYWH(cx, WINDOW_HEIGHT * 0.48, 760, 440), accent, border_width=3)

        self.p1_head.draw()
        self.p1_body.draw()
        self.p2_head.draw()
        self.p2_body.draw()
        self.footer.draw()

    def on_key_press(self, key: int, modifiers: int):
        if key in (arcade.key.ESCAPE, arcade.key.ENTER, arcade.key.SPACE):
            self.window.show_view(TitleView())


class FightView(arcade.View):
    def __init__(self):
        super().__init__()
        self.world_camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()
        self.hud = MatchHUD()
        self.setup()

    def setup(self):
        self.stage = HolidayStage(include_platforms=True, snow_count=100)
        self.effects = EffectSystem()

        self.p1 = Fighter(WINDOW_WIDTH * 0.30, 400, "Player 1", COLOR_HUD_P1, facing=1)
        self.p2 = Fighter(WINDOW_WIDTH * 0.70, 400, "Player 2", COLOR_HUD_P2, facing=-1)

        self.fighter_sprites = arcade.SpriteList()
        self.fighter_sprites.append(self.p1)
        self.fighter_sprites.append(self.p2)

        self.accumulator = 0.0
        self.screen_shake = 0.0
        self.hitstop_timer = 0
        self.intro_timer = 115
        self.game_state = "INTRO"
        self.is_paused = False
        self.game_over_title = ""
        self.game_over_sub = ""

    def on_update(self, delta_time: float):
        dt = min(delta_time, MAX_FRAME_TIME)
        if self.is_paused or self.game_state == "OVER":
            return

        self.stage.update(dt)
        self.effects.update()

        if self.screen_shake > 0:
            self.screen_shake = max(0.0, self.screen_shake - dt * 65.0)
            sx = random.uniform(-self.screen_shake, self.screen_shake)
            sy = random.uniform(-self.screen_shake, self.screen_shake)
            self.world_camera.position = (WINDOW_WIDTH * 0.5 + sx, WINDOW_HEIGHT * 0.5 + sy)
        else:
            self.world_camera.position = (WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5)

        self.accumulator += dt
        steps = 0
        while self.accumulator >= PHYSICS_STEP and steps < MAX_STEPS_PER_FRAME:
            self.accumulator -= PHYSICS_STEP
            self._fixed_step()
            steps += 1

        self._check_blast_zones()

    def _fixed_step(self):
        if self.game_state == "INTRO":
            self.intro_timer -= 1
            if self.intro_timer <= 0:
                self.game_state = "PLAYING"
            return

        if self.hitstop_timer > 0:
            self.hitstop_timer -= 1
            for f in (self.p1, self.p2):
                if f.hit_flash_timer > 0:
                    f.hit_flash_timer -= 1
                    if f.hit_flash_timer == 0:
                        f.color = f.base_color
            return

        self.p1.update_physics(self.stage.platforms)
        self.p2.update_physics(self.stage.platforms)

        for f in (self.p1, self.p2):
            if f.just_landed:
                self.effects.emit_land(f.center_x, f.bottom)
            if f.just_jumped:
                self.effects.emit_jump(f.center_x, f.bottom)
            if f.just_double_jumped:
                self.effects.emit_sparkle(f.center_x, f.bottom)

        self.p1.update_animation(PHYSICS_STEP)
        self.p2.update_animation(PHYSICS_STEP)

        self._resolve_attack(self.p1, self.p2)
        self._resolve_attack(self.p2, self.p1)

    def _resolve_attack(self, attacker: Fighter, defender: Fighter):
        if not attacker.attack_hitbox or attacker.attack_has_hit:
            return
        if defender.invincible_timer > 0 or self.game_state != "PLAYING":
            return

        hx, hy, hw, hh = attacker.attack_hitbox
        if not (defender.right > hx and defender.left < hx + hw and defender.top > hy and defender.bottom < hy + hh):
            return

        # Shield block
        if defender.is_shielding and defender.shield_stun_timer == 0:
            attacker.attack_has_hit = True
            attacker.attack_hitbox = None
            shield_dmg = (
                28.0 if attacker.attack_state == "ATTACK_HEAVY"
                else (24.0 if attacker.attack_state == "ATTACK_SIDE_2" else 18.0)
            )
            defender.shield_health = max(0.0, defender.shield_health - shield_dmg)
            self.effects.emit_sparkle(defender.center_x, defender.center_y, count=10, color=(110, 195, 255, 255))
            if defender.shield_health <= 0:
                defender.shield_stun_timer = 110
                defender.is_shielding = False
                self.screen_shake = 16.0
                self.effects.emit_shield_break(defender.center_x, defender.center_y)
            return

        # Direct hit
        dmg = attacker.get_current_attack_damage()
        defender.damage += dmg
        scale = 1.0 + defender.damage * KNOCKBACK_DAMAGE_SCALE
        direction = 1 if attacker.facing_right else -1

        is_heavy = attacker.attack_state == "ATTACK_HEAVY"
        is_meteor = attacker.attack_state == "ATTACK_DOWN"
        is_up = attacker.attack_state == "ATTACK_UP"
        is_side_2 = attacker.attack_state == "ATTACK_SIDE_2"

        if is_heavy:
            mult = attacker.charge_power_multiplier
            defender.change_x = BASE_KNOCKBACK_X * scale * 1.85 * mult * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 1.45 * mult
        elif is_side_2:
            defender.change_x = BASE_KNOCKBACK_X * scale * SIDE_COMBO_KB_MULT * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 1.25
        elif is_meteor:
            defender.change_x = BASE_KNOCKBACK_X * scale * 0.45 * direction
            defender.change_y = -BASE_KNOCKBACK_Y * scale * 1.85
        elif is_up:
            defender.change_x = BASE_KNOCKBACK_X * scale * 0.35 * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 1.55
        else:
            defender.change_x = BASE_KNOCKBACK_X * scale * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 0.95

        defender.hitstun_timer = int(HITSTUN_BASE * scale * (1.45 if is_heavy else (1.25 if is_side_2 else 1.0)))
        defender.is_grounded = False
        defender.invincible_timer = INVINCIBLE_HIT_FRAMES
        defender.hit_flash_timer = HIT_FLASH_FRAMES
        defender.color = COLOR_HIT_FLASH

        # Trigger 3-stage Xteve-Launch animation with damage-scaled control lockout
        launch_speed = math.hypot(defender.change_x, defender.change_y)
        if is_heavy or is_meteor or is_side_2 or launch_speed >= LAUNCH_SPEED_THRESHOLD:
            defender.start_launch(dmg)

        self.hitstop_timer = HITSTOP_FRAMES + (4 if is_heavy else (2 if is_side_2 else 0))
        self.screen_shake = 22.0 if is_heavy else (16.0 if (is_meteor or is_side_2) else 11.0)

        contact_x = defender.left if attacker.facing_right else defender.right
        self.effects.emit_hit(contact_x, defender.center_y, direction, is_meteor=is_meteor, is_heavy=(is_heavy or is_side_2))

        attacker.attack_has_hit = True
        attacker.attack_hitbox = None

    def _is_in_blast_zone(self, f: Fighter) -> bool:
        return (
            f.center_y < -BLAST_ZONE
            or f.center_y > WINDOW_HEIGHT + BLAST_ZONE
            or f.center_x < -BLAST_ZONE
            or f.center_x > WINDOW_WIDTH + BLAST_ZONE
        )

    def _check_blast_zones(self):
        if self.game_state != "PLAYING" or self.hitstop_timer > 0:
            return

        p1_ko = self._is_in_blast_zone(self.p1)
        p2_ko = self._is_in_blast_zone(self.p2)

        if p1_ko and p2_ko:
            self.p1.stocks -= 1
            self.p2.stocks -= 1
            self.effects.emit_ko(self.p1.center_x, self.p1.center_y)
            self.effects.emit_ko(self.p2.center_x, self.p2.center_y)
            self.screen_shake = 25.0
            if self.p1.stocks <= 0 and self.p2.stocks <= 0:
                self._end_match("DRAW", "Double knockout!")
            elif self.p1.stocks <= 0:
                self._end_match("PLAYER 2 WINS", "Winter champion crowned.")
            else:
                self._end_match("PLAYER 1 WINS", "Winter champion crowned.")
            return

        if p1_ko:
            self._handle_single_ko(self.p1, self.p2)
        elif p2_ko:
            self._handle_single_ko(self.p2, self.p1)

    def _handle_single_ko(self, victim: Fighter, survivor: Fighter):
        victim.stocks -= 1
        self.effects.emit_ko(victim.center_x, victim.center_y)
        self.screen_shake = 22.0
        if victim.stocks <= 0:
            self._end_match(f"{survivor.player_name.upper()} WINS", "Winter champion crowned.")
        else:
            spawn_x = WINDOW_WIDTH * 0.30 if victim is self.p1 else WINDOW_WIDTH * 0.70
            victim.reset_after_ko(spawn_x, 540)
            self.effects.emit_sparkle(victim.center_x, victim.center_y, count=24)

    def _end_match(self, title: str, sub: str):
        self.game_over_title = title
        self.game_over_sub = sub
        self.game_state = "OVER"

    def on_draw(self):
        self.clear()

        with self.world_camera.activate():
            self.stage.draw_backdrop()
            self.stage.draw_foreground()

            # Charge-up lightning renders BEHIND the characters
            self._draw_charge_vfx()

            # Shields
            for f in (self.p1, self.p2):
                if f.is_shielding:
                    radius = 52 * (0.55 + 0.45 * (f.shield_health / 100.0))
                    arcade.draw_circle_filled(f.center_x, f.center_y, radius, COLOR_SHIELD)
                    arcade.draw_circle_outline(f.center_x, f.center_y, radius, COLOR_SHIELD_RIM, 3)

            # Crisp pixel-art fighter rendering
            try:
                self.fighter_sprites.draw(pixelated=True)
            except TypeError:
                self.fighter_sprites.draw()

            # Enlarged attack slash VFX renders in front
            self._draw_attack_vfx()
            self.effects.draw()

            if DEBUG_HITBOXES:
                for f in (self.p1, self.p2):
                    if f.attack_hitbox:
                        hx, hy, hw, hh = f.attack_hitbox
                        arcade.draw_rect_outline(arcade.XYWH(hx + hw * 0.5, hy + hh * 0.5, hw, hh), COLOR_HITBOX_DEBUG, 2)

        with self.gui_camera.activate():
            self.hud.draw(
                self.p1, self.p2,
                self.game_state, self.intro_timer, self.is_paused,
                self.game_over_title, self.game_over_sub,
            )

    def _draw_charge_vfx(self):
        for f in (self.p1, self.p2):
            if not f.is_charging:
                continue
            ratio = f.charge_timer / MAX_CHARGE_FRAMES
            stage = "WHITE" if ratio < 0.35 else ("RED" if ratio < 0.75 else "BLUE")
            dkey = "RIGHT" if f.facing_right else "LEFT"
            frames = f.vfx[dkey][f"CHARGE_{stage}"]
            tex = frames[(f.charge_timer // 6) % len(frames)]
            bx = f.center_x + (40 if f.facing_right else -40)
            by = f.center_y + 10
            arcade.draw_texture_rect(tex, arcade.XYWH(bx, by, 86, 86))

    def _draw_attack_vfx(self):
        for f in (self.p1, self.p2):
            if not f.is_attacking:
                continue
            dkey = "RIGHT" if f.facing_right else "LEFT"
            frames = f.vfx[dkey][f.attack_vfx_key]
            tex = frames[min(f.attack_texture_index, len(frames) - 1)]

            if f.attack_state == "ATTACK_UP":
                vx, vy, size = f.center_x, f.center_y + f.body_height * 0.5 + 36, 148
            elif f.attack_state == "ATTACK_DOWN":
                vx, vy, size = f.center_x, f.center_y - f.body_height * 0.5 - 36, 148
            elif f.attack_state == "ATTACK_HEAVY":
                vx = f.center_x + (ATTACK_REACH * 1.15 if f.facing_right else -ATTACK_REACH * 1.15)
                vy, size = f.center_y + 48, 190
            elif f.attack_state == "ATTACK_SIDE_2":
                vx = f.center_x + (ATTACK_REACH * 1.18 if f.facing_right else -ATTACK_REACH * 1.18)
                vy, size = f.center_y + 4, 178
            else:
                vx = f.center_x + (ATTACK_REACH if f.facing_right else -ATTACK_REACH)
                vy, size = f.center_y, 145

            arcade.draw_texture_rect(tex, arcade.XYWH(vx, vy, size, size))

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.ESCAPE and self.game_state == "PLAYING":
            self.is_paused = not self.is_paused
            return

        if self.is_paused or self.game_state == "OVER":
            if key == arcade.key.R:
                self.setup()
            elif key == arcade.key.Q:
                self.window.show_view(TitleView())
            return

        # Player 1
        if key == arcade.key.A:
            self.p1.move_left = True
        elif key == arcade.key.D:
            self.p1.move_right = True
        elif key == arcade.key.W:
            self.p1.up_held = True
            self.p1.jump_pressed = True
            self.p1.jump_held = True
        elif key == arcade.key.SPACE:
            self.p1.jump_pressed = True
            self.p1.jump_held = True
        elif key == arcade.key.S:
            self.p1.crouching = True
        elif key == arcade.key.F:
            self.p1.attack_pressed = True
        elif key == arcade.key.G:
            self.p1.charge_pressed = True
            self.p1.charge_held = True
        elif key == arcade.key.E:
            self.p1.shield_held = True

        # Player 2
        elif key == arcade.key.LEFT:
            self.p2.move_left = True
        elif key == arcade.key.RIGHT:
            self.p2.move_right = True
        elif key == arcade.key.UP:
            self.p2.up_held = True
            self.p2.jump_pressed = True
            self.p2.jump_held = True
        elif key == arcade.key.RSHIFT:
            self.p2.jump_pressed = True
            self.p2.jump_held = True
        elif key == arcade.key.DOWN:
            self.p2.crouching = True
        elif key == arcade.key.MINUS:
            self.p2.attack_pressed = True
        elif key == arcade.key.PERIOD:
            self.p2.charge_pressed = True
            self.p2.charge_held = True
        elif key == arcade.key.COMMA:
            self.p2.shield_held = True

    def on_key_release(self, key: int, modifiers: int):
        # Player 1
        if key == arcade.key.A:
            self.p1.move_left = False
        elif key == arcade.key.D:
            self.p1.move_right = False
        elif key == arcade.key.W:
            self.p1.up_held = False
            self.p1.jump_held = False
        elif key == arcade.key.SPACE:
            self.p1.jump_held = False
        elif key == arcade.key.S:
            self.p1.crouching = False
        elif key == arcade.key.G:
            self.p1.charge_held = False
        elif key == arcade.key.E:
            self.p1.shield_held = False

        # Player 2
        elif key == arcade.key.LEFT:
            self.p2.move_left = False
        elif key == arcade.key.RIGHT:
            self.p2.move_right = False
        elif key == arcade.key.UP:
            self.p2.up_held = False
            self.p2.jump_held = False
        elif key == arcade.key.RSHIFT:
            self.p2.jump_held = False
        elif key == arcade.key.DOWN:
            self.p2.crouching = False
        elif key == arcade.key.PERIOD:
            self.p2.charge_held = False
        elif key == arcade.key.COMMA:
            self.p2.shield_held = False