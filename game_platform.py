"""Platform geometry + stylized rendering."""

from arcade_compat import draw_filled_rectangle, draw_rectangle_outline
from config import (
    COLOR_PLATFORM_MAIN, COLOR_PLATFORM_MAIN_EDGE,
    COLOR_PLATFORM_SOFT, COLOR_PLATFORM_SOFT_EDGE,
)


class Platform:
    def __init__(self, x, y, width, height, pass_through=True):
        self.center_x = x
        self.center_y = y
        self.width = width
        self.height = height
        self.pass_through = pass_through

    def draw(self):
        cx, cy, w, h = self.center_x, self.center_y, self.width, self.height
        if self.pass_through:
            body, edge = COLOR_PLATFORM_SOFT, COLOR_PLATFORM_SOFT_EDGE
        else:
            body, edge = COLOR_PLATFORM_MAIN, COLOR_PLATFORM_MAIN_EDGE

        # Shadow / depth
        draw_filled_rectangle(cx, cy - 4, w + 6, h + 4, (0, 0, 0, 100))
        # Body
        draw_filled_rectangle(cx, cy, w, h, body)
        # Top highlight strip
        draw_filled_rectangle(cx, cy + h / 2 - 4, w, 5, edge)
        # Outline
        draw_rectangle_outline(cx, cy, w, h, edge, 2)

    @property
    def top(self):
        return self.center_y + self.height / 2

    @property
    def bottom(self):
        return self.center_y - self.height / 2

    @property
    def left(self):
        return self.center_x - self.width / 2

    @property
    def right(self):
        return self.center_x + self.width / 2