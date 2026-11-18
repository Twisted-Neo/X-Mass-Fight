"""Cached Arcade 3.x texture & spritesheet pipeline with auto-trimming and procedural textures."""

from functools import lru_cache
import arcade
from PIL import Image, ImageDraw, ImageOps

from config import ASSET_PATH, BODY_ANIM_SPECS, COLOR_BG_BOTTOM, COLOR_BG_TOP, COLOR_MOON, WINDOW_HEIGHT, WINDOW_WIDTH


def _to_texture(pil_img: Image.Image, name: str) -> arcade.Texture:
    return arcade.Texture(pil_img, name=name)


def _slice_sheet(filename: str, cols: int, rows: int, trim_empty: bool = True) -> list[Image.Image]:
    path = ASSET_PATH / filename
    try:
        with Image.open(path) as src:
            sheet = src.convert("RGBA")
    except OSError:
        return [Image.new("RGBA", (32, 32), (220, 40, 40, 255))]

    sw, sh = sheet.size
    # Guard against single-frame sprites misconfigured as multi-cell grids
    if cols > 1 and rows > 1 and (sw < cols * 8 or sh < rows * 8):
        cols, rows = 1, 1

    if cols == 1 and rows == 1:
        return [sheet]

    fw, fh = sw // cols, sh // rows
    frames: list[Image.Image] = []
    for r in range(rows):
        for c in range(cols):
            cell = sheet.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
            if trim_empty and cell.getbbox() is None:
                continue
            frames.append(cell)

    return frames if frames else [sheet]


@lru_cache(maxsize=1)
def get_fighter_animations() -> dict:
    """Returns cached right & mirrored left texture tuples for all body states."""
    anims = {"RIGHT": {}, "LEFT": {}}
    for state, (filename, cols, rows, _) in BODY_ANIM_SPECS.items():
        # Keep all frames for body sheets so timing stays consistent; 1x1 sheets return 1 frame
        raw_frames = _slice_sheet(filename, cols, rows, trim_empty=(cols * rows > 1))
        right_tex = tuple(_to_texture(img, f"{state}_R_{i}") for i, img in enumerate(raw_frames))
        left_tex = tuple(_to_texture(ImageOps.mirror(img), f"{state}_L_{i}") for i, img in enumerate(raw_frames))
        anims["RIGHT"][state] = right_tex
        anims["LEFT"][state] = left_tex
    return anims


@lru_cache(maxsize=1)
def get_vfx_animations() -> dict:
    """Returns cached right & left texture tuples for attacks and charge lightning."""
    vfx = {"RIGHT": {}, "LEFT": {}}

    # Side Slash (5x2, 9 active frames)
    side_imgs = _slice_sheet("attackSide-Xteve.png", 5, 2, trim_empty=True)
    vfx["RIGHT"]["ATTACK_SIDE"] = tuple(_to_texture(im, f"atk_side_R_{i}") for i, im in enumerate(side_imgs))
    vfx["LEFT"]["ATTACK_SIDE"] = tuple(_to_texture(ImageOps.mirror(im), f"atk_side_L_{i}") for i, im in enumerate(side_imgs))

    # Up & Down Crescent Slash (5x2, 9 active frames -> full arc for UP, vertically flipped for DOWN)
    arc_imgs = _slice_sheet("attackUpDown-Xteve.png", 5, 2, trim_empty=True)
    vfx["RIGHT"]["ATTACK_UP"] = tuple(_to_texture(im, f"atk_up_R_{i}") for i, im in enumerate(arc_imgs))
    vfx["LEFT"]["ATTACK_UP"] = tuple(_to_texture(ImageOps.mirror(im), f"atk_up_L_{i}") for i, im in enumerate(arc_imgs))

    down_imgs = [ImageOps.flip(im) for im in arc_imgs]
    vfx["RIGHT"]["ATTACK_DOWN"] = tuple(_to_texture(im, f"atk_down_R_{i}") for i, im in enumerate(down_imgs))
    vfx["LEFT"]["ATTACK_DOWN"] = tuple(_to_texture(ImageOps.mirror(im), f"atk_down_L_{i}") for i, im in enumerate(down_imgs))

    # Heavy Smash (5x1)
    heavy_imgs = _slice_sheet("attackHeavy-Xteve.png", 5, 2, trim_empty=True)
    vfx["RIGHT"]["ATTACK_HEAVY"] = tuple(_to_texture(im, f"atk_heavy_R_{i}") for i, im in enumerate(heavy_imgs))
    vfx["LEFT"]["ATTACK_HEAVY"] = tuple(_to_texture(ImageOps.mirror(im), f"atk_heavy_L_{i}") for i, im in enumerate(heavy_imgs))

    # Charge Lightning (2x1 each)
    for stage, fname in (("WHITE", "ChargeW.png"), ("RED", "ChargeR.png"), ("BLUE", "ChargeB.png")):
        c_imgs = _slice_sheet(fname, 2, 1, trim_empty=False)
        vfx["RIGHT"][f"CHARGE_{stage}"] = tuple(_to_texture(im, f"chg_{stage}_R_{i}") for i, im in enumerate(c_imgs))
        vfx["LEFT"][f"CHARGE_{stage}"] = tuple(_to_texture(ImageOps.mirror(im), f"chg_{stage}_L_{i}") for i, im in enumerate(c_imgs))

    return vfx


@lru_cache(maxsize=1)
def get_soft_circle_texture() -> arcade.Texture:
    """Procedural soft-edged circle texture for GPU-batched particles, stars, and snow."""
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, size - 3, size - 3), fill=(255, 255, 255, 255))
    return _to_texture(img, "proc_soft_circle")


@lru_cache(maxsize=1)
def get_sky_backdrop_texture() -> arcade.Texture:
    """Pre-bakes the gradient sky and glowing moon into a single GPU texture."""
    # Render at 1/2 resolution for instant generation and smooth gradient interpolation
    w, h = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    img = Image.new("RGBA", (w, h))
    px = img.load()

    for y in range(h):
        t = y / max(1, h - 1)
        r = int(COLOR_BG_TOP[0] * (1.0 - t) + COLOR_BG_BOTTOM[0] * t)
        g = int(COLOR_BG_TOP[1] * (1.0 - t) + COLOR_BG_BOTTOM[1] * t)
        b = int(COLOR_BG_TOP[2] * (1.0 - t) + COLOR_BG_BOTTOM[2] * t)
        row_col = (r, g, b, 255)
        for x in range(w):
            px[x, y] = row_col

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    mx, my = int(w * 0.82), int(h * 0.22)  # PIL y=0 is top
    for rad in range(65, 20, -4):
        alpha = int(12 * (65 - rad) / 45)
        draw.ellipse((mx - rad, my - rad, mx + rad, my + rad), fill=(COLOR_MOON[0], COLOR_MOON[1], COLOR_MOON[2], alpha))
    draw.ellipse((mx - 21, my - 21, mx + 21, my + 21), fill=COLOR_MOON)
    draw.ellipse((mx - 11, my - 9, mx - 3, my - 1), fill=(210, 210, 195, 255))
    draw.ellipse((mx + 3, my + 1, mx + 9, my + 7), fill=(220, 220, 205, 255))

    combined = Image.alpha_composite(img, overlay)
    return _to_texture(combined, "proc_sky_backdrop")