"""Spritesheet loading + slicing. Handles Arcade 2.x and 3.x Texture signature."""

from functools import lru_cache

import arcade
from PIL import Image

from config import ASSET_PATH, ANIM_SPECS


def _make_texture(image, name):
    try:
        return arcade.Texture(image=image, name=name)
    except TypeError:
        return arcade.Texture(name, image)


@lru_cache(maxsize=None)
def load_animation_from_sheet(filename, columns, rows):
    """Slice a spritesheet into frames. Row-major order (left→right, top→bottom)."""
    full_path = ASSET_PATH / filename
    try:
        with Image.open(full_path) as source:
            sheet = source.convert("RGBA")
            sw, sh = sheet.size

            # Guard: a 1x1 sprite erroneously given a 6x4 grid.
            if columns * rows > 1 and (sw % columns != 0 or sh % rows != 0):
                print(
                    f"Warning: {filename} {sw}x{sh} does not divide evenly "
                    f"into {columns}x{rows}. Treating as single frame."
                )
                return (_make_texture(sheet, f"{filename}_single"),)

            fw, fh = sw // columns, sh // rows
            if columns * rows > 1 and (fw < 20 or fh < 20):
                print(
                    f"Warning: {filename} frames are {fw}x{fh} — too small "
                    f"for {columns}x{rows}. Treating as single frame."
                )
                return (_make_texture(sheet, f"{filename}_single"),)

            frames = []
            for r in range(rows):
                for c in range(columns):
                    x, y = c * fw, r * fh
                    img = sheet.crop((x, y, x + fw, y + fh))
                    frames.append(_make_texture(img, f"{filename}_{c}_{r}"))
        print(f"Loaded {len(frames)} frames from {filename}")
        return tuple(frames)
    except (OSError, ValueError) as exc:
        print(f"Warning: could not load {full_path}: {exc}. Placeholder used.")
        ph = Image.new("RGBA", (60, 60), (220, 30, 30, 255))
        return (_make_texture(ph, f"{filename}_missing"),)


def load_all_animations():
    from config import ANIM_FRAMES
    result = {}
    for name, spec in ANIM_SPECS.items():
        frames = load_animation_from_sheet(*spec)
        limit = ANIM_FRAMES.get(name)
        if limit:
            frames = frames[:limit]
            print(f"Trimming {name} to {limit} of {len(frames)} frames")
        result[name] = frames
    return result