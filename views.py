"""Arcade 3.x Views: TitleView, SettingsView, CharacterSelectView, ControlsView, and FightView."""

import math
import random
import arcade

import config
from assets import get_fighter_animations
from characters import CHARACTER_ROSTER
from config import (
    ATTACK_REACH, BASE_KNOCKBACK_X, BASE_KNOCKBACK_Y, BOTTOM_BLAST_ZONE,
    CAMERA_LERP_SPEED, CAMERA_MAX_ZOOM, CAMERA_MIN_ZOOM,
    CAMERA_PADDING_X, CAMERA_PADDING_Y, CAMERA_Y_BIAS,
    COLOR_GOLD, COLOR_HITBOX_DEBUG, COLOR_HIT_FLASH, COLOR_HUD_BG,
    COLOR_HUD_P1, COLOR_HUD_P2, COLOR_HURTBOX_DEBUG, COLOR_SHIELD, COLOR_SHIELD_RIM,
    COLOR_TEXT, COLOR_TEXT_DIM, EXTREME_LAUNCH_KO_SPEED,
    FIGHTER_HURTBOX_H, FIGHTER_HURTBOX_W,
    GAME_SET_DELAY_FRAMES, HITSTOP_FRAMES, HITSTUN_BASE, HIT_FLASH_FRAMES,
    IMPACT_FREEZE_FRAMES, INVINCIBLE_HIT_FRAMES,
    KNOCKBACK_DAMAGE_SCALE, KO_RESPAWN_DELAY_FRAMES, LAUNCH_SPEED_THRESHOLD,
    MAX_CHARGE_FRAMES, MAX_FRAME_TIME, MAX_STEPS_PER_FRAME, PHYSICS_STEP,
    SIDE_BLAST_ZONE, SIDE_COMBO_KB_MULT, TOP_BLAST_ZONE,
    WINDOW_HEIGHT, WINDOW_WIDTH,
    WORLD_MAX_X, WORLD_MAX_Y, WORLD_MIN_X, WORLD_MIN_Y,
)
from effects import EffectSystem
from fighter import Fighter
from hud import MatchHUD
from settings import (
    ACTION_SPECS, DISPLAY_MODES, MAX_PRESET_NAME_LEN, SETTINGS,
    get_available_resolutions, key_name,
)
from stage import HolidayStage


class TitleView(arcade.View):
    def __init__(self):
        super().__init__()
        self.stage = HolidayStage(include_platforms=False, snow_count=130)
        self.options = ["START BATTLE", "SETTINGS", "CONTROLS", "QUIT"]
        self.selected = 0

        self.title_lbl = arcade.Text(
            "X-MASS-FIGHT", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.70, COLOR_GOLD,
            font_size=84, anchor_x="center", bold=True,
        )
        self.sub_lbl = arcade.Text(
            "HOLIDAY BRAWL - ULTIMATE EDITION", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.60, COLOR_TEXT,
            font_size=28, anchor_x="center",
        )
        self.hint_lbl = arcade.Text(
            "W/S or Up/Down: Navigate   |   Enter / Space: Select",
            WINDOW_WIDTH * 0.5, 60, COLOR_TEXT_DIM, font_size=18, anchor_x="center",
        )
        self.option_lbls = [
            arcade.Text(opt, WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.43 - i * 64, COLOR_TEXT_DIM, 32, anchor_x="center")
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
        self.window.default_camera.use()
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
            choice = self.options[self.selected]
            if choice == "START BATTLE":
                self.window.show_view(CharacterSelectView())
            elif choice == "SETTINGS":
                self.window.show_view(SettingsView())
            elif choice == "CONTROLS":
                self.window.show_view(ControlsView())
            else:
                arcade.exit()


class SettingsView(arcade.View):
    """Display Mode, Resolution, P1/P2 Keybinds, and Named Control Presets View."""

    def __init__(self, return_view: arcade.View | None = None):
        super().__init__()
        self.return_view = return_view
        self.stage = HolidayStage(include_platforms=False, snow_count=95)

        # Navigation rows:
        # 0: Display Mode
        # 1: Resolution
        # 2: Preset selector (< Preset Name >)
        # 3: Preset actions ([+ SAVE NEW] / [DELETE])
        # 4 .. 4+N-1: Individual action keybinds
        # 4+N: Reset to Defaults
        # 5+N: Save & Back
        self.num_actions = len(ACTION_SPECS)
        self.row_preset_select = 2
        self.row_preset_actions = 3
        self.row_actions_start = 4
        self.row_reset = self.row_actions_start + self.num_actions
        self.row_back = self.row_reset + 1

        self.selected_row = 0
        self.selected_col = 0        # 0 = P1 column, 1 = P2 column
        self.preset_action_idx = 0   # 0 = Save New, 1 = Delete
        self.listening = False

        # Preset naming modal state
        self.naming_player: int | None = None
        self.naming_text: str = ""
        self.naming_is_default: bool = False
        self.cursor_timer: float = 0.0

        self.header = arcade.Text(
            "SETTINGS", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT - 74, COLOR_GOLD,
            font_size=50, anchor_x="center", bold=True,
        )
        self.status_lbl = arcade.Text(
            "Create, load, and save custom control presets — changes save automatically to settings.json",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT - 116, COLOR_TEXT_DIM,
            font_size=16, anchor_x="center",
        )

        # Display panel geometry
        self.disp_box = (WINDOW_WIDTH * 0.5, 868.0, 1560.0, 136.0)
        self.lbl_disp_title = arcade.Text("DISPLAY", 210.0, 908.0, COLOR_GOLD, 18, bold=True)
        self.lbl_mode_name = arcade.Text("Display Mode", 240.0, 868.0, COLOR_TEXT, 20)
        self.lbl_mode_val = arcade.Text("", 1680.0, 868.0, COLOR_GOLD, 20, anchor_x="right", bold=True)
        self.lbl_res_name = arcade.Text("Resolution", 240.0, 822.0, COLOR_TEXT, 20)
        self.lbl_res_val = arcade.Text("", 1680.0, 822.0, COLOR_GOLD, 20, anchor_x="right", bold=True)

        # Controls + Presets panels geometry
        self.p1_box = (WINDOW_WIDTH * 0.295, 472.0, 755.0, 616.0)
        self.p2_box = (WINDOW_WIDTH * 0.705, 472.0, 755.0, 616.0)
        self.lbl_p1_head = arcade.Text("PLAYER 1 CONTROLS", self.p1_box[0], 744.0, COLOR_HUD_P1, 22, anchor_x="center", bold=True)
        self.lbl_p2_head = arcade.Text("PLAYER 2 CONTROLS", self.p2_box[0], 744.0, COLOR_HUD_P2, 22, anchor_x="center", bold=True)

        # Preset selector row (y = 696)
        self.preset_select_y = 696.0
        self.lbl_p1_preset_tag = arcade.Text("Preset", self.p1_box[0] - 335.0, self.preset_select_y, COLOR_TEXT_DIM, 18, bold=True)
        self.lbl_p1_preset_val = arcade.Text("", self.p1_box[0] + 335.0, self.preset_select_y, COLOR_GOLD, 18, anchor_x="right", bold=True)
        self.lbl_p2_preset_tag = arcade.Text("Preset", self.p2_box[0] - 335.0, self.preset_select_y, COLOR_TEXT_DIM, 18, bold=True)
        self.lbl_p2_preset_val = arcade.Text("", self.p2_box[0] + 335.0, self.preset_select_y, COLOR_GOLD, 18, anchor_x="right", bold=True)

        # Preset save/delete button row (y = 650)
        self.preset_btn_y = 650.0
        self.p1_save_box = (self.p1_box[0] - 115.0, self.preset_btn_y, 220.0, 34.0)
        self.p1_del_box = (self.p1_box[0] + 150.0, self.preset_btn_y, 180.0, 34.0)
        self.p2_save_box = (self.p2_box[0] - 115.0, self.preset_btn_y, 220.0, 34.0)
        self.p2_del_box = (self.p2_box[0] + 150.0, self.preset_btn_y, 180.0, 34.0)

        self.lbl_p1_save = arcade.Text("+ SAVE NEW", self.p1_save_box[0], self.preset_btn_y, COLOR_TEXT, 14, anchor_x="center", anchor_y="center", bold=True)
        self.lbl_p1_del = arcade.Text("DELETE", self.p1_del_box[0], self.preset_btn_y, COLOR_TEXT_DIM, 14, anchor_x="center", anchor_y="center", bold=True)
        self.lbl_p2_save = arcade.Text("+ SAVE NEW", self.p2_save_box[0], self.preset_btn_y, COLOR_TEXT, 14, anchor_x="center", anchor_y="center", bold=True)
        self.lbl_p2_del = arcade.Text("DELETE", self.p2_del_box[0], self.preset_btn_y, COLOR_TEXT_DIM, 14, anchor_x="center", anchor_y="center", bold=True)

        # Action keybind rows
        self.p1_action_lbls: list[arcade.Text] = []
        self.p1_key_lbls: list[arcade.Text] = []
        self.p2_action_lbls: list[arcade.Text] = []
        self.p2_key_lbls: list[arcade.Text] = []

        self.action_start_y = 588.0
        self.action_step_y = 48.0
        for i, (_, act_label) in enumerate(ACTION_SPECS):
            ay = self.action_start_y - i * self.action_step_y
            self.p1_action_lbls.append(arcade.Text(act_label, self.p1_box[0] - 335.0, ay, COLOR_TEXT, 18))
            self.p1_key_lbls.append(arcade.Text("", self.p1_box[0] + 335.0, ay, COLOR_GOLD, 18, anchor_x="right", bold=True))
            self.p2_action_lbls.append(arcade.Text(act_label, self.p2_box[0] - 335.0, ay, COLOR_TEXT, 18))
            self.p2_key_lbls.append(arcade.Text("", self.p2_box[0] + 335.0, ay, COLOR_GOLD, 18, anchor_x="right", bold=True))

        # Bottom action buttons
        self.reset_btn_box = (WINDOW_WIDTH * 0.36, 106.0, 420.0, 50.0)
        self.back_btn_box = (WINDOW_WIDTH * 0.64, 106.0, 420.0, 50.0)
        self.lbl_reset = arcade.Text("RESET TO DEFAULTS", self.reset_btn_box[0], 106.0, COLOR_TEXT, 19, anchor_x="center", anchor_y="center", bold=True)
        self.lbl_back = arcade.Text("SAVE & BACK", self.back_btn_box[0], 106.0, COLOR_TEXT, 19, anchor_x="center", anchor_y="center", bold=True)

        # Modal text-entry labels
        self.modal_title = arcade.Text("", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 88, COLOR_GOLD, 28, anchor_x="center", bold=True)
        self.modal_sub = arcade.Text(
            f"Type a preset name (up to {MAX_PRESET_NAME_LEN} chars) to save current controls:",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 46, COLOR_TEXT_DIM, 17, anchor_x="center",
        )
        self.modal_input_lbl = arcade.Text("", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 8, (255, 255, 255, 255), 30, anchor_x="center", anchor_y="center", bold=True)
        self.modal_hint = arcade.Text(
            "ENTER: Save Preset   |   ESC: Cancel",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 82, COLOR_GOLD, 18, anchor_x="center", bold=True,
        )

        self.footer = arcade.Text(
            "Up/Down: Navigate  |  Left/Right: Change / Switch Column  |  Enter / Click: Select  |  ESC: Back",
            WINDOW_WIDTH * 0.5, 40.0, COLOR_TEXT_DIM, font_size=16, anchor_x="center",
        )
        self._refresh_labels()

    def _open_save_modal(self, player_num: int):
        self.naming_player = player_num
        cur_preset = SETTINGS.p1_preset if player_num == 1 else SETTINGS.p2_preset
        if SETTINGS.is_custom_preset(cur_preset):
            self.naming_text = cur_preset
        else:
            idx = len(SETTINGS.custom_presets) + 1
            self.naming_text = f"P{player_num} Preset {idx}"
        self.naming_is_default = True
        self.cursor_timer = 0.0

    def _confirm_save_modal(self):
        if self.naming_player is None:
            return
        p_num = self.naming_player
        ok, msg = SETTINGS.save_preset(p_num, self.naming_text)
        self.status_lbl.text = msg
        if ok:
            self.naming_player = None
            self._refresh_labels()

    def _delete_active_preset(self, player_num: int):
        preset_name = SETTINGS.p1_preset if player_num == 1 else SETTINGS.p2_preset
        _, msg = SETTINGS.delete_preset(preset_name)
        self.status_lbl.text = msg
        self._refresh_labels()

    def _refresh_labels(self):
        self.lbl_mode_val.text = f"<  {SETTINGS.display_mode_label()}  >"
        self.lbl_mode_val.color = COLOR_GOLD if self.selected_row == 0 else COLOR_TEXT

        if SETTINGS.display_mode == "borderless":
            scr = getattr(self.window, "screen", None)
            nw = int(scr.width) if scr else WINDOW_WIDTH
            nh = int(scr.height) if scr else WINDOW_HEIGHT
            self.lbl_res_val.text = f"Native ({nw} x {nh})"
            self.lbl_res_val.color = COLOR_TEXT_DIM
        else:
            rw, rh = SETTINGS.resolution
            self.lbl_res_val.text = f"<  {rw} x {rh}  >"
            self.lbl_res_val.color = COLOR_GOLD if self.selected_row == 1 else COLOR_TEXT

        # Preset selector labels
        p1_sel_preset = (self.selected_row == self.row_preset_select and self.selected_col == 0)
        p2_sel_preset = (self.selected_row == self.row_preset_select and self.selected_col == 1)
        self.lbl_p1_preset_val.text = f"<  {SETTINGS.p1_preset}  >"
        self.lbl_p1_preset_val.color = COLOR_GOLD if p1_sel_preset else (130, 225, 255, 255)
        self.lbl_p2_preset_val.text = f"<  {SETTINGS.p2_preset}  >"
        self.lbl_p2_preset_val.color = COLOR_GOLD if p2_sel_preset else (130, 225, 255, 255)

        # Preset Save / Delete button labels
        p1_act_row = (self.selected_row == self.row_preset_actions and self.selected_col == 0)
        p2_act_row = (self.selected_row == self.row_preset_actions and self.selected_col == 1)
        p1_can_del = SETTINGS.is_custom_preset(SETTINGS.p1_preset)
        p2_can_del = SETTINGS.is_custom_preset(SETTINGS.p2_preset)

        self.lbl_p1_save.color = COLOR_GOLD if (p1_act_row and self.preset_action_idx == 0) else COLOR_TEXT
        self.lbl_p1_del.color = (
            (255, 110, 110, 255) if (p1_act_row and self.preset_action_idx == 1 and p1_can_del)
            else ((220, 120, 120, 255) if p1_can_del else (95, 105, 125, 200))
        )

        self.lbl_p2_save.color = COLOR_GOLD if (p2_act_row and self.preset_action_idx == 0) else COLOR_TEXT
        self.lbl_p2_del.color = (
            (255, 110, 110, 255) if (p2_act_row and self.preset_action_idx == 1 and p2_can_del)
            else ((220, 120, 120, 255) if p2_can_del else (95, 105, 125, 200))
        )

        # Keybind rows
        for i, (act_id, _) in enumerate(ACTION_SPECS):
            row_idx = self.row_actions_start + i
            p1_sel = (self.selected_row == row_idx and self.selected_col == 0)
            p2_sel = (self.selected_row == row_idx and self.selected_col == 1)

            if p1_sel and self.listening:
                self.p1_key_lbls[i].text = "[ PRESS ANY KEY... ]"
                self.p1_key_lbls[i].color = (110, 235, 255, 255)
            else:
                self.p1_key_lbls[i].text = f"[ {key_name(SETTINGS.p1_controls[act_id])} ]"
                self.p1_key_lbls[i].color = COLOR_GOLD if p1_sel else COLOR_TEXT

            if p2_sel and self.listening:
                self.p2_key_lbls[i].text = "[ PRESS ANY KEY... ]"
                self.p2_key_lbls[i].color = (110, 235, 255, 255)
            else:
                self.p2_key_lbls[i].text = f"[ {key_name(SETTINGS.p2_controls[act_id])} ]"
                self.p2_key_lbls[i].color = COLOR_GOLD if p2_sel else COLOR_TEXT

        self.lbl_reset.color = COLOR_GOLD if self.selected_row == self.row_reset else COLOR_TEXT
        self.lbl_back.color = COLOR_GOLD if self.selected_row == self.row_back else COLOR_TEXT

    def _cycle_display_mode(self, step: int):
        modes = [m[0] for m in DISPLAY_MODES]
        idx = (modes.index(SETTINGS.display_mode) + step) % len(modes)
        SETTINGS.display_mode = modes[idx]
        SETTINGS.save()
        SETTINGS.apply_display(self.window)
        self.status_lbl.text = f"Display mode set to {SETTINGS.display_mode_label()}"
        self._refresh_labels()

    def _cycle_resolution(self, step: int):
        if SETTINGS.display_mode == "borderless":
            self.status_lbl.text = "Borderless Fullscreen automatically uses your monitor's native resolution."
            return
        res_list = get_available_resolutions(self.window)
        if SETTINGS.resolution not in res_list:
            res_list.append(SETTINGS.resolution)
            res_list.sort(key=lambda r: (r[0], r[1]))
        idx = (res_list.index(SETTINGS.resolution) + step) % len(res_list)
        SETTINGS.resolution = res_list[idx]
        SETTINGS.save()
        SETTINGS.apply_display(self.window)
        rw, rh = SETTINGS.resolution
        self.status_lbl.text = f"Resolution set to {rw} x {rh}"
        self._refresh_labels()

    def _cycle_player_preset(self, player_num: int, step: int):
        chosen = SETTINGS.cycle_preset(player_num, step)
        self.status_lbl.text = f"Player {player_num} loaded preset '{chosen}'"
        self._refresh_labels()

    def _go_back(self):
        SETTINGS.save()
        if self.return_view is not None:
            if hasattr(self.return_view, "hud"):
                self.return_view.hud.refresh_control_labels()
            self.window.show_view(self.return_view)
        else:
            self.window.show_view(TitleView())

    def on_update(self, delta_time: float):
        dt = min(delta_time, MAX_FRAME_TIME)
        self.stage.update(dt)
        if self.naming_player is not None:
            self.cursor_timer += dt

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.stage.draw_backdrop()
        self.stage.draw_foreground()

        self.header.draw()
        self.status_lbl.draw()

        # Display panel
        dcx, dcy, dcw, dch = self.disp_box
        arcade.draw_rect_filled(arcade.XYWH(dcx, dcy, dcw, dch), COLOR_HUD_BG)
        arcade.draw_rect_outline(arcade.XYWH(dcx, dcy, dcw, dch), COLOR_GOLD if self.selected_row in (0, 1) else (75, 90, 120, 255), border_width=3)

        if self.selected_row == 0:
            arcade.draw_rect_filled(arcade.XYWH(dcx, 876.0, dcw - 40, 38), (255, 215, 75, 32))
            arcade.draw_rect_outline(arcade.XYWH(dcx, 876.0, dcw - 40, 38), COLOR_GOLD, border_width=2)
        elif self.selected_row == 1:
            arcade.draw_rect_filled(arcade.XYWH(dcx, 830.0, dcw - 40, 38), (255, 215, 75, 32))
            arcade.draw_rect_outline(arcade.XYWH(dcx, 830.0, dcw - 40, 38), COLOR_GOLD, border_width=2)

        self.lbl_disp_title.draw()
        self.lbl_mode_name.draw()
        self.lbl_mode_val.draw()
        self.lbl_res_name.draw()
        self.lbl_res_val.draw()

        # P1 & P2 Controls panels
        for col_idx, (box, accent) in enumerate(((self.p1_box, COLOR_HUD_P1), (self.p2_box, COLOR_HUD_P2))):
            bx, by, bw, bh = box
            active_panel = (self.row_preset_select <= self.selected_row < self.row_reset) and (self.selected_col == col_idx)
            arcade.draw_rect_filled(arcade.XYWH(bx, by, bw, bh), COLOR_HUD_BG)
            arcade.draw_rect_outline(arcade.XYWH(bx, by, bw, bh), COLOR_GOLD if active_panel else accent, border_width=3)

        self.lbl_p1_head.draw()
        self.lbl_p2_head.draw()

        # Preset selector highlight bar
        if self.selected_row == self.row_preset_select:
            bx = self.p1_box[0] if self.selected_col == 0 else self.p2_box[0]
            bw = self.p1_box[2] - 44.0
            arcade.draw_rect_filled(arcade.XYWH(bx, self.preset_select_y + 6.0, bw, 38.0), (255, 215, 75, 34))
            arcade.draw_rect_outline(arcade.XYWH(bx, self.preset_select_y + 6.0, bw, 38.0), COLOR_GOLD, border_width=2)

        self.lbl_p1_preset_tag.draw()
        self.lbl_p1_preset_val.draw()
        self.lbl_p2_preset_tag.draw()
        self.lbl_p2_preset_val.draw()

        # Preset Save / Delete mini-buttons
        for col_idx, (save_box, del_box, preset_name) in enumerate((
            (self.p1_save_box, self.p1_del_box, SETTINGS.p1_preset),
            (self.p2_save_box, self.p2_del_box, SETTINGS.p2_preset),
        )):
            is_act_row = (self.selected_row == self.row_preset_actions and self.selected_col == col_idx)
            can_del = SETTINGS.is_custom_preset(preset_name)

            sx, sy, sw, sh = save_box
            s_sel = is_act_row and self.preset_action_idx == 0
            arcade.draw_rect_filled(arcade.XYWH(sx, sy, sw, sh), (42, 56, 48, 235) if s_sel else (24, 30, 48, 220))
            arcade.draw_rect_outline(arcade.XYWH(sx, sy, sw, sh), COLOR_GOLD if s_sel else (85, 135, 105, 220), border_width=2)

            dx, dy, dw, dh = del_box
            d_sel = is_act_row and self.preset_action_idx == 1
            arcade.draw_rect_filled(arcade.XYWH(dx, dy, dw, dh), (62, 30, 34, 235) if d_sel else (24, 30, 48, 220))
            del_rim = (255, 110, 110, 255) if d_sel else ((165, 85, 90, 220) if can_del else (65, 72, 92, 160))
            arcade.draw_rect_outline(arcade.XYWH(dx, dy, dw, dh), del_rim, border_width=2)

        self.lbl_p1_save.draw()
        self.lbl_p1_del.draw()
        self.lbl_p2_save.draw()
        self.lbl_p2_del.draw()

        # Divider line between preset controls and keybinds
        for box in (self.p1_box, self.p2_box):
            arcade.draw_line(box[0] - box[2] * 0.45, 622.0, box[0] + box[2] * 0.45, 622.0, (80, 95, 130, 180), line_width=1.5)

        # Action keybind rows
        for i in range(self.num_actions):
            row_idx = self.row_actions_start + i
            ay = self.action_start_y - i * self.action_step_y + 6.0
            if self.selected_row == row_idx:
                bx = self.p1_box[0] if self.selected_col == 0 else self.p2_box[0]
                bw = self.p1_box[2] - 44.0
                fill_col = (110, 235, 255, 45) if self.listening else (255, 215, 75, 34)
                rim_col = (110, 235, 255, 255) if self.listening else COLOR_GOLD
                arcade.draw_rect_filled(arcade.XYWH(bx, ay, bw, 38.0), fill_col)
                arcade.draw_rect_outline(arcade.XYWH(bx, ay, bw, 38.0), rim_col, border_width=2)

            self.p1_action_lbls[i].draw()
            self.p1_key_lbls[i].draw()
            self.p2_action_lbls[i].draw()
            self.p2_key_lbls[i].draw()

        # Bottom buttons
        for row_idx, box, lbl in (
            (self.row_reset, self.reset_btn_box, self.lbl_reset),
            (self.row_back, self.back_btn_box, self.lbl_back),
        ):
            bx, by, bw, bh = box
            selected = self.selected_row == row_idx
            arcade.draw_rect_filled(arcade.XYWH(bx, by, bw, bh), (45, 35, 35, 235) if selected else COLOR_HUD_BG)
            arcade.draw_rect_outline(arcade.XYWH(bx, by, bw, bh), COLOR_GOLD if selected else (90, 105, 135, 255), border_width=3 if selected else 2)
            lbl.draw()

        self.footer.draw()

        # Modal overlay when naming a new preset
        if self.naming_player is not None:
            arcade.draw_rect_filled(
                arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT),
                (0, 0, 0, 195),
            )
            mw, mh = 760.0, 280.0
            mx, my = WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5
            accent = COLOR_HUD_P1 if self.naming_player == 1 else COLOR_HUD_P2
            arcade.draw_rect_filled(arcade.XYWH(mx, my, mw, mh), (16, 20, 36, 250))
            arcade.draw_rect_outline(arcade.XYWH(mx, my, mw, mh), accent, border_width=4)

            arcade.draw_rect_filled(arcade.XYWH(mx, my - 8, 560.0, 58.0), (10, 13, 24, 255))
            arcade.draw_rect_outline(arcade.XYWH(mx, my - 8, 560.0, 58.0), COLOR_GOLD, border_width=2.5)

            self.modal_title.text = f"SAVE PLAYER {self.naming_player} CONTROL PRESET"
            cursor = "|" if int(self.cursor_timer * 2.4) % 2 == 0 else " "
            self.modal_input_lbl.text = f"{self.naming_text}{cursor}"
            self.modal_input_lbl.color = (165, 180, 210, 255) if self.naming_is_default else (255, 255, 255, 255)

            self.modal_title.draw()
            self.modal_sub.draw()
            self.modal_input_lbl.draw()
            self.modal_hint.draw()

    def on_text(self, text: str):
        if self.naming_player is None:
            return
        for ch in text:
            if ch.isprintable() and ch not in ("\r", "\n", "\t"):
                if self.naming_is_default:
                    self.naming_text = ""
                    self.naming_is_default = False
                if len(self.naming_text) < MAX_PRESET_NAME_LEN:
                    self.naming_text += ch

    def on_key_press(self, key: int, modifiers: int):
        # 1. Modal preset-name typing mode
        if self.naming_player is not None:
            if key == arcade.key.ESCAPE:
                self.naming_player = None
                self.status_lbl.text = "Save preset cancelled."
            elif key in (arcade.key.ENTER, arcade.key.RETURN):
                self._confirm_save_modal()
            elif key == arcade.key.BACKSPACE:
                self.naming_is_default = False
                self.naming_text = self.naming_text[:-1]
            return

        # 2. Keybind listening mode
        if self.listening:
            self.listening = False
            if key == arcade.key.ESCAPE:
                self.status_lbl.text = "Rebind cancelled."
            else:
                act_idx = self.selected_row - self.row_actions_start
                act_id, act_label = ACTION_SPECS[act_idx]
                p_num = 1 if self.selected_col == 0 else 2
                msg = SETTINGS.bind_key(p_num, act_id, key)
                self.status_lbl.text = f"P{p_num} {act_label}: {msg}"
            self._refresh_labels()
            return

        # 3. Standard Settings navigation
        if key == arcade.key.ESCAPE:
            self._go_back()
            return

        total_rows = self.row_back + 1
        if key == arcade.key.UP:
            self.selected_row = (self.selected_row - 1) % total_rows
            self._refresh_labels()
        elif key == arcade.key.DOWN:
            self.selected_row = (self.selected_row + 1) % total_rows
            self._refresh_labels()
        elif key == arcade.key.LEFT:
            if self.selected_row == 0:
                self._cycle_display_mode(-1)
            elif self.selected_row == 1:
                self._cycle_resolution(-1)
            elif self.selected_row == self.row_preset_select:
                self._cycle_player_preset(1 if self.selected_col == 0 else 2, -1)
            elif self.selected_row == self.row_preset_actions:
                if self.preset_action_idx == 1:
                    self.preset_action_idx = 0
                elif self.selected_col == 1:
                    self.selected_col = 0
                    self.preset_action_idx = 1
                self._refresh_labels()
            elif self.selected_row >= self.row_reset:
                self.selected_row = self.row_reset
                self._refresh_labels()
            else:
                self.selected_col = 0
                self._refresh_labels()
        elif key == arcade.key.RIGHT:
            if self.selected_row == 0:
                self._cycle_display_mode(1)
            elif self.selected_row == 1:
                self._cycle_resolution(1)
            elif self.selected_row == self.row_preset_select:
                self._cycle_player_preset(1 if self.selected_col == 0 else 2, 1)
            elif self.selected_row == self.row_preset_actions:
                if self.preset_action_idx == 0:
                    self.preset_action_idx = 1
                elif self.selected_col == 0:
                    self.selected_col = 1
                    self.preset_action_idx = 0
                self._refresh_labels()
            elif self.selected_row >= self.row_reset:
                self.selected_row = self.row_back
                self._refresh_labels()
            else:
                self.selected_col = 1
                self._refresh_labels()
        elif key in (arcade.key.ENTER, arcade.key.SPACE):
            p_num = 1 if self.selected_col == 0 else 2
            if self.selected_row == 0:
                self._cycle_display_mode(1)
            elif self.selected_row == 1:
                self._cycle_resolution(1)
            elif self.selected_row == self.row_preset_select:
                self._cycle_player_preset(p_num, 1)
            elif self.selected_row == self.row_preset_actions:
                if self.preset_action_idx == 0:
                    self._open_save_modal(p_num)
                else:
                    self._delete_active_preset(p_num)
            elif self.row_actions_start <= self.selected_row < self.row_reset:
                self.listening = True
                act_label = ACTION_SPECS[self.selected_row - self.row_actions_start][1]
                self.status_lbl.text = f"Press any key for Player {p_num} [{act_label}] (ESC to cancel)..."
                self._refresh_labels()
            elif self.selected_row == self.row_reset:
                SETTINGS.reset_defaults()
                SETTINGS.apply_display(self.window)
                self.status_lbl.text = "Display and active controls reset to defaults (saved presets kept)."
                self._refresh_labels()
            elif self.selected_row == self.row_back:
                self._go_back()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if button != arcade.MOUSE_BUTTON_LEFT or self.listening or self.naming_player is not None:
            return

        vx, vy = self.window.screen_to_virtual(x, y)

        # Display mode & resolution rows
        if 200 <= vx <= 1720:
            if 857 <= vy <= 895:
                self.selected_row = 0
                self._cycle_display_mode(1)
                return
            if 811 <= vy <= 849:
                self.selected_row = 1
                self._cycle_resolution(1)
                return

        # Preset selector row (click left half for prev, right half for next)
        if (self.preset_select_y - 14.0) <= vy <= (self.preset_select_y + 24.0):
            for col_idx, box in enumerate((self.p1_box, self.p2_box)):
                if (box[0] - box[2] * 0.5) <= vx <= (box[0] + box[2] * 0.5):
                    self.selected_row = self.row_preset_select
                    self.selected_col = col_idx
                    step = -1 if vx < (box[0] + 150.0) else 1
                    self._cycle_player_preset(col_idx + 1, step)
                    return

        # Preset Save / Delete buttons
        for col_idx, (save_box, del_box) in enumerate((
            (self.p1_save_box, self.p1_del_box),
            (self.p2_save_box, self.p2_del_box),
        )):
            sx, sy, sw, sh = save_box
            if (sx - sw * 0.5) <= vx <= (sx + sw * 0.5) and (sy - sh * 0.5) <= vy <= (sy + sh * 0.5):
                self.selected_row = self.row_preset_actions
                self.selected_col = col_idx
                self.preset_action_idx = 0
                self._refresh_labels()
                self._open_save_modal(col_idx + 1)
                return

            dx, dy, dw, dh = del_box
            if (dx - dw * 0.5) <= vx <= (dx + dw * 0.5) and (dy - dh * 0.5) <= vy <= (dy + dh * 0.5):
                self.selected_row = self.row_preset_actions
                self.selected_col = col_idx
                self.preset_action_idx = 1
                self._delete_active_preset(col_idx + 1)
                return

        # Control keybind rows
        for i in range(self.num_actions):
            ay = self.action_start_y - i * self.action_step_y + 6.0
            if (ay - 19.0) <= vy <= (ay + 19.0):
                for col_idx, box in enumerate((self.p1_box, self.p2_box)):
                    if (box[0] - box[2] * 0.5) <= vx <= (box[0] + box[2] * 0.5):
                        self.selected_row = self.row_actions_start + i
                        self.selected_col = col_idx
                        self.listening = True
                        self.status_lbl.text = f"Press any key for Player {col_idx + 1} [{ACTION_SPECS[i][1]}] (ESC to cancel)..."
                        self._refresh_labels()
                        return

        # Bottom buttons
        rx, ry, rw, rh = self.reset_btn_box
        if (rx - rw * 0.5) <= vx <= (rx + rw * 0.5) and (ry - rh * 0.5) <= vy <= (ry + rh * 0.5):
            self.selected_row = self.row_reset
            SETTINGS.reset_defaults()
            SETTINGS.apply_display(self.window)
            self.status_lbl.text = "Display and active controls reset to defaults (saved presets kept)."
            self._refresh_labels()
            return

        bx, by, bw, bh = self.back_btn_box
        if (bx - bw * 0.5) <= vx <= (bx + bw * 0.5) and (by - bh * 0.5) <= vy <= (by + bh * 0.5):
            self.selected_row = self.row_back
            self._go_back()


class CharacterSelectView(arcade.View):
    """2-Player Smash-style character selection screen with animated previews and live preset switching."""

    def __init__(self, p1_index: int = 0, p2_index: int = 1):
        super().__init__()
        self.stage = HolidayStage(include_platforms=False, snow_count=110)
        self.roster = CHARACTER_ROSTER
        self.count = len(self.roster)

        self.p1_idx = p1_index % self.count
        self.p2_idx = p2_index % self.count
        self.p1_ready = False
        self.p2_ready = False
        self.launch_countdown = -1.0

        self.header = arcade.Text(
            "CHOOSE YOUR FIGHTER", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT - 95, COLOR_GOLD,
            font_size=54, anchor_x="center", bold=True,
        )
        self.sub_header = arcade.Text(
            "All fighters share the exact same character hurtbox — each wields unique weapon hitboxes!",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT - 142, COLOR_TEXT_DIM,
            font_size=18, anchor_x="center",
        )

        card_w = min(310.0, (WINDOW_WIDTH - 240.0) / max(1, self.count) - 28.0)
        card_h = 250.0
        total_w = self.count * card_w + (self.count - 1) * 28.0
        start_x = (WINDOW_WIDTH - total_w) * 0.5 + card_w * 0.5
        card_y = WINDOW_HEIGHT * 0.65

        self.card_boxes = []
        self.card_name_lbls = []
        self.card_weapon_lbls = []
        self.roster_sprites = arcade.SpriteList()
        self.roster_anims = []
        self.anim_timer = 0.0
        self.anim_frame = 0

        for i, spec in enumerate(self.roster):
            cx = start_x + i * (card_w + 28.0)
            self.card_boxes.append((cx, card_y, card_w, card_h))

            anims = get_fighter_animations(spec.char_id)["RIGHT"]["IDLE"]
            self.roster_anims.append(anims)
            sp = arcade.Sprite(anims[0])
            sp.scale = (spec.visual_height * 1.45) / max(1, anims[0].height)
            sp.center_x = cx
            sp.bottom = card_y - 36.0
            self.roster_sprites.append(sp)

            self.card_name_lbls.append(
                arcade.Text(spec.display_name, cx, card_y - 78.0, COLOR_TEXT, 22, anchor_x="center", bold=True)
            )
            self.card_weapon_lbls.append(
                arcade.Text(spec.weapon_name, cx, card_y - 104.0, COLOR_GOLD, 14, anchor_x="center")
            )

        panel_w, panel_h = 760.0, 290.0
        panel_y = 235.0
        self.p1_panel = (WINDOW_WIDTH * 0.28, panel_y, panel_w, panel_h)
        self.p2_panel = (WINDOW_WIDTH * 0.72, panel_y, panel_w, panel_h)

        self.p1_preview = arcade.SpriteList()
        self.p2_preview = arcade.SpriteList()
        self.p1_sp = arcade.Sprite(self.roster_anims[self.p1_idx][0])
        self.p2_sp = arcade.Sprite(get_fighter_animations(self.roster[self.p2_idx].char_id)["LEFT"]["IDLE"][0])
        self.p1_preview.append(self.p1_sp)
        self.p2_preview.append(self.p2_sp)

        self.p1_texts = self._create_panel_texts(self.p1_panel, "PLAYER 1", COLOR_HUD_P1)
        self.p2_texts = self._create_panel_texts(self.p2_panel, "PLAYER 2", COLOR_HUD_P2)
        self._refresh_panel_control_hints()

        self.p1_badge_lbl = arcade.Text("P1", 0, 0, (255, 255, 255, 255), 13, anchor_x="center", anchor_y="center", bold=True)
        self.p2_badge_lbl = arcade.Text("P2", 0, 0, (15, 20, 30, 255), 13, anchor_x="center", anchor_y="center", bold=True)

        self.ready_banner = arcade.Text(
            "PRESS ENTER OR SPACE TO START BATTLE!",
            WINDOW_WIDTH * 0.5, 455, COLOR_GOLD, font_size=26, anchor_x="center", bold=True,
        )
        self.footer = arcade.Text(
            "ESC: Back to Main Menu   |   Press Heavy (or click Preset bar) to switch saved control presets",
            WINDOW_WIDTH * 0.5, 42, COLOR_TEXT_DIM, font_size=17, anchor_x="center",
        )

    def _create_panel_texts(self, box: tuple, player_label: str, accent: tuple) -> dict:
        cx, cy, w, h = box
        left = cx - w * 0.5 + 28.0
        right = cx + w * 0.5 - 28.0
        top = cy + h * 0.5 - 32.0
        return {
            "header": arcade.Text(player_label, left, top, accent, 20, bold=True),
            "status": arcade.Text("SELECTING...", right, top, COLOR_TEXT_DIM, 16, anchor_x="right", bold=True),
            "char": arcade.Text("", left + 155.0, top - 40.0, COLOR_TEXT, 28, bold=True),
            "title": arcade.Text("", left + 155.0, top - 66.0, COLOR_GOLD, 15),
            "desc": arcade.Text("", left + 155.0, top - 104.0, COLOR_TEXT_DIM, 13, multiline=True, width=int(w - 210)),
            "stats": arcade.Text("", left + 155.0, top - 154.0, COLOR_TEXT, 14, bold=True),
            "preset": arcade.Text("", cx, cy - h * 0.5 + 48.0, (130, 225, 255, 255), 14, anchor_x="center", bold=True),
            "hint": arcade.Text("", cx, cy - h * 0.5 + 18.0, COLOR_TEXT_DIM, 13, anchor_x="center"),
        }

    def _refresh_panel_control_hints(self):
        c1 = SETTINGS.p1_controls
        c2 = SETTINGS.p2_controls
        self.p1_texts["preset"].text = f"Control Preset: < {SETTINGS.p1_preset} >  [{key_name(c1['heavy'])}: Switch]"
        self.p2_texts["preset"].text = f"Control Preset: < {SETTINGS.p2_preset} >  [{key_name(c2['heavy'])}: Switch]"
        self.p1_texts["hint"].text = (
            f"{key_name(c1['left'])}/{key_name(c1['right'])}: Select  |  "
            f"{key_name(c1['attack'])} / {key_name(c1['jump'])}: Lock In  |  {key_name(c1['shield'])}: Back"
        )
        self.p2_texts["hint"].text = (
            f"{key_name(c2['left'])}/{key_name(c2['right'])}: Select  |  "
            f"{key_name(c2['attack'])} / {key_name(c2['jump'])}: Lock In  |  {key_name(c2['shield'])}: Back"
        )

    def on_update(self, delta_time: float):
        dt = min(delta_time, MAX_FRAME_TIME)
        self.stage.update(dt)

        self.anim_timer += dt
        if self.anim_timer >= 0.10:
            self.anim_timer -= 0.10
            self.anim_frame += 1

        for i, sp in enumerate(self.roster_sprites):
            frames = self.roster_anims[i]
            sp.texture = frames[self.anim_frame % len(frames)]

        if self.p1_ready and self.p2_ready:
            if self.launch_countdown < 0:
                self.launch_countdown = 0.55
            else:
                self.launch_countdown -= dt
                if self.launch_countdown <= 0:
                    self._start_match()
        else:
            self.launch_countdown = -1.0

    def _start_match(self):
        p1_id = self.roster[self.p1_idx].char_id
        p2_id = self.roster[self.p2_idx].char_id
        self.window.show_view(FightView(p1_char_id=p1_id, p2_char_id=p2_id))

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.stage.draw_backdrop()
        self.stage.draw_foreground()

        self.header.draw()
        self.sub_header.draw()

        for i, (cx, cy, cw, ch) in enumerate(self.card_boxes):
            arcade.draw_rect_filled(arcade.XYWH(cx, cy, cw, ch), COLOR_HUD_BG)
            arcade.draw_rect_outline(arcade.XYWH(cx, cy, cw, ch), (75, 90, 120, 255), border_width=2)

            p1_on = i == self.p1_idx
            p2_on = i == self.p2_idx
            if p1_on and p2_on:
                arcade.draw_rect_outline(arcade.XYWH(cx, cy, cw + 8, ch + 8), COLOR_HUD_P1, border_width=4)
                arcade.draw_rect_outline(arcade.XYWH(cx, cy, cw + 16, ch + 16), COLOR_HUD_P2, border_width=3)
            elif p1_on:
                arcade.draw_rect_outline(arcade.XYWH(cx, cy, cw + 8, ch + 8), COLOR_HUD_P1, border_width=4)
            elif p2_on:
                arcade.draw_rect_outline(arcade.XYWH(cx, cy, cw + 8, ch + 8), COLOR_HUD_P2, border_width=4)

            if p1_on:
                bx = cx - (34 if p2_on else 0)
                arcade.draw_rect_filled(arcade.XYWH(bx, cy + ch * 0.5 + 16, 56, 24), COLOR_HUD_P1)
                self.p1_badge_lbl.x = bx
                self.p1_badge_lbl.y = cy + ch * 0.5 + 16
                self.p1_badge_lbl.draw()
            if p2_on:
                bx = cx + (34 if p1_on else 0)
                arcade.draw_rect_filled(arcade.XYWH(bx, cy + ch * 0.5 + 16, 56, 24), COLOR_HUD_P2)
                self.p2_badge_lbl.x = bx
                self.p2_badge_lbl.y = cy + ch * 0.5 + 16
                self.p2_badge_lbl.draw()

            self.card_name_lbls[i].draw()
            self.card_weapon_lbls[i].draw()

        try:
            self.roster_sprites.draw(pixelated=True)
        except TypeError:
            self.roster_sprites.draw()

        is_mirror = self.p1_idx == self.p2_idx
        self._draw_player_panel(
            self.p1_panel, self.roster[self.p1_idx], self.p1_ready,
            COLOR_HUD_P1, self.p1_texts, self.p1_sp, self.p1_preview,
            facing="RIGHT", tint_preview=is_mirror,
        )
        self._draw_player_panel(
            self.p2_panel, self.roster[self.p2_idx], self.p2_ready,
            COLOR_HUD_P2, self.p2_texts, self.p2_sp, self.p2_preview,
            facing="LEFT", tint_preview=is_mirror,
        )

        if self.p1_ready and self.p2_ready:
            self.ready_banner.draw()

        self.footer.draw()

    def _draw_player_panel(self, box, spec, is_ready, accent, texts, sp, sp_list, facing: str, tint_preview: bool = False):
        cx, cy, w, h = box
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), COLOR_HUD_BG)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), COLOR_GOLD if is_ready else accent, border_width=4)

        ped_x = cx - w * 0.5 + 95.0
        ped_y = cy + 6.0
        arcade.draw_rect_filled(arcade.XYWH(ped_x, ped_y, 132, 156), (22, 27, 46, 220))
        arcade.draw_rect_outline(arcade.XYWH(ped_x, ped_y, 132, 156), accent, border_width=2)

        # Preset pill bar
        pill_y = cy - h * 0.5 + 53.0
        arcade.draw_rect_filled(arcade.XYWH(cx, pill_y, w - 48.0, 26.0), (20, 26, 44, 220))
        arcade.draw_rect_outline(arcade.XYWH(cx, pill_y, w - 48.0, 26.0), (95, 145, 195, 180), border_width=1.5)

        frames = get_fighter_animations(spec.char_id)[facing]["IDLE"]
        tex = frames[self.anim_frame % len(frames)]
        sp.texture = tex
        sp.color = accent if tint_preview else (255, 255, 255, 255)
        sp.scale = (spec.visual_height * 1.48) / max(1, tex.height)
        sp.center_x = ped_x
        sp.bottom = ped_y - 62.0
        try:
            sp_list.draw(pixelated=True)
        except TypeError:
            sp_list.draw()

        texts["status"].text = "READY!" if is_ready else "SELECTING..."
        texts["status"].color = COLOR_GOLD if is_ready else COLOR_TEXT_DIM
        texts["char"].text = spec.display_name
        texts["title"].text = f"{spec.title}  •  {spec.weapon_name}"
        texts["desc"].text = spec.summary

        def _bars(val: int) -> str:
            return "\u25a0" * val + "\u25a1" * (5 - val)

        texts["stats"].text = (
            f"REACH {_bars(spec.reach_rating)}    "
            f"POWER {_bars(spec.power_rating)}    "
            f"SPEED {_bars(spec.speed_rating)}"
        )

        for lbl in texts.values():
            lbl.draw()

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.ESCAPE:
            self.window.show_view(TitleView())
            return

        c1 = SETTINGS.p1_controls
        c2 = SETTINGS.p2_controls

        if not self.p1_ready:
            if key in (c1["left"], c1["up"]):
                self.p1_idx = (self.p1_idx - 1) % self.count
            elif key in (c1["right"], c1["down"]):
                self.p1_idx = (self.p1_idx + 1) % self.count
            elif key == c1["heavy"]:
                SETTINGS.cycle_preset(1, 1)
                self._refresh_panel_control_hints()
            elif key in (c1["attack"], c1["jump"]):
                self.p1_ready = True
        else:
            if key == c1["shield"]:
                self.p1_ready = False

        if not self.p2_ready:
            if key in (c2["left"], c2["up"]):
                self.p2_idx = (self.p2_idx - 1) % self.count
            elif key in (c2["right"], c2["down"]):
                self.p2_idx = (self.p2_idx + 1) % self.count
            elif key == c2["heavy"]:
                SETTINGS.cycle_preset(2, 1)
                self._refresh_panel_control_hints()
            elif key in (c2["attack"], c2["jump"]):
                self.p2_ready = True
        else:
            if key == c2["shield"]:
                self.p2_ready = False

        if key == arcade.key.ENTER:
            if self.p1_ready and self.p2_ready:
                self._start_match()
            elif not self.p1_ready:
                self.p1_ready = True
            elif not self.p2_ready:
                self.p2_ready = True

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        vx, vy = self.window.screen_to_virtual(x, y)

        for p_num, box, is_ready in (
            (1, self.p1_panel, self.p1_ready),
            (2, self.p2_panel, self.p2_ready),
        ):
            if is_ready:
                continue
            cx, cy, w, h = box
            pill_y = cy - h * 0.5 + 53.0
            if (cx - w * 0.5 + 24.0) <= vx <= (cx + w * 0.5 - 24.0) and (pill_y - 14.0) <= vy <= (pill_y + 14.0):
                step = -1 if vx < cx else 1
                SETTINGS.cycle_preset(p_num, step)
                self._refresh_panel_control_hints()
                return


class ControlsView(arcade.View):
    def __init__(self):
        super().__init__()
        self.stage = HolidayStage(include_platforms=False, snow_count=90)
        c1 = SETTINGS.p1_controls
        c2 = SETTINGS.p2_controls

        self.header = arcade.Text(
            "CONTROLS & MECHANICS", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.83, COLOR_GOLD,
            font_size=48, anchor_x="center", bold=True,
        )
        self.p1_head = arcade.Text(f"PLAYER 1  [{SETTINGS.p1_preset}]", WINDOW_WIDTH * 0.30, WINDOW_HEIGHT * 0.66, COLOR_HUD_P1, 24, anchor_x="center", bold=True)
        self.p1_body = arcade.Text(
            f"Move / DI: {key_name(c1['left'])} / {key_name(c1['right'])}\n"
            f"Jump / Double Jump: {key_name(c1['up'])} or {key_name(c1['jump'])} (Tap for Short Hop)\n"
            f"Crouch / Fast Fall / Ledge Drop: {key_name(c1['down'])}\n"
            f"Side Attack (2-Hit Combo): {key_name(c1['attack'])} -> {key_name(c1['attack'])}\n"
            f"Up Slash / Air Meteor: {key_name(c1['up'])} + {key_name(c1['attack'])}  |  {key_name(c1['down'])} + {key_name(c1['attack'])} (Air)\n"
            f"Ground Heavy Smash: Hold {key_name(c1['heavy'])}  (White -> Red -> Blue)\n"
            f"Mid-Air Dash Recovery (2-Slash): {key_name(c1['heavy'])} in Mid-Air\n"
            f"Shield / Tech: {key_name(c1['shield'])}  |  Ledge Grab: Touch Stage Corner",
            WINDOW_WIDTH * 0.30 - 340, WINDOW_HEIGHT * 0.56, COLOR_TEXT, 16, multiline=True, width=680,
        )
        self.p2_head = arcade.Text(f"PLAYER 2  [{SETTINGS.p2_preset}]", WINDOW_WIDTH * 0.70, WINDOW_HEIGHT * 0.66, COLOR_HUD_P2, 24, anchor_x="center", bold=True)
        self.p2_body = arcade.Text(
            f"Move / DI: {key_name(c2['left'])} / {key_name(c2['right'])}\n"
            f"Jump / Double Jump: {key_name(c2['up'])} or {key_name(c2['jump'])} (Tap for Short Hop)\n"
            f"Crouch / Fast Fall / Ledge Drop: {key_name(c2['down'])}\n"
            f"Side Attack (2-Hit Combo): {key_name(c2['attack'])} -> {key_name(c2['attack'])}\n"
            f"Up Slash / Air Meteor: {key_name(c2['up'])} + {key_name(c2['attack'])}  |  {key_name(c2['down'])} + {key_name(c2['attack'])} (Air)\n"
            f"Ground Heavy Smash: Hold {key_name(c2['heavy'])}  (White -> Red -> Blue)\n"
            f"Mid-Air Dash Recovery (2-Slash): {key_name(c2['heavy'])} in Mid-Air\n"
            f"Shield / Tech: {key_name(c2['shield'])}  |  Ledge Grab: Touch Stage Corner",
            WINDOW_WIDTH * 0.70 - 340, WINDOW_HEIGHT * 0.56, COLOR_TEXT, 16, multiline=True, width=680,
        )
        self.footer = arcade.Text("Press ESC or ENTER to return  |  Create & load control presets in SETTINGS  |  F1 in-game toggles Hitboxes", WINDOW_WIDTH * 0.5, 55, COLOR_TEXT_DIM, 19, anchor_x="center")

    def on_update(self, delta_time: float):
        self.stage.update(min(delta_time, MAX_FRAME_TIME))

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
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
    def __init__(self, p1_char_id: str = "Xteve", p2_char_id: str = "Xanta"):
        super().__init__()
        self.p1_char_id = p1_char_id
        self.p2_char_id = p2_char_id
        self.world_camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()
        self.hud = MatchHUD()
        self.p1_tag = arcade.Text("P1", 0, 0, COLOR_HUD_P1, 13, anchor_x="center", bold=True)
        self.p2_tag = arcade.Text("P2", 0, 0, COLOR_HUD_P2, 13, anchor_x="center", bold=True)
        self.setup()

    def _sync_camera_viewports(self):
        if self.window is None:
            return
        vp = getattr(self.window, "viewport_rect", arcade.LBWH(0, 0, self.window.width, self.window.height))
        self.gui_camera.viewport = vp
        self.gui_camera.projection = arcade.LRBT(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
        self.world_camera.viewport = vp
        self.world_camera.projection = arcade.LRBT(
            -WINDOW_WIDTH * 0.5, WINDOW_WIDTH * 0.5,
            -WINDOW_HEIGHT * 0.5, WINDOW_HEIGHT * 0.5,
        )

    def on_show_view(self):
        self._sync_camera_viewports()
        self.hud.refresh_control_labels()

    def on_resize(self, width: int, height: int):
        self._sync_camera_viewports()

    def setup(self):
        self._sync_camera_viewports()
        self.hud.refresh_control_labels()
        self.stage = HolidayStage(include_platforms=True, snow_count=120)
        self.effects = EffectSystem()

        is_mirror = self.p1_char_id == self.p2_char_id
        p1_tint = COLOR_HUD_P1 if is_mirror else (255, 255, 255, 255)
        p2_tint = COLOR_HUD_P2 if is_mirror else (255, 255, 255, 255)

        self.p1 = Fighter(
            WINDOW_WIDTH * 0.30, 450, "Player 1", COLOR_HUD_P1,
            facing=1, char_id=self.p1_char_id, sprite_tint=p1_tint,
        )
        self.p2 = Fighter(
            WINDOW_WIDTH * 0.70, 450, "Player 2", COLOR_HUD_P2,
            facing=-1, char_id=self.p2_char_id, sprite_tint=p2_tint,
        )

        self.fighter_sprites = arcade.SpriteList()
        self.fighter_sprites.append(self.p1)
        self.fighter_sprites.append(self.p2)

        # Pre-upload VFX textures to the GPU atlas during setup
        for f in (self.p1, self.p2):
            for dir_dict in f.vfx.values():
                for frames in dir_dict.values():
                    for tex in frames:
                        arcade.draw_texture_rect(tex, arcade.XYWH(-9999, -9999, 1, 1), alpha=0)

        self.cam_x = WINDOW_WIDTH * 0.5
        self.cam_y = 460.0
        self.cam_zoom = 1.12
        self.world_camera.position = (self.cam_x, self.cam_y)
        self.world_camera.zoom = self.cam_zoom

        self.accumulator = 0.0
        self.screen_shake = 0.0
        self.hitstop_timer = 0
        self.impact_freeze_timer = 0
        self.impact_point = (WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5)
        self.impact_accent = (255, 80, 90)
        self.ko_flash_timer = 0

        self.intro_timer = 115
        self.game_set_timer = 0
        self.match_time = 0.0
        self.game_state = "INTRO"
        self.is_paused = False
        self.game_over_title = ""
        self.game_over_sub = ""

    def _open_char_select(self):
        ids = [c.char_id for c in CHARACTER_ROSTER]
        i1 = ids.index(self.p1_char_id) if self.p1_char_id in ids else 0
        i2 = ids.index(self.p2_char_id) if self.p2_char_id in ids else 1
        self.window.show_view(CharacterSelectView(p1_index=i1, p2_index=i2))

    def _update_active_camera(self, dt: float):
        def _tracked_point(f: Fighter) -> tuple[float, float]:
            tx = max(-240.0, min(WINDOW_WIDTH + 240.0, f.hurt_center_x + f.change_x * 4.5))
            ty = max(-80.0, min(WINDOW_HEIGHT + 280.0, f.hurt_center_y + f.change_y * 3.0))
            return tx, ty

        active_fighters = [f for f in (self.p1, self.p2) if not f.is_ko_waiting]
        if len(active_fighters) == 2:
            x1, y1 = _tracked_point(active_fighters[0])
            x2, y2 = _tracked_point(active_fighters[1])
            mid_x = (x1 + x2) * 0.5
            mid_y = (y1 + y2) * 0.5 + CAMERA_Y_BIAS
            span_x = abs(x1 - x2) + CAMERA_PADDING_X
            span_y = abs(y1 - y2) + CAMERA_PADDING_Y
        elif len(active_fighters) == 1:
            x1, y1 = _tracked_point(active_fighters[0])
            mid_x = (x1 + WINDOW_WIDTH * 0.5) * 0.5
            mid_y = (y1 + 360.0) * 0.5 + CAMERA_Y_BIAS
            span_x = 1280.0
            span_y = 760.0
        else:
            mid_x = WINDOW_WIDTH * 0.5
            mid_y = 430.0
            span_x = 1500.0
            span_y = 860.0

        target_zoom = min(WINDOW_WIDTH / span_x, WINDOW_HEIGHT / span_y)
        target_zoom = max(CAMERA_MIN_ZOOM, min(CAMERA_MAX_ZOOM, target_zoom))
        if self.impact_freeze_timer > 0:
            target_zoom = min(CAMERA_MAX_ZOOM, target_zoom * 1.07)

        lerp_t = 1.0 - math.exp(-CAMERA_LERP_SPEED * dt)
        self.cam_zoom += (target_zoom - self.cam_zoom) * lerp_t
        self.cam_x += (mid_x - self.cam_x) * lerp_t
        self.cam_y += (mid_y - self.cam_y) * lerp_t

        half_w = (WINDOW_WIDTH * 0.5) / self.cam_zoom
        half_h = (WINDOW_HEIGHT * 0.5) / self.cam_zoom

        if half_w * 2.0 >= (WORLD_MAX_X - WORLD_MIN_X):
            self.cam_x = WINDOW_WIDTH * 0.5
        else:
            self.cam_x = max(WORLD_MIN_X + half_w, min(WORLD_MAX_X - half_w, self.cam_x))

        if half_h * 2.0 >= (WORLD_MAX_Y - WORLD_MIN_Y):
            self.cam_y = WINDOW_HEIGHT * 0.5
        else:
            self.cam_y = max(WORLD_MIN_Y + half_h, min(WORLD_MAX_Y - half_h, self.cam_y))

        sx, sy = 0.0, 0.0
        if self.screen_shake > 0:
            self.screen_shake = max(0.0, self.screen_shake - dt * 65.0)
            sx = random.uniform(-self.screen_shake, self.screen_shake)
            sy = random.uniform(-self.screen_shake, self.screen_shake)

        self.world_camera.zoom = self.cam_zoom
        self.world_camera.position = (self.cam_x + sx, self.cam_y + sy)

    def _get_camera_world_bounds(self) -> tuple[float, float, float, float]:
        half_w = (WINDOW_WIDTH * 0.5) / max(0.01, self.cam_zoom)
        half_h = (WINDOW_HEIGHT * 0.5) / max(0.01, self.cam_zoom)
        return (
            self.cam_x - half_w,
            self.cam_x + half_w,
            self.cam_y - half_h,
            self.cam_y + half_h,
        )

    def on_update(self, delta_time: float):
        dt = min(delta_time, MAX_FRAME_TIME)
        if self.is_paused or self.game_state == "OVER":
            return

        if self.game_state == "PLAYING":
            self.match_time += dt

        self.stage.update(dt)
        self.effects.update()
        self._update_active_camera(dt)

        self.accumulator += dt
        steps = 0
        while self.accumulator >= PHYSICS_STEP and steps < MAX_STEPS_PER_FRAME:
            self.accumulator -= PHYSICS_STEP
            self._fixed_step()
            steps += 1

        self._check_blast_zones()

    def _fixed_step(self):
        if self.ko_flash_timer > 0:
            self.ko_flash_timer -= 1

        if self.game_state == "INTRO":
            self.intro_timer -= 1
            if self.intro_timer <= 0:
                self.game_state = "PLAYING"
            return

        if self.game_state == "GAME_SET":
            if self.game_set_timer % 2 == 0:
                self.p1.update_physics(self.stage.platforms, opponent=self.p2)
                self.p2.update_physics(self.stage.platforms, opponent=self.p1)
                self.p1.update_animation(PHYSICS_STEP)
                self.p2.update_animation(PHYSICS_STEP)
            self.game_set_timer -= 1
            if self.game_set_timer <= 0:
                self.game_state = "OVER"
            return

        for idx, f in enumerate((self.p1, self.p2)):
            if f.is_ko_waiting:
                f.respawn_timer -= 1
                if f.respawn_timer <= 0:
                    spawn_x = WINDOW_WIDTH * (0.30 if idx == 0 else 0.70)
                    f.reset_after_ko(spawn_x, 590)
                    self.effects.emit_sparkle(f.hurt_center_x, f.hurt_center_y, count=26)

        if self.hitstop_timer > 0:
            self.hitstop_timer -= 1
            if self.impact_freeze_timer > 0:
                self.impact_freeze_timer -= 1
            for f in (self.p1, self.p2):
                if f.hit_flash_timer > 0:
                    f.hit_flash_timer -= 1
                    if f.hit_flash_timer == 0:
                        f.color = f.sprite_tint
            return

        self.impact_freeze_timer = 0

        self.p1.update_physics(self.stage.platforms, opponent=self.p2)
        self.p2.update_physics(self.stage.platforms, opponent=self.p1)

        for f in (self.p1, self.p2):
            if f.is_ko_waiting:
                continue
            if f.just_landed:
                self.effects.emit_land(f.hurt_center_x, f.hurt_bottom)
            if f.just_jumped:
                self.effects.emit_jump(f.hurt_center_x, f.hurt_bottom)
            if f.just_double_jumped:
                self.effects.emit_sparkle(f.hurt_center_x, f.hurt_bottom)
            if f.just_teched:
                self.effects.emit_tech(f.hurt_center_x, f.hurt_bottom, f.accent_color)
            if f.just_grabbed_ledge:
                edge_x = f.hurt_right if f.ledge_side == -1 else f.hurt_left
                self.effects.emit_ledge_grab(edge_x, f.hurt_top, f.accent_color)
            if f.launch_active and not f.is_grounded and math.hypot(f.change_x, f.change_y) > 10.5:
                self.effects.emit_launch_trail(f.hurt_center_x, f.hurt_center_y, f.accent_color)

        self.p1.update_animation(PHYSICS_STEP)
        self.p2.update_animation(PHYSICS_STEP)

        self._resolve_attack(self.p1, self.p2)
        self._resolve_attack(self.p2, self.p1)

    def _resolve_attack(self, attacker: Fighter, defender: Fighter):
        if attacker.is_ko_waiting or defender.is_ko_waiting:
            return
        if not attacker.attack_hitbox or attacker.attack_has_hit:
            return
        if defender.invincible_timer > 0 or self.game_state != "PLAYING":
            return

        hx, hy, hw, hh = attacker.attack_hitbox
        if not (
            defender.hurt_right > hx
            and defender.hurt_left < hx + hw
            and defender.hurt_top > hy
            and defender.hurt_bottom < hy + hh
        ):
            return

        if defender.is_shielding and defender.shield_stun_timer == 0:
            attacker.attack_has_hit = True
            attacker.attack_hitbox = None
            shield_dmg = (
                28.0 if attacker.attack_state == "ATTACK_HEAVY"
                else (24.0 if attacker.attack_state == "ATTACK_SIDE_2" else 16.0)
            )
            defender.shield_health = max(0.0, defender.shield_health - shield_dmg)
            self.effects.emit_sparkle(defender.hurt_center_x, defender.hurt_center_y, count=10, color=(110, 195, 255, 255))
            if defender.shield_health <= 0:
                defender.shield_stun_timer = 110
                defender.is_shielding = False
                self.screen_shake = 16.0
                self.effects.emit_shield_break(defender.hurt_center_x, defender.hurt_center_y)
            return

        dmg = attacker.get_current_attack_damage()
        kb_mult = attacker.get_weapon_spec().kb_mult
        defender.damage += dmg
        attacker.damage_dealt_total += dmg
        scale = (1.0 + defender.damage * KNOCKBACK_DAMAGE_SCALE) * kb_mult
        direction = 1 if attacker.facing_right else -1

        is_heavy = attacker.attack_state == "ATTACK_HEAVY"
        is_meteor = attacker.attack_state == "ATTACK_DOWN"
        is_up = attacker.attack_state == "ATTACK_UP"
        is_side_2 = attacker.attack_state == "ATTACK_SIDE_2"
        is_dash = attacker.attack_state == "ATTACK_DASH"
        is_dash_2 = attacker.is_dash_second_slash

        if is_heavy:
            mult = attacker.charge_power_multiplier
            defender.change_x = BASE_KNOCKBACK_X * scale * 1.85 * mult * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 1.45 * mult
        elif is_dash and not is_dash_2:
            defender.change_x = (BASE_KNOCKBACK_X * 0.55 + abs(attacker.change_x) * 0.55) * direction
            defender.change_y = BASE_KNOCKBACK_Y * 0.65
        elif is_dash_2:
            defender.change_x = BASE_KNOCKBACK_X * scale * 1.38 * direction
            defender.change_y = BASE_KNOCKBACK_Y * scale * 1.22
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

        if is_dash and not is_dash_2:
            defender.hitstun_timer = 10
            defender.invincible_timer = 5
        else:
            defender.hitstun_timer = int(HITSTUN_BASE * scale * (1.45 if is_heavy else (1.25 if (is_side_2 or is_dash_2) else 1.0)))
            defender.invincible_timer = INVINCIBLE_HIT_FRAMES

        defender._release_ledge(regrab_cooldown=22)
        defender.is_grounded = False
        defender.hit_flash_timer = HIT_FLASH_FRAMES
        defender.color = COLOR_HIT_FLASH
        defender._impulse_squash(0.88, -0.02)

        launch_speed = math.hypot(defender.change_x, defender.change_y)
        if launch_speed > attacker.peak_launch_speed:
            attacker.peak_launch_speed = launch_speed

        is_big_hit = (
            is_heavy
            or is_meteor
            or is_side_2
            or is_dash_2
            or launch_speed >= LAUNCH_SPEED_THRESHOLD
        )
        if is_big_hit and not (is_dash and not is_dash_2):
            defender.start_launch(dmg)

        contact_x = defender.hurt_left if attacker.facing_right else defender.hurt_right
        contact_y = defender.hurt_center_y

        if (is_heavy or is_meteor or is_side_2 or is_dash_2 or launch_speed >= 15.0) and not (is_dash and not is_dash_2):
            freeze_len = IMPACT_FREEZE_FRAMES + (4 if is_heavy else 0)
            self.hitstop_timer = freeze_len
            self.impact_freeze_timer = freeze_len
            self.impact_point = (contact_x, contact_y)
            self.impact_accent = attacker.accent_color[:3]
            self.screen_shake = 26.0 if is_heavy else 19.0
        else:
            self.hitstop_timer = 3 if (is_dash and not is_dash_2) else HITSTOP_FRAMES
            self.screen_shake = 8.0 if (is_dash and not is_dash_2) else 11.0

        label_override = "DASH SLASH!" if is_dash_2 else None
        self.effects.emit_hit(
            contact_x, contact_y, direction,
            is_meteor=is_meteor,
            is_heavy=(is_heavy or is_side_2 or is_dash_2),
            label_override=label_override,
        )

        attacker.attack_has_hit = True
        attacker.attack_hitbox = None

    def _is_in_blast_zone(self, f: Fighter) -> bool:
        if f.is_ko_waiting:
            return False

        if f.hurt_center_y < -BOTTOM_BLAST_ZONE:
            return True

        if (
            f.hurt_center_x < -SIDE_BLAST_ZONE
            or f.hurt_center_x > WINDOW_WIDTH + SIDE_BLAST_ZONE
            or f.hurt_center_y > WINDOW_HEIGHT + TOP_BLAST_ZONE
        ):
            return True

        off_left = f.hurt_center_x < 0.0 and f.change_x < 0.0
        off_right = f.hurt_center_x > WINDOW_WIDTH and f.change_x > 0.0
        off_top = f.hurt_center_y > WINDOW_HEIGHT and f.change_y > 0.0
        if (off_left or off_right or off_top) and (f.launch_active or f.hitstun_timer > 0):
            if math.hypot(f.change_x, f.change_y) >= EXTREME_LAUNCH_KO_SPEED:
                return True

        return False

    def _check_blast_zones(self):
        if self.game_state != "PLAYING" or self.hitstop_timer > 0:
            return

        p1_ko = self._is_in_blast_zone(self.p1)
        p2_ko = self._is_in_blast_zone(self.p2)

        if p1_ko and p2_ko:
            self.p1.stocks -= 1
            self.p2.stocks -= 1
            self.p1.kos_scored += 1
            self.p2.kos_scored += 1
            self.effects.emit_ko(self.p1.hurt_center_x, self.p1.hurt_center_y, self.p1.change_x, self.p1.change_y, self.p1.accent_color)
            self.effects.emit_ko(self.p2.hurt_center_x, self.p2.hurt_center_y, self.p2.change_x, self.p2.change_y, self.p2.accent_color)
            self.screen_shake = 26.0
            self.ko_flash_timer = 8
            if self.p1.stocks <= 0 and self.p2.stocks <= 0:
                self._trigger_game_set("DRAW", "Double knockout!")
            elif self.p1.stocks <= 0:
                self._trigger_game_set(f"PLAYER 2 ({self.p2.spec.display_name}) WINS", "Winter champion crowned.")
            else:
                self._trigger_game_set(f"PLAYER 1 ({self.p1.spec.display_name}) WINS", "Winter champion crowned.")
            return

        if p1_ko:
            self._handle_single_ko(self.p1, self.p2)
        elif p2_ko:
            self._handle_single_ko(self.p2, self.p1)

    def _handle_single_ko(self, victim: Fighter, survivor: Fighter):
        victim.stocks -= 1
        survivor.kos_scored += 1
        self.effects.emit_ko(victim.hurt_center_x, victim.hurt_center_y, victim.change_x, victim.change_y, victim.accent_color)
        self.screen_shake = 24.0
        self.ko_flash_timer = 8

        victim._release_ledge(regrab_cooldown=0)
        victim.is_ko_waiting = True
        victim.attack_hitbox = None
        victim.change_x = 0.0
        victim.change_y = 0.0

        if victim.stocks <= 0:
            self._trigger_game_set(f"{survivor.player_name.upper()} ({survivor.spec.display_name}) WINS", "Winter champion crowned.")
        else:
            victim.respawn_timer = KO_RESPAWN_DELAY_FRAMES

    def _trigger_game_set(self, title: str, sub: str):
        self.game_over_title = title
        self.game_over_sub = sub
        self.game_set_timer = GAME_SET_DELAY_FRAMES
        self.game_state = "GAME_SET"

    def _draw_impact_freeze_backdrop(self):
        phase = (self.impact_freeze_timer // 2) % 3
        if phase == 0:
            bg_col = (145, 14, 34, 255)
            bolt_col = (255, 245, 175, 235)
        elif phase == 1:
            bg_col = (12, 18, 34, 255)
            bolt_col = (255, 70, 95, 240)
        else:
            bg_col = (44, 14, 88, 255)
            bolt_col = (110, 240, 255, 235)

        arcade.draw_rect_filled(
            arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT),
            bg_col,
        )

        for i in range(-4, 10):
            sx = i * 240.0 + (self.impact_freeze_timer * 35.0)
            poly = (
                (sx, 0),
                (sx + 90.0, 0),
                (sx + 340.0, WINDOW_HEIGHT),
                (sx + 250.0, WINDOW_HEIGHT),
            )
            arcade.draw_polygon_filled(poly, (255, 255, 255, 24))

        ix, iy = self.impact_point
        rng = random.Random(self.impact_freeze_timer * 97)
        for b in range(7):
            ang = (b / 7.0) * math.tau + rng.uniform(-0.25, 0.25)
            cx, cy = ix, iy
            for seg in range(5):
                step = rng.uniform(55.0, 105.0)
                nx = cx + math.cos(ang + rng.uniform(-0.35, 0.35)) * step
                ny = cy + math.sin(ang + rng.uniform(-0.35, 0.35)) * step
                arcade.draw_line(cx, cy, nx, ny, bolt_col, line_width=max(1.5, 5.0 - seg * 0.8))
                cx, cy = nx, ny

    def on_draw(self):
        self.clear()
        self._sync_camera_viewports()

        with self.gui_camera.activate():
            if self.impact_freeze_timer > 0:
                self._draw_impact_freeze_backdrop()
            else:
                self.stage.draw_backdrop(self.cam_x, self.cam_y)

        with self.world_camera.activate():
            self.stage.draw_foreground()
            self.stage.draw_fighter_shadows((self.p1, self.p2))

            self._draw_charge_vfx()

            for f in (self.p1, self.p2):
                if f.is_ko_waiting:
                    continue

                if f.respawn_invuln_timer > 0:
                    arcade.draw_ellipse_filled(f.hurt_center_x, f.hurt_bottom - 3, 64, 12, (255, 220, 90, 110))
                    arcade.draw_ellipse_outline(f.hurt_center_x, f.hurt_bottom - 3, 64, 12, (255, 235, 130, 220), border_width=2)

                if f.is_ledge_hanging and f.invincible_timer > 0:
                    arcade.draw_circle_outline(f.hurt_center_x, f.hurt_center_y, 44.0, (255, 225, 100, 185), border_width=2.5)

                if f.is_shielding:
                    radius = 52 * (0.55 + 0.45 * (f.shield_health / 100.0))
                    arcade.draw_circle_filled(f.hurt_center_x, f.hurt_center_y, radius, COLOR_SHIELD)
                    arcade.draw_circle_outline(f.hurt_center_x, f.hurt_center_y, radius, COLOR_SHIELD_RIM, 3)

            self.p1.visible = not self.p1.is_ko_waiting
            self.p2.visible = not self.p2.is_ko_waiting
            try:
                self.fighter_sprites.draw(pixelated=True)
            except TypeError:
                self.fighter_sprites.draw()

            self._draw_attack_vfx()
            self.effects.draw()
            self._draw_player_tags()

            if config.DEBUG_HITBOXES:
                for f in (self.p1, self.p2):
                    if f.is_ko_waiting:
                        continue
                    arcade.draw_rect_outline(
                        arcade.XYWH(f.hurt_center_x, f.hurt_center_y, FIGHTER_HURTBOX_W, FIGHTER_HURTBOX_H),
                        COLOR_HURTBOX_DEBUG, 2,
                    )
                    if f.attack_hitbox:
                        hx, hy, hw, hh = f.attack_hitbox
                        arcade.draw_rect_outline(arcade.XYWH(hx + hw * 0.5, hy + hh * 0.5, hw, hh), COLOR_HITBOX_DEBUG, 2)

        with self.gui_camera.activate():
            if self.ko_flash_timer > 0:
                alpha = int(140 * (self.ko_flash_timer / 8.0))
                arcade.draw_rect_filled(
                    arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT),
                    (255, 255, 255, alpha),
                )

            self.hud.draw(
                self.p1, self.p2,
                self.game_state, self.intro_timer, self.is_paused,
                self.game_over_title, self.game_over_sub,
                self.match_time, self._get_camera_world_bounds(),
            )

    def _draw_player_tags(self):
        for f, tag in ((self.p1, self.p1_tag), (self.p2, self.p2_tag)):
            if f.is_ko_waiting:
                continue
            ty = max(f.top, f.hurt_top) + 16.0
            tag.x = f.hurt_center_x
            tag.y = ty
            tag.draw()
            arcade.draw_triangle_filled(
                f.hurt_center_x - 5, ty - 4,
                f.hurt_center_x + 5, ty - 4,
                f.hurt_center_x, ty - 10,
                f.accent_color,
            )

    def _draw_charge_vfx(self):
        for f in (self.p1, self.p2):
            if f.is_ko_waiting or not f.is_charging:
                continue
            ratio = f.charge_timer / MAX_CHARGE_FRAMES
            stage = "WHITE" if ratio < 0.35 else ("RED" if ratio < 0.75 else "BLUE")
            dkey = "RIGHT" if f.facing_right else "LEFT"
            frames = f.vfx[dkey][f"CHARGE_{stage}"]
            tex = frames[(f.charge_timer // 6) % len(frames)]
            bx = f.hurt_center_x + (40 if f.facing_right else -40)
            by = f.hurt_center_y + 10
            arcade.draw_texture_rect(tex, arcade.XYWH(bx, by, 86, 86))

            if ratio >= 0.35:
                ring_col = (255, 95, 95, 165) if ratio < 0.75 else (100, 205, 255, 210)
                pulse_r = 46.0 + math.sin(f.charge_timer * 0.45) * 6.0
                arcade.draw_circle_outline(f.hurt_center_x, f.hurt_center_y, pulse_r, ring_col, border_width=2.5)

    def _draw_attack_vfx(self):
        for f in (self.p1, self.p2):
            if f.is_ko_waiting or not f.is_attacking:
                continue
            dkey = "RIGHT" if f.facing_right else "LEFT"
            frames = f.vfx[dkey][f.attack_vfx_key]
            tex = frames[min(f.attack_texture_index, len(frames) - 1)]
            w_spec = f.get_weapon_spec()

            if w_spec.vertical_mode in ("UP", "DOWN"):
                vx = f.hurt_center_x
                vy = f.hurt_center_y + w_spec.vfx_offset_y
            else:
                reach = ATTACK_REACH * w_spec.vfx_reach_mult
                vx = f.hurt_center_x + (reach if f.facing_right else -reach)
                vy = f.hurt_center_y + w_spec.vfx_offset_y

            arcade.draw_texture_rect(tex, arcade.XYWH(vx, vy, w_spec.vfx_size, w_spec.vfx_size))

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.F1:
            config.DEBUG_HITBOXES = not config.DEBUG_HITBOXES
            return

        if key == arcade.key.ESCAPE and self.game_state == "PLAYING":
            self.is_paused = not self.is_paused
            return

        if self.is_paused or self.game_state == "OVER":
            if self.is_paused and key == arcade.key.S:
                self.window.show_view(SettingsView(return_view=self))
            elif key == arcade.key.R:
                self.setup()
            elif key == arcade.key.C:
                self._open_char_select()
            elif key == arcade.key.Q:
                self.window.show_view(TitleView())
            return

        c1 = SETTINGS.p1_controls
        c2 = SETTINGS.p2_controls

        # Player 1
        if key == c1["left"]:
            self.p1.move_left = True
        elif key == c1["right"]:
            self.p1.move_right = True
        elif key == c1["up"]:
            self.p1.up_held = True
            self.p1.jump_pressed = True
            self.p1.jump_held = True
        elif key == c1["jump"]:
            self.p1.jump_pressed = True
            self.p1.jump_held = True
        elif key == c1["down"]:
            self.p1.crouching = True
        elif key == c1["attack"]:
            self.p1.attack_pressed = True
        elif key == c1["heavy"]:
            self.p1.charge_pressed = True
            self.p1.charge_held = True
        elif key == c1["shield"]:
            self.p1.shield_held = True
            self.p1.trigger_tech_window()

        # Player 2
        if key == c2["left"]:
            self.p2.move_left = True
        elif key == c2["right"]:
            self.p2.move_right = True
        elif key == c2["up"]:
            self.p2.up_held = True
            self.p2.jump_pressed = True
            self.p2.jump_held = True
        elif key == c2["jump"]:
            self.p2.jump_pressed = True
            self.p2.jump_held = True
        elif key == c2["down"]:
            self.p2.crouching = True
        elif key == c2["attack"]:
            self.p2.attack_pressed = True
        elif key == c2["heavy"]:
            self.p2.charge_pressed = True
            self.p2.charge_held = True
        elif key == c2["shield"]:
            self.p2.shield_held = True
            self.p2.trigger_tech_window()

    def on_key_release(self, key: int, modifiers: int):
        c1 = SETTINGS.p1_controls
        c2 = SETTINGS.p2_controls

        # Player 1
        if key == c1["left"]:
            self.p1.move_left = False
        elif key == c1["right"]:
            self.p1.move_right = False
        elif key == c1["up"]:
            self.p1.up_held = False
            self.p1.jump_held = False
        elif key == c1["jump"]:
            self.p1.jump_held = False
        elif key == c1["down"]:
            self.p1.crouching = False
        elif key == c1["heavy"]:
            self.p1.charge_held = False
        elif key == c1["shield"]:
            self.p1.shield_held = False

        # Player 2
        if key == c2["left"]:
            self.p2.move_left = False
        elif key == c2["right"]:
            self.p2.move_right = False
        elif key == c2["up"]:
            self.p2.up_held = False
            self.p2.jump_held = False
        elif key == c2["jump"]:
            self.p2.jump_held = False
        elif key == c2["down"]:
            self.p2.crouching = False
        elif key == c2["heavy"]:
            self.p2.charge_held = False
        elif key == c2["shield"]:
            self.p2.shield_held = False