"""Persistent display, control bindings, and named control presets for X-Mass-Fight."""

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import arcade

from config import WINDOW_HEIGHT, WINDOW_WIDTH

SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"

DISPLAY_MODES: tuple[tuple[str, str], ...] = (
    ("windowed", "Windowed"),
    ("borderless", "Borderless Fullscreen"),
    ("fullscreen", "Fullscreen"),
)

BASE_RESOLUTIONS: tuple[tuple[int, int], ...] = (
    (1280, 720),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
)

ACTION_SPECS: tuple[tuple[str, str], ...] = (
    ("left", "Move Left"),
    ("right", "Move Right"),
    ("up", "Up / Tap Jump"),
    ("down", "Crouch / Fast Fall"),
    ("jump", "Jump"),
    ("attack", "Attack"),
    ("heavy", "Heavy / Air Dash"),
    ("shield", "Shield / Tech"),
)

DEFAULT_P1_CONTROLS: dict[str, int] = {
    "left": arcade.key.A,
    "right": arcade.key.D,
    "up": arcade.key.W,
    "down": arcade.key.S,
    "jump": arcade.key.SPACE,
    "attack": arcade.key.F,
    "heavy": arcade.key.G,
    "shield": arcade.key.E,
}

DEFAULT_P2_CONTROLS: dict[str, int] = {
    "left": arcade.key.LEFT,
    "right": arcade.key.RIGHT,
    "up": arcade.key.UP,
    "down": arcade.key.DOWN,
    "jump": arcade.key.RSHIFT,
    "attack": arcade.key.MINUS,
    "heavy": arcade.key.PERIOD,
    "shield": arcade.key.COMMA,
}

BUILTIN_PRESETS: dict[str, dict[str, int]] = {
    "Default P1": DEFAULT_P1_CONTROLS,
    "Default P2": DEFAULT_P2_CONTROLS,
}

MAX_PRESET_NAME_LEN = 18

_SPECIAL_KEY_NAMES: dict[int, str] = {
    arcade.key.SPACE: "Space",
    arcade.key.ENTER: "Enter",
    arcade.key.RETURN: "Enter",
    arcade.key.TAB: "Tab",
    arcade.key.BACKSPACE: "Backspace",
    arcade.key.DELETE: "Delete",
    arcade.key.INSERT: "Insert",
    arcade.key.HOME: "Home",
    arcade.key.END: "End",
    arcade.key.PAGEUP: "PgUp",
    arcade.key.PAGEDOWN: "PgDn",
    arcade.key.LSHIFT: "L-Shift",
    arcade.key.RSHIFT: "R-Shift",
    arcade.key.LCTRL: "L-Ctrl",
    arcade.key.RCTRL: "R-Ctrl",
    arcade.key.LALT: "L-Alt",
    arcade.key.RALT: "R-Alt",
    arcade.key.LEFT: "Left",
    arcade.key.RIGHT: "Right",
    arcade.key.UP: "Up",
    arcade.key.DOWN: "Down",
    arcade.key.MINUS: "-",
    arcade.key.EQUAL: "=",
    arcade.key.PERIOD: ".",
    arcade.key.COMMA: ",",
    arcade.key.SLASH: "/",
    arcade.key.BACKSLASH: "\\",
    arcade.key.SEMICOLON: ";",
    arcade.key.APOSTROPHE: "'",
    arcade.key.BRACKETLEFT: "[",
    arcade.key.BRACKETRIGHT: "]",
    arcade.key.GRAVE: "`",
    arcade.key.CAPSLOCK: "CapsLock",
}

_REVERSE_KEY_LOOKUP: dict[int, str] | None = None


def key_name(code: int) -> str:
    """Returns a clean human-readable label for an arcade.key code."""
    if code in _SPECIAL_KEY_NAMES:
        return _SPECIAL_KEY_NAMES[code]

    if arcade.key.A <= code <= arcade.key.Z:
        return chr(code).upper()
    if arcade.key.KEY_0 <= code <= arcade.key.KEY_9:
        return chr(code)
    if arcade.key.NUM_0 <= code <= arcade.key.NUM_9:
        return f"Num {code - arcade.key.NUM_0}"
    if arcade.key.F1 <= code <= arcade.key.F12:
        return f"F{code - arcade.key.F1 + 1}"

    global _REVERSE_KEY_LOOKUP
    if _REVERSE_KEY_LOOKUP is None:
        _REVERSE_KEY_LOOKUP = {
            val: name.replace("_", " ").title()
            for name, val in vars(arcade.key).items()
            if not name.startswith("_") and isinstance(val, int)
        }
    return _REVERSE_KEY_LOOKUP.get(code, f"Key({code})")


def get_available_resolutions(window: arcade.Window | None = None) -> list[tuple[int, int]]:
    """Returns standard 16:9 resolutions plus the active monitor's native resolution if unique."""
    res_list = list(BASE_RESOLUTIONS)
    if window is not None and getattr(window, "screen", None) is not None:
        native = (int(window.screen.width), int(window.screen.height))
        if native[0] >= 800 and native[1] >= 600 and native not in res_list:
            res_list.append(native)
            res_list.sort(key=lambda r: (r[0], r[1]))
    return res_list


def _set_win32_borderless(window: arcade.Window, borderless: bool, x: int, y: int, w: int, h: int) -> bool:
    """Toggles Win32 window chrome cleanly without recreating the OpenGL context."""
    if sys.platform != "win32":
        return False
    hwnd = getattr(window, "_hwnd", None)
    if not hwnd:
        return False

    try:
        user32 = ctypes.windll.user32
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL

        gwl_style = -16
        ws_overlappedwindow = 0x00CF0000
        ws_thickframe = 0x00040000
        ws_maximizebox = 0x00010000
        ws_popup = 0x80000000
        ws_visible = 0x10000000

        swp_framechanged = 0x0020
        swp_nozorder = 0x0004
        swp_noownerzorder = 0x0200

        style = (ws_popup | ws_visible) if borderless else (
            (ws_overlappedwindow & ~ws_thickframe & ~ws_maximizebox) | ws_visible
        )
        user32.SetWindowLongPtrW(hwnd, gwl_style, style)
        user32.SetWindowPos(
            hwnd, None, x, y, w, h,
            swp_framechanged | swp_nozorder | swp_noownerzorder,
        )
        return True
    except Exception:
        return False


def _sanitize_bindings(raw: object, fallback: dict[str, int]) -> dict[str, int]:
    cleaned = dict(fallback)
    if isinstance(raw, dict):
        for action, _ in ACTION_SPECS:
            val = raw.get(action)
            if isinstance(val, int) and val > 0:
                cleaned[action] = val
    return cleaned


class GameSettings:
    def __init__(self):
        self.display_mode: str = "windowed"  # "windowed" | "borderless" | "fullscreen"
        self.resolution: tuple[int, int] = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.p1_controls: dict[str, int] = dict(DEFAULT_P1_CONTROLS)
        self.p2_controls: dict[str, int] = dict(DEFAULT_P2_CONTROLS)
        self.custom_presets: dict[str, dict[str, int]] = {}
        self.p1_preset: str = "Default P1"
        self.p2_preset: str = "Default P2"
        self.load()

    def display_mode_label(self) -> str:
        for mode_id, label in DISPLAY_MODES:
            if mode_id == self.display_mode:
                return label
        return "Windowed"

    def get_all_preset_names(self) -> list[str]:
        return list(BUILTIN_PRESETS.keys()) + list(self.custom_presets.keys())

    def get_preset_bindings(self, name: str) -> dict[str, int] | None:
        if name in BUILTIN_PRESETS:
            return dict(BUILTIN_PRESETS[name])
        if name in self.custom_presets:
            return dict(self.custom_presets[name])
        return None

    def is_custom_preset(self, name: str) -> bool:
        return name in self.custom_presets

    def _detect_matching_preset(self, bindings: dict[str, int]) -> str:
        for name in self.get_all_preset_names():
            preset_map = self.get_preset_bindings(name)
            if preset_map == bindings:
                return name
        return "Custom"

    def load(self):
        if not SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return

        mode = data.get("display_mode")
        if mode in {m[0] for m in DISPLAY_MODES}:
            self.display_mode = mode

        res = data.get("resolution")
        if isinstance(res, list) and len(res) == 2 and all(isinstance(v, int) and v >= 640 for v in res):
            self.resolution = (res[0], res[1])

        self.p1_controls = _sanitize_bindings(data.get("p1_controls"), DEFAULT_P1_CONTROLS)
        self.p2_controls = _sanitize_bindings(data.get("p2_controls"), DEFAULT_P2_CONTROLS)

        saved_presets = data.get("presets")
        if isinstance(saved_presets, dict):
            for raw_name, raw_map in saved_presets.items():
                if not isinstance(raw_name, str):
                    continue
                clean_name = raw_name.strip()[:MAX_PRESET_NAME_LEN]
                if not clean_name or clean_name in BUILTIN_PRESETS or clean_name == "Custom":
                    continue
                self.custom_presets[clean_name] = _sanitize_bindings(raw_map, DEFAULT_P1_CONTROLS)

        saved_p1_preset = data.get("p1_preset")
        if isinstance(saved_p1_preset, str) and (saved_p1_preset in BUILTIN_PRESETS or saved_p1_preset in self.custom_presets):
            self.p1_preset = saved_p1_preset
        else:
            self.p1_preset = self._detect_matching_preset(self.p1_controls)

        saved_p2_preset = data.get("p2_preset")
        if isinstance(saved_p2_preset, str) and (saved_p2_preset in BUILTIN_PRESETS or saved_p2_preset in self.custom_presets):
            self.p2_preset = saved_p2_preset
        else:
            self.p2_preset = self._detect_matching_preset(self.p2_controls)

    def save(self):
        payload = {
            "display_mode": self.display_mode,
            "resolution": list(self.resolution),
            "p1_controls": self.p1_controls,
            "p2_controls": self.p2_controls,
            "p1_preset": self.p1_preset,
            "p2_preset": self.p2_preset,
            "presets": self.custom_presets,
        }
        try:
            SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def reset_defaults(self):
        self.display_mode = "windowed"
        self.resolution = (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.p1_controls = dict(DEFAULT_P1_CONTROLS)
        self.p2_controls = dict(DEFAULT_P2_CONTROLS)
        self.p1_preset = "Default P1"
        self.p2_preset = "Default P2"
        self.save()

    def apply_preset(self, player_num: int, preset_name: str) -> bool:
        bindings = self.get_preset_bindings(preset_name)
        if bindings is None:
            return False
        if player_num == 1:
            self.p1_controls = dict(bindings)
            self.p1_preset = preset_name
        else:
            self.p2_controls = dict(bindings)
            self.p2_preset = preset_name
        self.save()
        return True

    def cycle_preset(self, player_num: int, step: int = 1) -> str:
        names = self.get_all_preset_names()
        current = self.p1_preset if player_num == 1 else self.p2_preset
        if current in names:
            idx = (names.index(current) + step) % len(names)
        else:
            idx = 0 if step >= 0 else len(names) - 1
        chosen = names[idx]
        self.apply_preset(player_num, chosen)
        return chosen

    def save_preset(self, player_num: int, raw_name: str) -> tuple[bool, str]:
        clean = " ".join(raw_name.strip().split())[:MAX_PRESET_NAME_LEN]
        if not clean:
            return False, "Preset name cannot be empty."
        if clean in BUILTIN_PRESETS or clean.lower() == "custom":
            return False, f"'{clean}' is a reserved preset name."

        existed = clean in self.custom_presets
        source = self.p1_controls if player_num == 1 else self.p2_controls
        self.custom_presets[clean] = dict(source)

        if player_num == 1:
            self.p1_preset = clean
            if self.p2_preset == clean:
                self.p2_controls = dict(source)
        else:
            self.p2_preset = clean
            if self.p1_preset == clean:
                self.p1_controls = dict(source)

        self.save()
        verb = "Updated" if existed else "Saved"
        return True, f"{verb} preset '{clean}'!"

    def delete_preset(self, name: str) -> tuple[bool, str]:
        if name not in self.custom_presets:
            return False, "Built-in or unsaved presets cannot be deleted."
        del self.custom_presets[name]
        if self.p1_preset == name:
            self.p1_preset = "Custom"
        if self.p2_preset == name:
            self.p2_preset = "Custom"
        self.save()
        return True, f"Deleted preset '{name}'."

    def bind_key(self, player_num: int, action: str, new_key: int) -> str:
        """Binds new_key to (player_num, action), swapping if already used by the same player."""
        own = self.p1_controls if player_num == 1 else self.p2_controls
        other = self.p2_controls if player_num == 1 else self.p1_controls
        old_key = own[action]

        note = ""
        for act_id, act_label in ACTION_SPECS:
            if act_id != action and own.get(act_id) == new_key:
                own[act_id] = old_key
                note = f" (swapped with {act_label})"
                break

        for act_id, act_label in ACTION_SPECS:
            if other.get(act_id) == new_key:
                other_tag = "P2" if player_num == 1 else "P1"
                note = f" (also bound to {other_tag} {act_label})"
                break

        own[action] = new_key
        matched = self._detect_matching_preset(own)
        if player_num == 1:
            self.p1_preset = matched
        else:
            self.p2_preset = matched
        self.save()
        return f"Bound {key_name(new_key)}{note}"

    def apply_display(self, window: arcade.Window):
        """Applies display_mode and resolution to the live Arcade window."""
        screen = window.screen
        mon_w = int(screen.width) if screen else WINDOW_WIDTH
        mon_h = int(screen.height) if screen else WINDOW_HEIGHT
        mon_x = int(getattr(screen, "x", 0))
        mon_y = int(getattr(screen, "y", 0))

        req_w, req_h = self.resolution

        if self.display_mode == "fullscreen":
            if window.fullscreen:
                window.set_fullscreen(False)
            _set_win32_borderless(window, False, mon_x, mon_y, req_w, req_h)
            try:
                window.set_fullscreen(True, width=req_w, height=req_h)
            except Exception:
                window.set_fullscreen(True)
            window.on_resize(window.width, window.height)

        elif self.display_mode == "borderless":
            if window.fullscreen:
                window.set_fullscreen(False)
            if _set_win32_borderless(window, True, mon_x, mon_y, mon_w, mon_h):
                window.set_size(mon_w, mon_h)
                window.set_location(mon_x, mon_y)
            else:
                window.set_fullscreen(True)
            window.on_resize(window.width, window.height)

        else:  # "windowed"
            if window.fullscreen:
                window.set_fullscreen(False)
            w = min(req_w, mon_w)
            h = min(req_h, mon_h)
            cx = mon_x + max(0, (mon_w - w) // 2)
            cy = mon_y + max(0, (mon_h - h) // 2)
            _set_win32_borderless(window, False, cx, cy, w, h)
            window.set_size(w, h)
            window.set_location(cx, cy)
            window.on_resize(window.width, window.height)


SETTINGS = GameSettings()