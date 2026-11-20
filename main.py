"""Entry point for X-Mass-Fight: Holiday Brawl."""

import arcade

from config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from settings import SETTINGS
from views import TitleView


class XMassFightWindow(arcade.Window):
    def __init__(self):
        init_w, init_h = SETTINGS.resolution
        super().__init__(
            init_w, init_h, WINDOW_TITLE,
            resizable=False, vsync=True,
            fullscreen=(SETTINGS.display_mode == "fullscreen"),
        )
        self.viewport_rect = arcade.LBWH(0, 0, self.width, self.height)
        SETTINGS.apply_display(self)
        self.on_resize(self.width, self.height)

    def sync_default_camera(self):
        """Locks default_camera to 1920x1080 logical coordinates centered in the active viewport."""
        self.default_camera.viewport = self.viewport_rect
        self.default_camera.projection = arcade.LRBT(
            -WINDOW_WIDTH * 0.5, WINDOW_WIDTH * 0.5,
            -WINDOW_HEIGHT * 0.5, WINDOW_HEIGHT * 0.5,
        )
        self.default_camera.position = (WINDOW_WIDTH * 0.5, WINDOW_HEIGHT * 0.5)

    def on_resize(self, width: int, height: int):
        """Maps the fixed 1920x1080 logical arena/UI space cleanly onto any physical resolution."""
        target_aspect = WINDOW_WIDTH / WINDOW_HEIGHT
        win_aspect = max(1, width) / max(1, height)

        if win_aspect > target_aspect:
            vp_h = height
            vp_w = int(round(height * target_aspect))
        else:
            vp_w = width
            vp_h = int(round(width / target_aspect))

        vp_x = (width - vp_w) // 2
        vp_y = (height - vp_h) // 2

        self.viewport_rect = arcade.LBWH(vp_x, vp_y, vp_w, vp_h)
        self.sync_default_camera()

        if self.current_view is not None:
            self.current_view.on_resize(width, height)

    def screen_to_virtual(self, x: float, y: float) -> tuple[float, float]:
        """Converts physical window mouse coordinates into 1920x1080 virtual coordinates."""
        vp = self.viewport_rect
        vx = ((x - vp.left) / max(1.0, float(vp.width))) * WINDOW_WIDTH
        vy = ((y - vp.bottom) / max(1.0, float(vp.height))) * WINDOW_HEIGHT
        return vx, vy


def main():
    window = XMassFightWindow()
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()