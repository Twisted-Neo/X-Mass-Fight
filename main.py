"""Entry point for X-Mass-Fight: Holiday Brawl."""

import arcade

from config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from game_view import XMassFightView


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.show_view(XMassFightView())
    arcade.run()


if __name__ == "__main__":
    main()