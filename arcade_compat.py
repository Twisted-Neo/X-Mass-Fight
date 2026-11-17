"""Arcade 2.x / 3.x compatibility wrappers for drawing primitives and text."""

import arcade


def draw_filled_rectangle(cx, cy, w, h, color):
    if hasattr(arcade, "draw_rect_filled"):
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), color)
    else:
        arcade.draw_rectangle_filled(cx, cy, w, h, color)


def draw_rectangle_outline(cx, cy, w, h, color, border_width=1):
    if hasattr(arcade, "draw_rect_outline"):
        arcade.draw_rect_outline(
            arcade.XYWH(cx, cy, w, h), color, border_width=border_width,
        )
    else:
        arcade.draw_rectangle_outline(cx, cy, w, h, color, border_width)


def draw_sprite(sprite):
    """Arcade 3.x removed Sprite.draw()."""
    if hasattr(arcade, "draw_sprite"):
        arcade.draw_sprite(sprite)
    else:
        sprite.draw()


def draw_text(text, x, y, color, size, anchor_x="left", anchor_y="baseline",
              bold=False):
    """Prefer arcade.Text; fall back to arcade.draw_text for older builds."""
    if hasattr(arcade, "Text"):
        try:
            arcade.Text(
                text, x, y, color,
                font_size=size, anchor_x=anchor_x, anchor_y=anchor_y,
                bold=bold,
            ).draw()
            return
        except Exception:
            pass
    arcade.draw_text(
        text, x, y, color, size,
        anchor_x=anchor_x, anchor_y=anchor_y,
    )


def draw_line(x1, y1, x2, y2, color, width=1):
    arcade.draw_line(x1, y1, x2, y2, color, width)