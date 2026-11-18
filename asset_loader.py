"""Spritesheet loading + slicing for body and attack animations."""

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
    full_path = ASSET_PATH / filename
    try:
        with Image.open(full_path) as source:
            sheet = source.convert("RGBA")
            sw, sh = sheet.size
            fw, fh = sw // columns, sh // rows
            frames = []
            for r in range(rows):
                for c in range(columns):
                    x, y = c * fw, r * fh
                    img = sheet.crop((x, y, x + fw, y + fh))
                    frames.append(_make_texture(img, f"{filename}_{c}_{r}"))
        return tuple(frames)
    except (OSError, ValueError):
        ph = Image.new("RGBA", (60, 60), (220, 30, 30, 255))
        return (_make_texture(ph, f"{filename}_missing"),)


@lru_cache(maxsize=None)
def load_attack_animations():
    result = {}

    # 1. Side Attacks (attackSide-Xteve.png - 5 columns, 2 rows)
    try:
        with Image.open(ASSET_PATH / "attackSide-Xteve.png") as img:
            sheet = img.convert("RGBA")
            sw, sh = sheet.size
            cols, rows = 5, 2
            fw, fh = sw // cols, sh // rows
            side_frames = []
            for r in range(rows):
                for c in range(cols):
                    cropped = sheet.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
                    side_frames.append(_make_texture(cropped, f"atk_side_{c}_{r}"))
            result["ATTACK_SIDE"] = tuple(side_frames)
    except Exception as e:
        print(f"Error loading attackSide-Xteve.png: {e}")
        ph = _make_texture(Image.new("RGBA", (60, 60), (220, 30, 30, 255)), "side_missing")
        result["ATTACK_SIDE"] = (ph,)

    # 2. Up & Down Attacks (attackUpDown-Xteve.png - 5 columns, 2 rows)
    try:
        with Image.open(ASSET_PATH / "attackUpDown-Xteve.png") as img:
            sheet = img.convert("RGBA")
            sw, sh = sheet.size
            cols, rows = 5, 2
            fw, fh = sw // cols, sh // rows
            up_frames = [
                _make_texture(sheet.crop((c * fw, 0, (c + 1) * fw, fh)), f"atk_up_{c}")
                for c in range(cols)
            ]
            down_frames = [
                _make_texture(sheet.crop((c * fw, fh, (c + 1) * fw, sh)), f"atk_down_{c}")
                for c in range(cols)
            ]
            result["ATTACK_UP"] = tuple(up_frames)
            result["ATTACK_DOWN"] = tuple(down_frames)
    except Exception as e:
        print(f"Error loading attackUpDown-Xteve.png: {e}")
        ph = _make_texture(Image.new("RGBA", (60, 60), (220, 30, 30, 255)), "updown_missing")
        result["ATTACK_UP"] = (ph,)
        result["ATTACK_DOWN"] = (ph,)

    # 3. Heavy Smash Attack (attackHeavy-Xteve.png - 5 columns, 1 row)
    try:
        with Image.open(ASSET_PATH / "attackHeavy-Xteve.png") as img:
            sheet = img.convert("RGBA")
            sw, sh = sheet.size
            cols, rows = 5, 1
            fw, fh = sw // cols, sh // rows
            heavy_frames = [
                _make_texture(sheet.crop((c * fw, 0, (c + 1) * fw, fh)), f"atk_heavy_{c}")
                for c in range(cols)
            ]
            result["ATTACK_HEAVY"] = tuple(heavy_frames)
    except Exception as e:
        print(f"Error loading attackHeavy-Xteve.png: {e}")
        ph = _make_texture(Image.new("RGBA", (60, 60), (220, 30, 30, 255)), "heavy_missing")
        result["ATTACK_HEAVY"] = (ph,)

    # 4. Charge Effects (ChargeW.png, ChargeR.png, ChargeB.png - 2 frames each)
    for color_name, filename in [("WHITE", "ChargeW.png"), ("RED", "ChargeR.png"), ("BLUE", "ChargeB.png")]:
        try:
            with Image.open(ASSET_PATH / filename) as img:
                sheet = img.convert("RGBA")
                sw, sh = sheet.size
                cols = 2
                fw, fh = sw // cols, sh
                charge_frames = [
                    _make_texture(sheet.crop((c * fw, 0, (c + 1) * fw, fh)), f"charge_{color_name}_{c}")
                    for c in range(cols)
                ]
                result[f"CHARGE_{color_name}"] = tuple(charge_frames)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            ph = _make_texture(Image.new("RGBA", (30, 30), (255, 255, 255, 255)), f"charge_{color_name}_missing")
            result[f"CHARGE_{color_name}"] = (ph, ph)

    return result


def load_all_animations():
    from config import ANIM_FRAMES
    result = {}
    for name, spec in ANIM_SPECS.items():
        frames = load_animation_from_sheet(*spec)
        if ANIM_FRAMES.get(name):
            frames = frames[:ANIM_FRAMES[name]]
        result[name] = frames
    return result