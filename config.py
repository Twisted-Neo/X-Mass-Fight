"""Central configuration: window, physics, combat, colors, animation specs."""

from pathlib import Path

# --- Window ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_TITLE = "X-Mass-Fight: Holiday Brawl - Ultimate Edition"

# --- Fixed timestep ---
PHYSICS_STEP = 1.0 / 60.0
MAX_FRAME_TIME = 0.25
MAX_STEPS_PER_FRAME = 5

# --- Physics (tuned at 60 fps) ---
GRAVITY = 0.70
MAX_FALL_SPEED = 16.0
FAST_FALL_SPEED = 24.0
JUMP_SPEED = 16.5
DOUBLE_JUMP_SPEED = 15.5
GROUND_ACCELERATION = 2.6
AIR_ACCELERATION = 1.5
GROUND_FRICTION = 0.82
AIR_FRICTION = 0.95
MAX_RUN_SPEED = 9.5

JUMP_BUFFER_FRAMES = 7
COYOTE_TIME_FRAMES = 7

# --- Combat & Shield ---
BASE_DAMAGE = 7.0
BASE_KNOCKBACK_X = 6.5
BASE_KNOCKBACK_Y = 6.0
KNOCKBACK_DAMAGE_SCALE = 1.0 / 40.0
HITSTUN_BASE = 10
HITSTOP_FRAMES = 6
HIT_FLASH_FRAMES = 6
INVINCIBLE_HIT_FRAMES = 15
ATTACK_DURATION = 14
ATTACK_COOLDOWN = 5
ATTACK_REACH = 75
ATTACK_HITBOX_W = 100
ATTACK_HITBOX_H = 70

SHIELD_MAX_HEALTH = 100.0
SHIELD_REGEN = 0.4
SHIELD_DRAIN = 1.5

BLAST_ZONE = 300

# --- Assets ---
ASSET_PATH = Path(__file__).resolve().parent / "assets"

ANIM_SPECS = {
    "IDLE":    ("Xteve-Idle.png", 6, 4),
    "WALKING": ("Xteve-Walk.png", 6, 4),
    "JUMPING": ("Xteve-Jump.png", 6, 4),
    "FALLING": ("Xteve-Fall.png", 6, 4),
    "LANDING": ("Xteve-Land.png", 6, 4),
    "SIT":     ("Xteve-Sit.png",  1, 1),
    "HIT":     ("Xteve-Hit.png",  1, 1),
}

ANIM_FRAMES = {k: None for k in ANIM_SPECS}

ANIM_SPEED = {
    "IDLE":    0.10,
    "WALKING": 0.033,
    "JUMPING": 0.033,
    "FALLING": 0.050,
    "LANDING": 0.033,
    "SIT":     0.15,
    "HIT":     0.050,
}

# --- Colors (RGBA) ---
COLOR_BG_TOP        = (10, 14, 32, 255)
COLOR_BG_BOTTOM     = (45, 20, 65, 255)
COLOR_STAR          = (255, 255, 255, 255)
COLOR_MOON          = (245, 245, 225, 255)
COLOR_AURORA_A      = (50, 230, 150)
COLOR_AURORA_B      = (130, 100, 245)
COLOR_SNOW          = (255, 255, 255, 255)
COLOR_PLATFORM_MAIN = (180, 35, 55, 255)
COLOR_PLATFORM_MAIN_EDGE = (255, 110, 130, 255)
COLOR_PLATFORM_SOFT = (50, 150, 110, 255)
COLOR_PLATFORM_SOFT_EDGE = (120, 235, 190, 255)
COLOR_HUD_BG        = (15, 18, 30, 225)
COLOR_HUD_BORDER    = (70, 85, 110, 255)
COLOR_HUD_P1        = (235, 65, 75, 255)
COLOR_HUD_P2        = (65, 210, 130, 255)
COLOR_SHIELD        = (100, 180, 255, 140)
COLOR_TEXT          = (245, 245, 250, 255)
COLOR_TEXT_DIM      = (160, 170, 195, 255)
COLOR_GOLD          = (255, 215, 75, 255)
COLOR_HITBOX_DEBUG  = (255, 240, 0, 255)
COLOR_HIT_FLASH     = (255, 140, 140, 255)
COLOR_HIT_SPARKS    = [
    (255, 245, 160, 255),
    (255, 205, 90, 255),
    (255, 150, 60, 255),
]
COLOR_KO_SPARKS = [
    (255, 90, 90, 255),
    (255, 210, 90, 255),
    (255, 255, 210, 255),
]

HEART_CHAR = "\u2665"
DEBUG_HITBOXES = False