"""Character definitions & unique weapon hitbox profiles.

All characters share the exact same physical/combat character hurtbox (FIGHTER_HURTBOX_W x FIGHTER_HURTBOX_H),
while each character can define custom weapon hitbox reach, width, height, offsets, and VFX scale.
To add a new character, drop '<CharId>-Idle.png', '<CharId>-Walk.png', etc. into assets/ and add a CharacterSpec below.
"""

from dataclasses import dataclass
from config import (
    ATTACK_HITBOX_H, ATTACK_HITBOX_W, ATTACK_REACH,
    SIDE_COMBO_HITBOX_MULT, TARGET_FIGHTER_HEIGHT,
)


@dataclass(frozen=True)
class WeaponHitboxSpec:
    """Defines a single attack's weapon hitbox, knockback/damage multipliers, and slash VFX size."""
    reach: float
    width: float
    height: float
    offset_y: float = 0.0
    damage_mult: float = 1.0
    kb_mult: float = 1.0
    vfx_size: float = 145.0
    vfx_reach_mult: float = 1.0
    vfx_offset_y: float = 0.0
    vertical_mode: str = "SIDE"  # "SIDE", "UP", or "DOWN"


@dataclass(frozen=True)
class CharacterSpec:
    char_id: str
    display_name: str
    title: str
    weapon_name: str
    summary: str
    reach_rating: int   # 1..5 for Character Select UI
    power_rating: int   # 1..5 for Character Select UI
    speed_rating: int   # 1..5 for Character Select UI
    visual_height: float = TARGET_FIGHTER_HEIGHT  # Visual sprite height only; hurtbox remains uniform
    weapons: dict[str, WeaponHitboxSpec] = None
    state_ground_offsets: dict[str, float] | None = None


CHARACTER_ROSTER: tuple[CharacterSpec, ...] = (
    CharacterSpec(
        char_id="Xteve",
        display_name="XTEVE",
        title="Frostblade All-Rounder",
        weapon_name="Candy Edge",
        summary="Balanced reach, reliable 2-hit side slash, and crisp aerial arcs.",
        reach_rating=3,
        power_rating=3,
        speed_rating=4,
        visual_height=84.0,
        weapons={
            "ATTACK_SIDE_1": WeaponHitboxSpec(
                reach=ATTACK_REACH,
                width=ATTACK_HITBOX_W,
                height=ATTACK_HITBOX_H,
                damage_mult=1.0,
                kb_mult=1.0,
                vfx_size=145.0,
            ),
            "ATTACK_SIDE_2": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.22,
                width=ATTACK_HITBOX_W * SIDE_COMBO_HITBOX_MULT,
                height=ATTACK_HITBOX_H * SIDE_COMBO_HITBOX_MULT,
                damage_mult=1.0,
                kb_mult=1.0,
                vfx_size=178.0,
                vfx_reach_mult=1.18,
                vfx_offset_y=4.0,
            ),
            "ATTACK_UP": WeaponHitboxSpec(
                reach=0.0,
                width=ATTACK_HITBOX_W,
                height=ATTACK_HITBOX_H * 1.15,
                offset_y=52.0,
                damage_mult=1.0,
                kb_mult=1.0,
                vfx_size=148.0,
                vfx_offset_y=74.0,
                vertical_mode="UP",
            ),
            "ATTACK_DOWN": WeaponHitboxSpec(
                reach=0.0,
                width=ATTACK_HITBOX_W,
                height=ATTACK_HITBOX_H * 1.15,
                offset_y=-52.0,
                damage_mult=1.0,
                kb_mult=1.0,
                vfx_size=148.0,
                vfx_offset_y=-74.0,
                vertical_mode="DOWN",
            ),
            "ATTACK_DASH": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.12,
                width=ATTACK_HITBOX_W * 1.24,
                height=ATTACK_HITBOX_H * 1.22,
                offset_y=4.0,
                damage_mult=1.0,
                kb_mult=1.05,
                vfx_size=172.0,
                vfx_reach_mult=1.08,
                vfx_offset_y=4.0,
            ),
            "ATTACK_HEAVY": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.20,
                width=ATTACK_HITBOX_W * 1.28,
                height=ATTACK_HITBOX_H * 1.28,
                offset_y=24.0,
                damage_mult=1.0,
                kb_mult=1.0,
                vfx_size=190.0,
                vfx_reach_mult=1.15,
                vfx_offset_y=48.0,
            ),
        },
    ),
    CharacterSpec(
        char_id="Xanta",
        display_name="XANTA",
        title="Heavy Gift-Sack Brawler",
        weapon_name="Toy-Sack Slam",
        summary="Oversized, tall weapon hitboxes with devastating knockback power.",
        reach_rating=4,
        power_rating=5,
        speed_rating=2,
        visual_height=96.0,  # Tall Santa hat extends visually above the uniform 84px character hurtbox
        state_ground_offsets={"LAUNCH": -12.0},
        weapons={
            "ATTACK_SIDE_1": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.06,
                width=ATTACK_HITBOX_W * 1.16,
                height=ATTACK_HITBOX_H * 1.24,
                offset_y=4.0,
                damage_mult=1.14,
                kb_mult=1.12,
                vfx_size=168.0,
                vfx_reach_mult=1.06,
            ),
            "ATTACK_SIDE_2": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.28,
                width=ATTACK_HITBOX_W * 1.44,
                height=ATTACK_HITBOX_H * 1.48,
                offset_y=6.0,
                damage_mult=1.16,
                kb_mult=1.15,
                vfx_size=204.0,
                vfx_reach_mult=1.24,
                vfx_offset_y=6.0,
            ),
            "ATTACK_UP": WeaponHitboxSpec(
                reach=0.0,
                width=ATTACK_HITBOX_W * 1.24,
                height=ATTACK_HITBOX_H * 1.28,
                offset_y=58.0,
                damage_mult=1.12,
                kb_mult=1.12,
                vfx_size=172.0,
                vfx_offset_y=80.0,
                vertical_mode="UP",
            ),
            "ATTACK_DOWN": WeaponHitboxSpec(
                reach=0.0,
                width=ATTACK_HITBOX_W * 1.26,
                height=ATTACK_HITBOX_H * 1.26,
                offset_y=-56.0,
                damage_mult=1.18,
                kb_mult=1.16,
                vfx_size=172.0,
                vfx_offset_y=-78.0,
                vertical_mode="DOWN",
            ),
            "ATTACK_DASH": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.16,
                width=ATTACK_HITBOX_W * 1.36,
                height=ATTACK_HITBOX_H * 1.38,
                offset_y=6.0,
                damage_mult=1.14,
                kb_mult=1.14,
                vfx_size=196.0,
                vfx_reach_mult=1.12,
                vfx_offset_y=6.0,
            ),
            "ATTACK_HEAVY": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.26,
                width=ATTACK_HITBOX_W * 1.46,
                height=ATTACK_HITBOX_H * 1.50,
                offset_y=28.0,
                damage_mult=1.18,
                kb_mult=1.18,
                vfx_size=224.0,
                vfx_reach_mult=1.22,
                vfx_offset_y=52.0,
            ),
        },
    ),
    CharacterSpec(
        char_id="Xcarf",
        display_name="XCARF",
        title="Long-Reach Scarf Striker",
        weapon_name="Crimson Whip",
        summary="Extended horizontal whip hitboxes with sleek, wide-sweeping arcs.",
        reach_rating=5,
        power_rating=3,
        speed_rating=5,
        visual_height=84.0,
        weapons={
            "ATTACK_SIDE_1": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.24,
                width=ATTACK_HITBOX_W * 1.26,
                height=ATTACK_HITBOX_H * 0.78,
                offset_y=-2.0,
                damage_mult=0.94,
                kb_mult=0.96,
                vfx_size=162.0,
                vfx_reach_mult=1.24,
            ),
            "ATTACK_SIDE_2": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.46,
                width=ATTACK_HITBOX_W * 1.54,
                height=ATTACK_HITBOX_H * 0.94,
                offset_y=0.0,
                damage_mult=0.96,
                kb_mult=1.04,
                vfx_size=196.0,
                vfx_reach_mult=1.42,
                vfx_offset_y=2.0,
            ),
            "ATTACK_UP": WeaponHitboxSpec(
                reach=0.0,
                width=ATTACK_HITBOX_W * 1.32,
                height=ATTACK_HITBOX_H * 1.02,
                offset_y=48.0,
                damage_mult=0.95,
                kb_mult=1.02,
                vfx_size=164.0,
                vfx_offset_y=70.0,
                vertical_mode="UP",
            ),
            "ATTACK_DOWN": WeaponHitboxSpec(
                reach=0.0,
                width=ATTACK_HITBOX_W * 0.86,
                height=ATTACK_HITBOX_H * 1.32,
                offset_y=-58.0,
                damage_mult=1.0,
                kb_mult=1.05,
                vfx_size=156.0,
                vfx_offset_y=-78.0,
                vertical_mode="DOWN",
            ),
            "ATTACK_DASH": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.34,
                width=ATTACK_HITBOX_W * 1.44,
                height=ATTACK_HITBOX_H * 1.08,
                offset_y=2.0,
                damage_mult=0.96,
                kb_mult=1.04,
                vfx_size=188.0,
                vfx_reach_mult=1.30,
                vfx_offset_y=2.0,
            ),
            "ATTACK_HEAVY": WeaponHitboxSpec(
                reach=ATTACK_REACH * 1.44,
                width=ATTACK_HITBOX_W * 1.52,
                height=ATTACK_HITBOX_H * 1.08,
                offset_y=20.0,
                damage_mult=1.02,
                kb_mult=1.06,
                vfx_size=212.0,
                vfx_reach_mult=1.38,
                vfx_offset_y=42.0,
            ),
        },
    ),
)

CHARACTER_BY_ID: dict[str, CharacterSpec] = {c.char_id: c for c in CHARACTER_ROSTER}


def get_character_spec(char_id: str) -> CharacterSpec:
    return CHARACTER_BY_ID.get(char_id, CHARACTER_ROSTER[0])