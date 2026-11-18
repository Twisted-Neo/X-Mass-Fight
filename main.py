"""Entry point for X-Mass-Fight: Holiday Brawl."""

import arcade

from config import TARGET_FPS, WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from views import TitleView


class XMassFightWindow(arcade.Window):
    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, resizable=False, vsync=True)
        self.set_update_rate(1.0 / TARGET_FPS)


def main():
    window = XMassFightWindow()
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()