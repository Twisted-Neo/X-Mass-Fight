"""Persistent display, graphics (Bloom), keybind, and named control preset management."""

import json
from pathlib import Path
import arcade

from config import WINDOW_HEIGHT, WINDOW_WIDTH

SETTINGS_FILE = Path("settings.json")
MAX_PRESET_NAME_LEN = 22

DISPLAY_MODES: list[tuple[str, str]] = [
    ("windowed", "Windowed"),
    ("borderless", "Borderless Fullscreen"),
    ("fullscreen", "Exclusive Fullscreen"),
]

STANDARD_RESOLUTIONS: list[tuple[int, int]] = [
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
]

ACTION_SPECS: list[tuple[str, str]] = [
    ("left", "Move Left"),
    ("right", "Move Right"),
    ("up", "Up / Aim Up"),
    ("down", "Down / Fast Fall"),
    ("jump", "Jump"),
    ("attack", "Attack"),
    ("heavy", "Heavy / Dash"),
    ("shield", "Shield / Tech"),
]

DEFAULT_P1_PRESET = "P1 Classic (WASD)"
DEFAULT_P2_PRESET = "P2 Classic (Arrows)"

BUILTIN_PRESETS: dict[str, dict[str, int]] = {
    "P1 Classic (WASD)": {
        "left": arcade.key.A,
        "right": arcade.key.D,
        "up": arcade.key.W,
        "down": arcade.key.S,
        "jump": arcade.key.SPACE,
        "attack": arcade.key.J,
        "heavy": arcade.key.K,
        "shield": arcade.key.L,
    },
    "P1 Compact (TFGH)": {
        "left": arcade.key.F,
        "right": arcade.key.H,
        "up": arcade.key.T,
        "down": arcade.key.G,
        "jump": arcade.key.SPACE,
        "attack": arcade.key.Z,
        "heavy": arcade.key.X,
        "shield": arcade.key.C,
    },
    "P2 Classic (Arrows)": {
        "left": arcade.key.LEFT,
        "right": arcade.key.RIGHT,
        "up": arcade.key.UP,
        "down": arcade.key.DOWN,
        "jump": arcade.key.RSHIFT,
        "attack": arcade.key.NUM_1,
        "heavy": arcade.key.NUM_2,
        "shield": arcade.key.NUM_3,
    },
    "P2 Laptop (Arrows + ,./)": {
        "left": arcade.key.LEFT,
        "right": arcade.key.RIGHT,
        "up": arcade.key.UP,
        "down": arcade.key.DOWN,
        "jump": arcade.key.RSHIFT,
        "attack": arcade.key.COMMA,
        "heavy": arcade.key.PERIOD,
        "shield": arcade.key.SLASH,
    },
}

_FRIENDLY_KEY_NAMES: dict[int, str] = {
    arcade.key.UP: "UP",
    arcade.key.DOWN: "DOWN",
    arcade.key.LEFT: "LEFT",
    arcade.key.RIGHT: "RIGHT",
    arcade.key.SPACE: "SPACE",
    arcade.key.ENTER: "ENTER",
    arcade.key.RETURN: "ENTER",
    arcade.key.TAB: "TAB",
    arcade.key.BACKSPACE: "BACKSPACE",
    arcade.key.LSHIFT: "L-SHIFT",
    arcade.key.RSHIFT: "R-SHIFT",
    arcade.key.LCTRL: "L-CTRL",
    arcade.key.RCTRL: "R-CTRL",
    arcade.key.LALT: "L-ALT",
    arcade.key.RALT: "R-ALT",
    arcade.key.COMMA: ",",
    arcade.key.PERIOD: ".",
    arcade.key.SLASH: "/",
    arcade.key.SEMICOLON: ";",
    arcade.key.APOSTROPHE: "'",
    arcade.key.BRACKETLEFT: "[",
    arcade.key.BRACKETRIGHT: "]",
    arcade.key.BACKSLASH: "\\",
    arcade.key.MINUS: "-",
    arcade.key.EQUAL: "=",
    arcade.key.NUM_0: "NUM 0",
    arcade.key.NUM_1: "NUM 1",
    arcade.key.NUM_2: "NUM 2",
    arcade.key.NUM_3: "NUM 3",
    arcade.key.NUM_4: "NUM 4",
    arcade.key.NUM_5: "NUM 5",
    arcade.key.NUM_6: "NUM 6",
    arcade.key.NUM_7: "NUM 7",
    arcade.key.NUM_8: "NUM 8",
    arcade.key.NUM_9: "NUM 9",
    arcade.key.NUM_ENTER: "NUM ENTER",
    arcade.key.NUM_ADD: "NUM +",
    arcade.key.NUM_SUBTRACT: "NUM -",
    arcade.key.NUM_MULTIPLY: "NUM *",
    arcade.key.NUM_DIVIDE: "NUM /",
    arcade.key.NUM_DECIMAL: "NUM .",
}

_REVERSE_KEY_LOOKUP: dict[int, str] = {}
for _attr in dir(arcade.key):
    if _attr.startswith("_") or _attr.startswith("MOD_"):
        continue
    _val = getattr(arcade.key, _attr)
    if isinstance(_val, int) and _val not in _REVERSE_KEY_LOOKUP:
        _REVERSE_KEY_LOOKUP[_val] = _attr.replace("_", " ")


def key_name(key_code: int) -> str:
    """Converts an Arcade key constant into a readable uppercase label."""
    if key_code in _FRIENDLY_KEY_NAMES:
        return _FRIENDLY_KEY_NAMES[key_code]
    if key_code in _REVERSE_KEY_LOOKUP:
        return _REVERSE_KEY_LOOKUP[key_code]
    return f"KEY {key_code}"


def get_available_resolutions(window: arcade.Window | None = None) -> list[tuple[int, int]]:
    """Returns supported window resolutions up to the active monitor's native size."""
    resolutions = list(STANDARD_RESOLUTIONS)
    scr = getattr(window, "screen", None) if window is not None else None
    if scr is not None:
        max_w = int(getattr(scr, "width", WINDOW_WIDTH))
        max_h = int(getattr(scr, "height", WINDOW_HEIGHT))
        filtered = [r for r in resolutions if r[0] <= max_w and r[1] <= max_h]
        if (max_w, max_h) not in filtered:
            filtered.append((max_w, max_h))
        if filtered:
            resolutions = sorted(set(filtered), key=lambda r: (r[0], r[1]))
    return resolutions


def _sanitize_controls(raw: dict | None, fallback: dict[str, int]) -> dict[str, int]:
    cleaned = dict(fallback)
    if isinstance(raw, dict):
        for act_id, _ in ACTION_SPECS:
            val = raw.get(act_id)
            if isinstance(val, int) and val > 0:
                cleaned[act_id] = val
    return cleaned


class Settings:
    """Singleton configuration manager persisted to settings.json."""

    def __init__(self):
        self.display_mode: str = "windowed"
        self.resolution: tuple[int, int] = (1280, 720)
        self.bloom_enabled: bool = True

        self.p1_preset: str = DEFAULT_P1_PRESET
        self.p2_preset: str = DEFAULT_P2_PRESET
        self.p1_controls: dict[str, int] = dict(BUILTIN_PRESETS[DEFAULT_P1_PRESET])
        self.p2_controls: dict[str, int] = dict(BUILTIN_PRESETS[DEFAULT_P2_PRESET])
        self.custom_presets: dict[str, dict[str, int]] = {}

        self.load()

    def display_mode_label(self) -> str:
        for mode_id, label in DISPLAY_MODES:
            if mode_id == self.display_mode:
                return label
        return "Windowed"

    def all_presets(self) -> dict[str, dict[str, int]]:
        merged: dict[str, dict[str, int]] = {}
        for name, mapping in BUILTIN_PRESETS.items():
            merged[name] = dict(mapping)
        for name, mapping in self.custom_presets.items():
            merged[name] = dict(mapping)
        return merged

    def is_custom_preset(self, preset_name: str) -> bool:
        return preset_name in self.custom_presets

    def _find_matching_preset_name(self, controls: dict[str, int]) -> str | None:
        for name, mapping in self.all_presets().items():
            if all(controls.get(act) == mapping.get(act) for act, _ in ACTION_SPECS):
                return name
        return None

    def cycle_preset(self, player_num: int, step: int) -> str:
        presets = self.all_presets()
        names = list(presets.keys())
        current = self.p1_preset if player_num == 1 else self.p2_preset

        if current in names:
            idx = (names.index(current) + step) % len(names)
        else:
            idx = 0 if step >= 0 else len(names) - 1

        chosen = names[idx]
        mapping = dict(presets[chosen])
        if player_num == 1:
            self.p1_preset = chosen
            self.p1_controls = mapping
        else:
            self.p2_preset = chosen
            self.p2_controls = mapping

        self.save()
        return chosen

    def save_preset(self, player_num: int, raw_name: str) -> tuple[bool, str]:
        name = " ".join(raw_name.strip().split())[:MAX_PRESET_NAME_LEN]
        if not name:
            return False, "Preset name cannot be empty."
        if name in BUILTIN_PRESETS or name.lower() == "custom":
            return False, f"'{name}' is a reserved preset name — pick another name."

        controls = dict(self.p1_controls if player_num == 1 else self.p2_controls)
        self.custom_presets[name] = controls

        if player_num == 1:
            self.p1_preset = name
        else:
            self.p2_preset = name

        # Refresh the other player's preset label if their bindings now match this preset
        other_controls = self.p2_controls if player_num == 1 else self.p1_controls
        if all(other_controls.get(a) == controls.get(a) for a, _ in ACTION_SPECS):
            if player_num == 1:
                self.p2_preset = name
            else:
                self.p1_preset = name

        self.save()
        return True, f"Saved custom preset '{name}'!"

    def delete_preset(self, preset_name: str) -> tuple[bool, str]:
        if preset_name not in self.custom_presets:
            return False, "Built-in presets cannot be deleted."

        del self.custom_presets[preset_name]

        if self.p1_preset == preset_name:
            self.p1_preset = DEFAULT_P1_PRESET
            self.p1_controls = dict(BUILTIN_PRESETS[DEFAULT_P1_PRESET])
        if self.p2_preset == preset_name:
            self.p2_preset = DEFAULT_P2_PRESET
            self.p2_controls = dict(BUILTIN_PRESETS[DEFAULT_P2_PRESET])

        self.save()
        return True, f"Deleted custom preset '{preset_name}'."

    def bind_key(self, player_num: int, action_id: str, key: int) -> str:
        controls = self.p1_controls if player_num == 1 else self.p2_controls
        old_key = controls.get(action_id)

        # If this key is already assigned to another action on the same player, swap them cleanly
        swapped_with = None
        for other_act, other_label in ACTION_SPECS:
            if other_act != action_id and controls.get(other_act) == key and old_key is not None:
                controls[other_act] = old_key
                swapped_with = other_label
                break

        controls[action_id] = key

        matched = self._find_matching_preset_name(controls)
        preset_label = matched if matched is not None else "Custom"
        if player_num == 1:
            self.p1_preset = preset_label
        else:
            self.p2_preset = preset_label

        self.save()
        if swapped_with:
            return f"Bound to {key_name(key)} (swapped with {swapped_with})"
        return f"Bound to {key_name(key)}"

    def reset_defaults(self):
        self.display_mode = "windowed"
        self.resolution = (1280, 720)
        self.bloom_enabled = True
        self.p1_preset = DEFAULT_P1_PRESET
        self.p2_preset = DEFAULT_P2_PRESET
        self.p1_controls = dict(BUILTIN_PRESETS[DEFAULT_P1_PRESET])
        self.p2_controls = dict(BUILTIN_PRESETS[DEFAULT_P2_PRESET])
        self.save()

    def apply_display(self, window: arcade.Window | None):
        """Applies display mode and window resolution safely to the Arcade window."""
        if window is None:
            return
        try:
            if self.display_mode == "borderless":
                if not window.fullscreen:
                    window.set_fullscreen(True)
            elif self.display_mode == "fullscreen":
                rw, rh = self.resolution
                try:
                    window.set_fullscreen(True, width=rw, height=rh)
                except TypeError:
                    window.set_fullscreen(True)
            else:
                if window.fullscreen:
                    window.set_fullscreen(False)
                rw, rh = self.resolution
                window.set_size(rw, rh)
                if hasattr(window, "center_window"):
                    window.center_window()
        except Exception:
            pass

        if hasattr(window, "sync_default_camera"):
            window.sync_default_camera()

    def load(self):
        if not SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return

        valid_modes = {m[0] for m in DISPLAY_MODES}
        mode = data.get("display_mode")
        if mode in valid_modes:
            self.display_mode = mode

        res = data.get("resolution")
        if (
            isinstance(res, (list, tuple))
            and len(res) == 2
            and isinstance(res[0], int)
            and isinstance(res[1], int)
            and res[0] >= 640
            and res[1] >= 360
        ):
            self.resolution = (res[0], res[1])

        self.bloom_enabled = bool(data.get("bloom_enabled", True))

        raw_custom = data.get("custom_presets")
        if isinstance(raw_custom, dict):
            loaded_custom: dict[str, dict[str, int]] = {}
            for raw_name, raw_map in raw_custom.items():
                if not isinstance(raw_name, str):
                    continue
                clean_name = " ".join(raw_name.strip().split())[:MAX_PRESET_NAME_LEN]
                if not clean_name or clean_name in BUILTIN_PRESETS or clean_name.lower() == "custom":
                    continue
                loaded_custom[clean_name] = _sanitize_controls(raw_map, BUILTIN_PRESETS[DEFAULT_P1_PRESET])
            self.custom_presets = loaded_custom

        self.p1_controls = _sanitize_controls(data.get("p1_controls"), BUILTIN_PRESETS[DEFAULT_P1_PRESET])
        self.p2_controls = _sanitize_controls(data.get("p2_controls"), BUILTIN_PRESETS[DEFAULT_P2_PRESET])

        all_p = self.all_presets()
        p1_p = data.get("p1_preset")
        p2_p = data.get("p2_preset")
        self.p1_preset = p1_p if isinstance(p1_p, str) and (p1_p in all_p or p1_p == "Custom") else (
            self._find_matching_preset_name(self.p1_controls) or "Custom"
        )
        self.p2_preset = p2_p if isinstance(p2_p, str) and (p2_p in all_p or p2_p == "Custom") else (
            self._find_matching_preset_name(self.p2_controls) or "Custom"
        )

    def save(self):
        payload = {
            "display_mode": self.display_mode,
            "resolution": [self.resolution[0], self.resolution[1]],
            "bloom_enabled": self.bloom_enabled,
            "p1_preset": self.p1_preset,
            "p2_preset": self.p2_preset,
            "p1_controls": self.p1_controls,
            "p2_controls": self.p2_controls,
            "custom_presets": self.custom_presets,
        }
        try:
            SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass


SETTINGS = Settings()