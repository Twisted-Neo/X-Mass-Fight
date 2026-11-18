"""Central configuration: window, physics, combat, colors, animation specs."""

from pathlib import Path

# --- Window ---
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
WINDOW_TITLE = "X-Mass-Fight: Holiday Brawl"

# --- Fixed timestep ---
PHYSICS_STEP = 1.0 / 60.0
MAX_FRAME_TIME = 0.25        # cap to avoid spiral-of-death on slow frames
MAX_STEPS_PER_FRAME = 5

# --- Physics (tuned at 60 fps) ---
GRAVITY = 0.70
MAX_FALL_SPEED = 16.0
FAST_FALL_SPEED = 22.0
JUMP_SPEED = 16.0
DOUBLE_JUMP_SPEED = 15.0
GROUND_ACCELERATION = 2.4
AIR_ACCELERATION = 1.4
GROUND_FRICTION = 0.82
AIR_FRICTION = 0.94
MAX_RUN_SPEED = 9.0

JUMP_BUFFER_FRAMES = 6
COYOTE_TIME_FRAMES = 6

# --- Combat ---
BASE_DAMAGE = 8.0
BASE_KNOCKBACK_X = 7.0
BASE_KNOCKBACK_Y = 6.0
KNOCKBACK_DAMAGE_SCALE = 1.0 / 45.0
HITSTUN_BASE = 9
HITSTOP_FRAMES = 5
HIT_FLASH_FRAMES = 6
INVINCIBLE_HIT_FRAMES = 12
ATTACK_DURATION = 14
ATTACK_COOLDOWN = 6
ATTACK_REACH = 55
ATTACK_HITBOX_W = 70
ATTACK_HITBOX_H = 46

BLAST_ZONE = 250

# --- Assets ---
ASSET_PATH = Path(__file__).resolve().parent / "assets"

# All 6x4 = 24 frames, except Hit and Sit which are 1x1.
ANIM_SPECS = {
    "IDLE":    ("Xteve-Idle.png", 6, 4),
    "WALKING": ("Xteve-Walk.png", 6, 4),
    "JUMPING": ("Xteve-Jump.png", 6, 4),
    "FALLING": ("Xteve-Fall.png", 6, 4),
    "LANDING": ("Xteve-Land.png", 6, 4),
    "SIT":     ("Xteve-Sit.png",  1, 1),
    "HIT":     ("Xteve-Hit.png",  1, 1),
}

ANIM_FRAMES = {
    "IDLE":    None,
    "WALKING": None,
    "JUMPING": None,
    "FALLING": None,
    "LANDING": None,
    "SIT":     None,
    "HIT":     None,
}

# Seconds per frame. Choosier states animate slowly, action ones quickly.
ANIM_SPEED = {
    "IDLE":    0.10,    #  6 steps = 10 fps (calm)
    "WALKING": 0.033,   #  2 steps = 30 fps (smooth)
    "JUMPING": 0.033,   #  2 steps = 30 fps
    "FALLING": 0.050,   #  3 steps = 20 fps
    "LANDING": 0.033,   #  2 steps = 30 fps
    "SIT":     0.15,    #  9 steps = 6.7 fps
    "HIT":     0.050,   #  3 steps = 20 fps
}

# --- Colors (RGBA) ---
COLOR_BG_TOP        = (10, 14, 30, 255)
COLOR_BG_BOTTOM     = (40, 18, 55, 255)
COLOR_STAR          = (255, 255, 255, 255)
COLOR_MOON          = (240, 240, 220, 255)
COLOR_AURORA_A      = (60, 220, 160)
COLOR_AURORA_B      = (140, 120, 230)
COLOR_SNOW          = (255, 255, 255, 255)
COLOR_PLATFORM_MAIN = (200, 40, 60, 255)
COLOR_PLATFORM_MAIN_EDGE = (255, 120, 140, 255)
COLOR_PLATFORM_SOFT = (60, 160, 120, 255)
COLOR_PLATFORM_SOFT_EDGE = (140, 240, 200, 255)
COLOR_HUD_BG        = (15, 18, 30, 210)
COLOR_HUD_BORDER    = (60, 70, 90, 255)
COLOR_HUD_P1        = (230, 70, 80, 255)
COLOR_HUD_P2        = (80, 220, 120, 255)
COLOR_TEXT          = (240, 240, 250, 255)
COLOR_TEXT_DIM      = (160, 170, 190, 255)
COLOR_GOLD          = (255, 210, 80, 255)
COLOR_HITBOX_DEBUG  = (255, 240, 0, 255)
COLOR_SWIPE         = (255, 255, 255, 220)
COLOR_HIT_FLASH     = (255, 120, 120, 255)
COLOR_LAND_DUST     = (220, 220, 235, 200)
COLOR_JUMP_PUFF     = (200, 220, 255, 180)
COLOR_HIT_SPARKS    = [
    (255, 240, 150, 255),
    (255, 200, 100, 255),
    (255, 160, 80, 255),
]
COLOR_KO_SPARKS = [
    (255, 100, 100, 255),
    (255, 200, 100, 255),
    (255, 255, 200, 255),
]

HEART_CHAR = "\u2665"

# --- Debug ---
DEBUG_HITBOXES = False