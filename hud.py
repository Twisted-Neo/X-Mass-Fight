"""Persistent cached arcade.Text HUD, countdown, pause, and victory overlays."""

import arcade

from config import (
    COLOR_GOLD, COLOR_HUD_BG, COLOR_HUD_BORDER, COLOR_HUD_P1, COLOR_HUD_P2,
    COLOR_TEXT, COLOR_TEXT_DIM, HEART_CHAR, SHIELD_MAX_HEALTH, WINDOW_HEIGHT, WINDOW_WIDTH,
)


class _PlayerCard:
    def __init__(self, label: str, accent: tuple, left: bool):
        self.pw, self.ph = 420, 140
        self.cx = self.pw * 0.5 + 25 if left else WINDOW_WIDTH - self.pw * 0.5 - 25
        self.cy = self.ph * 0.5 + 25
        self.accent = accent
        self.left = left

        inner_l = self.cx - self.pw * 0.5 + 25
        inner_r = self.cx + self.pw * 0.5 - 25
        top_y = self.cy + self.ph * 0.5 - 30
        mid_y = self.cy - 6

        if left:
            self.lbl_name = arcade.Text(label, inner_l, top_y, accent, 18, bold=True)
            self.lbl_stocks_tag = arcade.Text("STOCKS", inner_r, top_y, COLOR_TEXT_DIM, 11, anchor_x="right")
            self.lbl_hearts = arcade.Text("", inner_r, mid_y, COLOR_GOLD, 24, anchor_x="right", bold=True)
            self.lbl_damage = arcade.Text("0%", inner_l, mid_y - 2, (140, 235, 140, 255), 32, bold=True)
        else:
            self.lbl_name = arcade.Text(label, inner_r, top_y, accent, 18, anchor_x="right", bold=True)
            self.lbl_stocks_tag = arcade.Text("STOCKS", inner_l, top_y, COLOR_TEXT_DIM, 11)
            self.lbl_hearts = arcade.Text("", inner_l, mid_y, COLOR_GOLD, 24, bold=True)
            self.lbl_damage = arcade.Text("0%", inner_r, mid_y - 2, (140, 235, 140, 255), 32, anchor_x="right", bold=True)

        self._cached_dmg = -1
        self._cached_stocks = -1

    def draw(self, player):
        arcade.draw_rect_filled(arcade.XYWH(self.cx, self.cy, self.pw, self.ph), COLOR_HUD_BG)
        arcade.draw_rect_outline(arcade.XYWH(self.cx, self.cy, self.pw, self.ph), self.accent, border_width=4)

        dmg = int(player.damage)
        if dmg != self._cached_dmg:
            self._cached_dmg = dmg
            self.lbl_damage.text = f"{dmg}%"
            if dmg < 50:
                self.lbl_damage.color = (140, 235, 140, 255)
            elif dmg < 100:
                self.lbl_damage.color = (240, 220, 100, 255)
            elif dmg < 150:
                self.lbl_damage.color = (250, 160, 80, 255)
            else:
                self.lbl_damage.color = (255, 75, 75, 255)

        if player.stocks != self._cached_stocks:
            self._cached_stocks = player.stocks
            self.lbl_hearts.text = (HEART_CHAR + " ") * max(0, player.stocks)

        self.lbl_name.draw()
        self.lbl_stocks_tag.draw()
        self.lbl_hearts.draw()
        self.lbl_damage.draw()

        # Shield bar
        bar_w = self.pw - 50
        bar_y = self.cy - self.ph * 0.5 + 16
        pct = max(0.0, player.shield_health / SHIELD_MAX_HEALTH)
        bar_col = (255, 95, 95, 255) if player.shield_stun_timer > 0 else (100, 180, 255, 255)

        arcade.draw_rect_filled(arcade.XYWH(self.cx, bar_y, bar_w, 8), (40, 45, 60, 255))
        if pct > 0:
            fill_w = bar_w * pct
            arcade.draw_rect_filled(arcade.XYWH(self.cx - bar_w * 0.5 + fill_w * 0.5, bar_y, fill_w, 8), bar_col)
        arcade.draw_rect_outline(arcade.XYWH(self.cx, bar_y, bar_w, 8), (150, 200, 255, 200), border_width=1)


class MatchHUD:
    def __init__(self):
        self.p1_card = _PlayerCard("PLAYER 1", COLOR_HUD_P1, left=True)
        self.p2_card = _PlayerCard("PLAYER 2", COLOR_HUD_P2, left=False)

        bar_y = WINDOW_HEIGHT - 34
        self.legend_p1 = arcade.Text(
            "P1: A/D Move | W/Space Jump | S Crouch/Drop | F Attack | Hold G Heavy | E Shield",
            45, bar_y - 5, COLOR_TEXT, 13,
        )
        self.legend_p2 = arcade.Text(
            "P2: Left/Right Move | Up/RShift Jump | Down Crouch/Drop | - Attack | Hold . Heavy | , Shield",
            WINDOW_WIDTH - 45, bar_y - 5, COLOR_TEXT, 13, anchor_x="right",
        )

        self.countdown_text = arcade.Text(
            "3", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, COLOR_GOLD,
            font_size=130, anchor_x="center", anchor_y="center", bold=True,
        )
        self.pause_title = arcade.Text(
            "PAUSED", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 50, COLOR_GOLD,
            font_size=64, anchor_x="center", bold=True,
        )
        self.pause_sub = arcade.Text(
            "ESC: Resume   |   R: Restart   |   Q: Main Menu",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 25, COLOR_TEXT,
            font_size=22, anchor_x="center",
        )
        self.over_title = arcade.Text(
            "", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 55, COLOR_GOLD,
            font_size=64, anchor_x="center", bold=True,
        )
        self.over_sub = arcade.Text(
            "", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 5, COLOR_TEXT,
            font_size=24, anchor_x="center",
        )
        self.over_hint = arcade.Text(
            "R: Rematch   |   Q: Main Menu",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 85, COLOR_TEXT_DIM,
            font_size=20, anchor_x="center",
        )

    def draw(self, p1, p2, game_state: str, intro_timer: int, is_paused: bool, over_title: str, over_sub: str):
        self.p1_card.draw(p1)
        self.p2_card.draw(p2)

        bar_y = WINDOW_HEIGHT - 34
        arcade.draw_rect_filled(arcade.XYWH(WINDOW_WIDTH * 0.5, bar_y, WINDOW_WIDTH - 60, 44), (10, 12, 22, 195))
        arcade.draw_rect_outline(arcade.XYWH(WINDOW_WIDTH * 0.5, bar_y, WINDOW_WIDTH - 60, 44), COLOR_HUD_BORDER, border_width=2)
        self.legend_p1.draw()
        self.legend_p2.draw()

        if game_state == "INTRO":
            word = "3" if intro_timer > 80 else ("2" if intro_timer > 45 else ("1" if intro_timer > 15 else "FIGHT!"))
            if self.countdown_text.text != word:
                self.countdown_text.text = word
            self.countdown_text.draw()

        if is_paused:
            arcade.draw_rect_filled(arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0, 170))
            self.pause_title.draw()
            self.pause_sub.draw()

        if game_state == "OVER":
            arcade.draw_rect_filled(arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0, 185))
            if self.over_title.text != over_title:
                self.over_title.text = over_title
            if self.over_sub.text != over_sub:
                self.over_sub.text = over_sub
            self.over_title.draw()
            self.over_sub.draw()
            self.over_hint.draw()