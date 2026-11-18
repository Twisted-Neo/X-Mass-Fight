"""Entry point for X-Mass-Fight: Holiday Brawl - Ultimate Edition."""

import arcade

from config import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH
from game_view import TitleScreenView


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, resizable=True)
    window.show_view(TitleScreenView())
    arcade.run()


if __name__ == "__main__":
    main()