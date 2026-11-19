"""Persistent cached arcade.Text HUD, camera-aware off-screen edge indicators, match timer, and overlays."""

import math
import random
import arcade

from config import (
    COLOR_GOLD, COLOR_HUD_BG, COLOR_HUD_BORDER, COLOR_HUD_P1, COLOR_HUD_P2,
    COLOR_TEXT, COLOR_TEXT_DIM, HEART_CHAR, SHIELD_MAX_HEALTH,
    SIDE_BLAST_ZONE, TOP_BLAST_ZONE, WINDOW_HEIGHT, WINDOW_WIDTH,
)


class _OffscreenIndicator:
    """Smash-style screen-edge directional arrow + radial dial showing off-screen X distance."""

    def __init__(self, tag: str, accent: tuple):
        self.accent = accent
        self.radius = 28.0
        self.lbl_tag = arcade.Text(tag, 0, 0, accent, 10, anchor_x="center", anchor_y="center", bold=True)
        self.lbl_dist = arcade.Text("0", 0, 0, COLOR_TEXT, 12, anchor_x="center", anchor_y="center", bold=True)
        self._cached_text = ""

    def draw(self, player, cam_bounds: tuple):
        if getattr(player, "is_ko_waiting", False):
            return

        cam_left, cam_right, cam_bottom, cam_top = cam_bounds
        cam_w = max(1.0, cam_right - cam_left)
        cam_h = max(1.0, cam_top - cam_bottom)

        off_left = player.center_x < cam_left
        off_right = player.center_x > cam_right
        off_top = player.center_y > cam_top

        if not (off_left or off_right or off_top):
            return

        x_dist = (cam_left - player.center_x) if off_left else ((player.center_x - cam_right) if off_right else 0.0)
        y_dist = max(0.0, player.center_y - cam_top)

        screen_x = ((player.center_x - cam_left) / cam_w) * WINDOW_WIDTH
        screen_y = ((player.center_y - cam_bottom) / cam_h) * WINDOW_HEIGHT

        pad_x = 58.0
        min_y = 195.0
        max_y = WINDOW_HEIGHT - 102.0

        if off_left:
            ix = pad_x
            iy = max(min_y, min(max_y, screen_y))
        elif off_right:
            ix = WINDOW_WIDTH - pad_x
            iy = max(min_y, min(max_y, screen_y))
        else:
            ix = max(pad_x, min(WINDOW_WIDTH - pad_x, screen_x))
            iy = max_y

        ang = math.atan2(screen_y - iy, screen_x - ix)
        r = self.radius

        tip_r = r + 16.0
        base_r = r + 2.0
        spread = 0.42
        tx = ix + math.cos(ang) * tip_r
        ty = iy + math.sin(ang) * tip_r
        bx1 = ix + math.cos(ang + spread) * base_r
        by1 = iy + math.sin(ang + spread) * base_r
        bx2 = ix + math.cos(ang - spread) * base_r
        by2 = iy + math.sin(ang - spread) * base_r

        arcade.draw_triangle_filled(tx, ty, bx1, by1, bx2, by2, self.accent)
        arcade.draw_triangle_outline(tx, ty, bx1, by1, bx2, by2, (255, 255, 255, 220), border_width=1.5)

        arcade.draw_circle_filled(ix, iy, r, (12, 15, 26, 232))
        arcade.draw_circle_outline(ix, iy, r, self.accent, border_width=2.5)

        world_x_dist = abs(player.center_x) if player.center_x < 0.0 else max(0.0, player.center_x - WINDOW_WIDTH)
        world_y_dist = max(0.0, player.center_y - WINDOW_HEIGHT)

        if off_left or off_right:
            ratio = max(0.0, min(1.0, world_x_dist / max(1.0, float(SIDE_BLAST_ZONE))))
            dist_str = f"{int(x_dist)}"
        else:
            ratio = max(0.0, min(1.0, world_y_dist / max(1.0, float(TOP_BLAST_ZONE))))
            dist_str = f"^{int(y_dist)}"

        dial_r = r - 5.5
        arcade.draw_circle_outline(ix, iy, dial_r, (45, 55, 78, 220), border_width=3)

        if ratio > 0.01:
            dial_col = self.accent if ratio < 0.60 else (COLOR_GOLD if ratio < 0.85 else (255, 75, 75, 255))
            sweep = 360.0 * ratio
            arcade.draw_arc_outline(
                ix, iy, dial_r * 2.0, dial_r * 2.0, dial_col,
                90.0 - sweep, 90.0, border_width=3,
            )
            needle_ang = math.radians(90.0 - sweep)
            nx1 = ix + math.cos(needle_ang) * (dial_r - 3.5)
            ny1 = iy + math.sin(needle_ang) * (dial_r - 3.5)
            nx2 = ix + math.cos(needle_ang) * (dial_r + 3.0)
            ny2 = iy + math.sin(needle_ang) * (dial_r + 3.0)
            arcade.draw_line(nx1, ny1, nx2, ny2, (255, 255, 255, 240), line_width=2)

        if dist_str != self._cached_text:
            self._cached_text = dist_str
            self.lbl_dist.text = dist_str

        self.lbl_tag.x = ix
        self.lbl_tag.y = iy + 8.5
        self.lbl_dist.x = ix
        self.lbl_dist.y = iy - 5.5
        self.lbl_tag.draw()
        self.lbl_dist.draw()


class _PlayerCard:
    def __init__(self, label: str, accent: tuple, left: bool):
        self.pw, self.ph = 420, 140
        self.base_cx = self.pw * 0.5 + 25 if left else WINDOW_WIDTH - self.pw * 0.5 - 25
        self.base_cy = self.ph * 0.5 + 25
        self.accent = accent
        self.left = left
        self.base_label = label

        self._cached_dmg = -1
        self._cached_stocks = -1
        self._cached_char = ""
        self._jiggle_timer = 0

        self.lbl_name = arcade.Text(label, 0, 0, accent, 18, anchor_x="left" if left else "right", bold=True)
        self.lbl_stocks_tag = arcade.Text("STOCKS", 0, 0, COLOR_TEXT_DIM, 11, anchor_x="right" if left else "left")
        self.lbl_hearts = arcade.Text("", 0, 0, COLOR_GOLD, 24, anchor_x="right" if left else "left", bold=True)
        self.lbl_damage = arcade.Text("0%", 0, 0, (140, 235, 140, 255), 32, anchor_x="left" if left else "right", bold=True)

    def draw(self, player):
        char_display = getattr(player.spec, "display_name", "")
        if char_display != self._cached_char:
            self._cached_char = char_display
            self.lbl_name.text = f"{self.base_label}  [{char_display}]" if char_display else self.base_label

        dmg = int(player.damage)
        if dmg != self._cached_dmg:
            if dmg > self._cached_dmg and self._cached_dmg >= 0:
                self._jiggle_timer = 12
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

        jx, jy = 0.0, 0.0
        if self._jiggle_timer > 0:
            self._jiggle_timer -= 1
            jx = random.uniform(-4.5, 4.5)
            jy = random.uniform(-4.5, 4.5)

        cx = self.base_cx + jx
        cy = self.base_cy + jy

        arcade.draw_rect_filled(arcade.XYWH(cx, cy, self.pw, self.ph), COLOR_HUD_BG)
        border_col = (255, 255, 255, 255) if self._jiggle_timer > 7 else self.accent
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, self.pw, self.ph), border_col, border_width=4)

        if player.stocks != self._cached_stocks:
            self._cached_stocks = player.stocks
            self.lbl_hearts.text = (HEART_CHAR + " ") * max(0, player.stocks)

        inner_l = cx - self.pw * 0.5 + 25
        inner_r = cx + self.pw * 0.5 - 25
        top_y = cy + self.ph * 0.5 - 30
        mid_y = cy - 6

        if self.left:
            self.lbl_name.x, self.lbl_name.y = inner_l, top_y
            self.lbl_stocks_tag.x, self.lbl_stocks_tag.y = inner_r, top_y
            self.lbl_hearts.x, self.lbl_hearts.y = inner_r, mid_y
            self.lbl_damage.x, self.lbl_damage.y = inner_l, mid_y - 2
        else:
            self.lbl_name.x, self.lbl_name.y = inner_r, top_y
            self.lbl_stocks_tag.x, self.lbl_stocks_tag.y = inner_l, top_y
            self.lbl_hearts.x, self.lbl_hearts.y = inner_l, mid_y
            self.lbl_damage.x, self.lbl_damage.y = inner_r, mid_y - 2

        self.lbl_name.draw()
        self.lbl_stocks_tag.draw()
        self.lbl_hearts.draw()
        self.lbl_damage.draw()

        bar_w = self.pw - 50
        bar_y = cy - self.ph * 0.5 + 16
        pct = max(0.0, player.shield_health / SHIELD_MAX_HEALTH)
        bar_col = (255, 95, 95, 255) if player.shield_stun_timer > 0 else (100, 180, 255, 255)

        arcade.draw_rect_filled(arcade.XYWH(cx, bar_y, bar_w, 8), (40, 45, 60, 255))
        if pct > 0:
            fill_w = bar_w * pct
            arcade.draw_rect_filled(arcade.XYWH(cx - bar_w * 0.5 + fill_w * 0.5, bar_y, fill_w, 8), bar_col)
        arcade.draw_rect_outline(arcade.XYWH(cx, bar_y, bar_w, 8), (150, 200, 255, 200), border_width=1)


class MatchHUD:
    def __init__(self):
        self.p1_card = _PlayerCard("PLAYER 1", COLOR_HUD_P1, left=True)
        self.p2_card = _PlayerCard("PLAYER 2", COLOR_HUD_P2, left=False)
        self.p1_offscreen = _OffscreenIndicator("P1", COLOR_HUD_P1)
        self.p2_offscreen = _OffscreenIndicator("P2", COLOR_HUD_P2)

        bar_y = WINDOW_HEIGHT - 34
        self.legend_p1 = arcade.Text(
            "P1: A/D Move | W/Space Jump | S Drop | F Atk | G Heavy (Air: Dash Atk) | E Shield",
            45, bar_y - 5, COLOR_TEXT, 12,
        )
        self.legend_p2 = arcade.Text(
            "P2: Arrows Move | Up/RShift Jump | - Atk | . Heavy (Air: Dash Atk) | , Shield | F1 Boxes",
            WINDOW_WIDTH - 45, bar_y - 5, COLOR_TEXT, 12, anchor_x="right",
        )
        self.timer_lbl = arcade.Text(
            "00:00", WINDOW_WIDTH * 0.5, bar_y - 6, COLOR_GOLD, 18,
            anchor_x="center", bold=True,
        )
        self._cached_secs = -1

        self.countdown_text = arcade.Text(
            "3", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, COLOR_GOLD,
            font_size=130, anchor_x="center", anchor_y="center", bold=True,
        )
        self.game_set_text = arcade.Text(
            "GAME!", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.52, COLOR_GOLD,
            font_size=138, anchor_x="center", anchor_y="center", bold=True,
        )
        self.pause_title = arcade.Text(
            "PAUSED", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 50, COLOR_GOLD,
            font_size=64, anchor_x="center", bold=True,
        )
        self.pause_sub = arcade.Text(
            "ESC: Resume   |   R: Restart   |   C: Char Select   |   F1: Hitboxes   |   Q: Main Menu",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 25, COLOR_TEXT,
            font_size=22, anchor_x="center",
        )
        self.over_title = arcade.Text(
            "", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 85, COLOR_GOLD,
            font_size=64, anchor_x="center", bold=True,
        )
        self.over_sub = arcade.Text(
            "", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 + 25, COLOR_TEXT,
            font_size=24, anchor_x="center",
        )
        self.over_stats = arcade.Text(
            "", WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 35, COLOR_TEXT_DIM,
            font_size=18, anchor_x="center", multiline=True, width=900, align="center",
        )
        self.over_hint = arcade.Text(
            "R: Rematch   |   C: Character Select   |   Q: Main Menu",
            WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5 - 115, COLOR_GOLD,
            font_size=20, anchor_x="center", bold=True,
        )

    def draw(
        self, p1, p2, game_state: str, intro_timer: int, is_paused: bool,
        over_title: str, over_sub: str, match_time: float, cam_bounds: tuple,
    ):
        if game_state == "PLAYING":
            self.p1_offscreen.draw(p1, cam_bounds)
            self.p2_offscreen.draw(p2, cam_bounds)

        self.p1_card.draw(p1)
        self.p2_card.draw(p2)

        bar_y = WINDOW_HEIGHT - 34
        arcade.draw_rect_filled(arcade.XYWH(WINDOW_WIDTH * 0.5, bar_y, WINDOW_WIDTH - 60, 44), (10, 12, 22, 195))
        arcade.draw_rect_outline(arcade.XYWH(WINDOW_WIDTH * 0.5, bar_y, WINDOW_WIDTH - 60, 44), COLOR_HUD_BORDER, border_width=2)
        self.legend_p1.draw()
        self.legend_p2.draw()

        secs = int(match_time)
        if secs != self._cached_secs:
            self._cached_secs = secs
            self.timer_lbl.text = f"{secs // 60:02d}:{secs % 60:02d}"
        self.timer_lbl.draw()

        if game_state == "INTRO":
            word = "3" if intro_timer > 80 else ("2" if intro_timer > 45 else ("1" if intro_timer > 15 else "FIGHT!"))
            if self.countdown_text.text != word:
                self.countdown_text.text = word
            self.countdown_text.draw()

        if game_state == "GAME_SET":
            self.game_set_text.draw()

        if is_paused:
            arcade.draw_rect_filled(arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0, 170))
            self.pause_title.draw()
            self.pause_sub.draw()

        if game_state == "OVER":
            arcade.draw_rect_filled(arcade.XYWH(WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5, WINDOW_WIDTH, WINDOW_HEIGHT), (0, 0, 0, 190))
            if self.over_title.text != over_title:
                self.over_title.text = over_title
            if self.over_sub.text != over_sub:
                self.over_sub.text = over_sub
            stats_str = (
                f"P1 — KOs: {p1.kos_scored}  |  Damage Dealt: {int(p1.damage_dealt_total)}%  |  Peak Launch: {p1.peak_launch_speed:.1f}\n"
                f"P2 — KOs: {p2.kos_scored}  |  Damage Dealt: {int(p2.damage_dealt_total)}%  |  Peak Launch: {p2.peak_launch_speed:.1f}"
            )
            if self.over_stats.text != stats_str:
                self.over_stats.text = stats_str
            self.over_title.draw()
            self.over_sub.draw()
            self.over_stats.draw()
            self.over_hint.draw()