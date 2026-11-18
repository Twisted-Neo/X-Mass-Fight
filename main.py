import arcade
import os
from PIL import Image

# --- Constants ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_TITLE = "X-Mass-Fight"

ANIMATION_FPS = 24

# Melee-like High-Performance Physics Constants
GRAVITY = 1.4
MAX_FALL_SPEED = 20.0
FAST_FALL_SPEED = 28.0
JUMP_SPEED = 24.0
GROUND_ACCELERATION = 3.0
AIR_ACCELERATION = 1.8
GROUND_FRICTION = 0.85
AIR_FRICTION = 0.96
MAX_WALK_SPEED = 8.0
MAX_RUN_SPEED = 14.0

# Clamp large delta_times (lag spikes, window drag, etc.)
MAX_DELTA_TIME = 1.0 / 30.0

# Asset Configuration
ASSET_PATH = "assets/"

# Cached spritesheet slices: (filename, columns, rows) -> [Texture, ...]
_ANIMATION_CACHE = {}


def load_animation_from_sheet(filename, columns, rows):
    """
    Bulletproof spritesheet slicer using Pillow and Arcade textures.
    Crops each frame precisely from the grid. Results are cached so the
    same sheet is never sliced twice (e.g. IDLE / JUMPING / FALLING).
    """
    key = (filename, columns, rows)
    cached = _ANIMATION_CACHE.get(key)
    if cached is not None:
        return cached

    full_path = os.path.join(ASSET_PATH, filename)
    textures = []

    try:
        pil_image = Image.open(full_path).convert("RGBA")
        sheet_width, sheet_height = pil_image.size
        frame_width = sheet_width // columns
        frame_height = sheet_height // rows

        for row in range(rows):
            for col in range(columns):
                box = (
                    col * frame_width,
                    row * frame_height,
                    (col + 1) * frame_width,
                    (row + 1) * frame_height,
                )
                frame_image = pil_image.crop(box)
                textures.append(arcade.Texture(
                    image=frame_image,
                    name=f"{filename}_{col}_{row}",
                ))

        print(f"Loaded {len(textures)} frames from {filename}")
    except Exception as e:
        print(f"Error loading spritesheet {full_path}: {e}")
        textures = [arcade.make_soft_square_texture(50, arcade.color.RED)]

    _ANIMATION_CACHE[key] = textures
    return textures


class Xteve(arcade.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.center_x = x
        self.center_y = y
        self.facing_right = True
        self._last_facing = True

        # Physics and Input States
        self.move_left = False
        self.move_right = False
        self.move_down = False
        self.jump_pressed = False

        # Load all animations
        idle_frames = load_animation_from_sheet("Xteve-Idle.png", 6, 4)
        walk_frames = load_animation_from_sheet("Xteve-Walk.png", 6, 4)
        jump_frames = load_animation_from_sheet("Xteve-Jump.png", 1, 1)
        fall_frames = load_animation_from_sheet("Xteve-Fall.png", 1, 1)
        land_frames = load_animation_from_sheet("Xteve-Land.png", 6, 4)
        sit_frames = load_animation_from_sheet("Xteve-Sit.png", 1, 1)
        hit_frames = load_animation_from_sheet("Xteve-Hit.png", 1, 1)
        
        self.animations = {
            "IDLE": idle_frames,
            "WALKING": walk_frames,
            "JUMPING": jump_frames,
            "FALLING": fall_frames,
            "LANDING": land_frames,
            "SIT": sit_frames,
            "HIT": hit_frames,
        }
        
        self.was_airborne = False

        # State Machine Initialization
        self.state = "IDLE"
        self.cur_texture_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 1.0 / ANIMATION_FPS  # seconds per frame

        # Set initial texture
        self.texture = self.animations["IDLE"][0]

        # Controller Setup
        self.joystick = None
        joysticks = arcade.get_joysticks()
        if joysticks:
            self.joystick = joysticks[0]
            self.joystick.open()

    def update_movement(self, physics_engine):
        """Applies competitive acceleration, friction, and gravity."""
        is_on_ground = physics_engine.can_jump()

        # Horizontal Acceleration
        accel = GROUND_ACCELERATION if is_on_ground else AIR_ACCELERATION
        friction = GROUND_FRICTION if is_on_ground else AIR_FRICTION

        if self.move_left:
            self.change_x -= accel
            self.facing_right = False
        elif self.move_right:
            self.change_x += accel
            self.facing_right = True
        else:
            self.change_x *= friction
            if abs(self.change_x) < 0.2:
                self.change_x = 0.0

        # Speed Limiting
        if self.change_x > MAX_RUN_SPEED:
            self.change_x = MAX_RUN_SPEED
        elif self.change_x < -MAX_RUN_SPEED:
            self.change_x = -MAX_RUN_SPEED

        # Vertical Gravity & Fast Fall
        if not is_on_ground:
            self.change_y -= GRAVITY
            max_fall = FAST_FALL_SPEED if self.move_down else MAX_FALL_SPEED
            if self.change_y < -max_fall:
                self.change_y = -max_fall

        # Jumping
        if self.jump_pressed:
            if is_on_ground:
                self.change_y = JUMP_SPEED
            self.jump_pressed = False

    def update_animation_state(self, delta_time, is_on_ground):
        """Manages state transitions, frame timing, and sprite direction."""
        # Check for landing transition from airborne
        if is_on_ground and self.was_airborne:
            new_state = "LANDING"
            self.cur_texture_index = 0
            self.animation_timer = 0.0
        elif self.state == "LANDING":
            # Keep playing LANDING animation until it finishes
            new_state = "LANDING"
        elif not is_on_ground:
            new_state = "JUMPING" if self.change_y > 0 else "FALLING"
        elif self.move_down:
            new_state = "SIT"
        elif abs(self.change_x) > 0.8:
            new_state = "WALKING"
        else:
            new_state = "IDLE"

        self.was_airborne = not is_on_ground

        if new_state != self.state:
            self.state = new_state
            if new_state != "LANDING":
                self.cur_texture_index = 0
                self.animation_timer = 0.0

        frames = self.animations.get(self.state, self.animations["IDLE"])

        # Safely handle Arcade 3.x scale tuple representation
        base_scale = self.scale[0] if isinstance(self.scale, tuple) else self.scale
        scale_mag = abs(base_scale)
        self.scale_x = scale_mag if self.facing_right else -scale_mag

        self.animation_timer += delta_time
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            if self.state == "LANDING":
                if self.cur_texture_index < len(frames) - 1:
                    self.cur_texture_index += 1
                else:
                    # Landing animation finished, transition out
                    self.state = "IDLE"
                    self.cur_texture_index = 0
            else:
                self.cur_texture_index = (self.cur_texture_index + 1) % len(frames)
            
            self.texture = frames[self.cur_texture_index]


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.DARK_MIDNIGHT_BLUE
        self.scene = None
        self.player = None
        self.physics_engine = None
        self.setup()

    def setup(self):
        self.scene = arcade.Scene()

        self.player = Xteve(WINDOW_WIDTH / 2, 400)
        self.scene.add_sprite("Player", self.player)

        self.scene.add_sprite_list("Platforms")

        ground = arcade.SpriteSolidColor(1000, 40, arcade.color.SNOW)
        ground.center_x = WINDOW_WIDTH / 2
        ground.center_y = 150
        self.scene.add_sprite("Platforms", ground)

        platforms_data = [
            (WINDOW_WIDTH / 3, 380, 350, 25),
            ((WINDOW_WIDTH / 3) * 2, 380, 350, 25),
            (WINDOW_WIDTH / 2, 600, 300, 25),
        ]
        for px, py, pw, ph in platforms_data:
            plat = arcade.SpriteSolidColor(pw, ph, arcade.color.LIGHT_BLUE)
            plat.center_x = px
            plat.center_y = py
            self.scene.add_sprite("Platforms", plat)

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player,
            platforms=self.scene["Platforms"],
        )

        # NOTE: push handlers onto the VIEW (this), not the Sprite.
        # The joy callbacks (on_joybutton_press, on_joyaxis_motion,
        # on_joyhat_motion) live on GameView — pushing them to Xteve
        # would leave the controller dead.
        if self.player.joystick:
            self.player.joystick.push_handlers(self)

    def on_show_view(self):
        arcade.set_background_color(self.background_color)

    def on_draw(self):
        self.clear()
        self.scene.draw()

    def on_update(self, delta_time):
        # Clamp to prevent tunneling and animation runaway on lag spikes
        if delta_time > MAX_DELTA_TIME:
            delta_time = MAX_DELTA_TIME

        self.player.update_movement(self.physics_engine)
        self.physics_engine.update()

        is_on_ground = self.physics_engine.can_jump()
        self.player.update_animation_state(delta_time, is_on_ground)

        # Fall-out recovery
        if self.player.center_y < -150:
            self.player.center_x = WINDOW_WIDTH / 2
            self.player.center_y = 700
            self.player.change_x = 0
            self.player.change_y = 0

        # Screen edge clamping
        if self.player.left < 0:
            self.player.left = 0
            self.player.change_x = 0
        elif self.player.right > WINDOW_WIDTH:
            self.player.right = WINDOW_WIDTH
            self.player.change_x = 0

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.A, arcade.key.LEFT):
            self.player.move_left = True
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.player.move_right = True
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.player.move_down = True
        elif key in (arcade.key.SPACE, arcade.key.W, arcade.key.UP):
            self.player.jump_pressed = True

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.A, arcade.key.LEFT):
            self.player.move_left = False
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.player.move_right = False
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.player.move_down = False

    def on_joybutton_press(self, joystick, button):
        if button == 0:
            self.player.jump_pressed = True

    def on_joyaxis_motion(self, joystick, axis, value):
        if axis == 0:
            if value < -0.3:
                self.player.move_left = True
                self.player.move_right = False
            elif value > 0.3:
                self.player.move_right = True
                self.player.move_left = False
            else:
                self.player.move_left = False
                self.player.move_right = False
        elif axis == 1:
            self.player.move_down = (value > 0.5)

    def on_joyhat_motion(self, joystick, hat_x, hat_y):
        self.player.move_left = (hat_x == -1)
        self.player.move_right = (hat_x == 1)
        self.player.move_down = (hat_y == -1)


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
