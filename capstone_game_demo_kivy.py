import math
import os
import sys
from datetime import datetime, timezone

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle, PushMatrix, PopMatrix, Rotate
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty, BooleanProperty, ListProperty, ObjectProperty
import random
import time

# Game constants
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
FLOOR_HEIGHT = 150
PLAYER_X = 400.0

FLOOR_HEIGHT_RATIO = FLOOR_HEIGHT / WINDOW_HEIGHT
PLAYER_X_RATIO = PLAYER_X / WINDOW_WIDTH

# BASE_FLOOR_RATIO = 0.15

PLAYER_RADIUS = 40
GRAVITY = -1200  # pixels per second^2 (negative = pulls down)
JUMP_VELOCITY = 700  # initial jump velocity - tuned for feel

INITIAL_SPEED = 260  # pixels/second (how fast obstacles move left)
SPEED_INCREASE_PER_5_AVOIDED = 100  # speed increases incrementally for every 5 obstacles avoided
OBSTACLE_MIN_GAP = 350
OBSTACLE_MAX_GAP = 900
SPAWN_INTERVAL_BASE = 2.0  # base interval between obstacles (sec) - modified by speed

SLOW_ON_HIT_MULTIPLIER = 0.9  # speed multiplier upon hit
GAME_DURATION = 300  # 5 minute game duration

#SPAWN_PAUSE_ON_BG_SWITCH = 2.0  # pause obstacle spawning after background switches (sec)
OBSTACLE_PREVIEW_SECONDS = 5.5  # spawn NEXT theme obstacles this many seconds before bg switch


def _resource_path(relative_path):
    # helper to find resource path that works both in dev and when packaged with PyInstaller
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(sys._MEIPASS)

    repo_base = os.path.dirname(os.path.abspath(__file__))
    candidates.append(repo_base)
    candidates.append(os.path.join(repo_base, "areteDemo"))

    for base in candidates:
        path = os.path.join(base, relative_path)
        if os.path.exists(path):
            return path

    return os.path.join(repo_base, relative_path)


def lock_window_fullscreen():
    Window.fullscreen = "auto"
    Window.borderless = True


class Obstacle:
    def __init__(self, x, y, size, source, object_id):
        self.x = x
        self.y = y
        self.size = size
        self.source = source
        self.object_id = object_id
        self.passed = False


class GameWidget(Widget):
    speed = NumericProperty(INITIAL_SPEED)  # current world speed (px/s)
    base_speed = NumericProperty(INITIAL_SPEED)  # base target speed

    player_y = NumericProperty(0.0)  # center y of player
    player_vy = NumericProperty(0.0)
    player_x = NumericProperty(400.0)  # horizontal position of player (constant)
    player_radius = NumericProperty(PLAYER_RADIUS)

    is_running = BooleanProperty(False)
    is_counting_down = BooleanProperty(False)
    countdown_value = NumericProperty(0)

    obstacles = ListProperty([])
    score_distance = NumericProperty(0.0)
    avoided_count = NumericProperty(0)

    game_over = BooleanProperty(False)
    on_game_over_callback = ObjectProperty(None, allownone=True)

    def __init__(self, embedded=False, **kwargs):
        super().__init__(**kwargs)
        if not embedded:
            lock_window_fullscreen()
        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_resize=self._on_resize)

        self.is_active = True
        self.player_x = self.viewport_width * PLAYER_X_RATIO
        self.player_y = self.floor_height + PLAYER_RADIUS
        self._last_floor_height = self.floor_height

        self.player_color = [1, 1, 1, 1]

        self.player_sprite_sources = {
            "blue": _resource_path(os.path.join("images", "player_blue.png")),
            "green": _resource_path(os.path.join("images", "player_green.png")),
            "orange": _resource_path(os.path.join("images", "player_orange.png")),
            "red": _resource_path(os.path.join("images", "player_red.png")),
        }
        self.player_sprite = self.player_sprite_sources["blue"]

        self.is_flickering = False
        self.flicker_timer = 0.0
        self.flicker_interval = 0.1
        self.flicker_duration = 1.5
        self.player_visible = True

        self._spawn_accumulator = 0.0
        self._time = time.time()
        self._slow_start_speed = None
        self._slow_until = None

        self._last_speed_milestone = 0

        # Run telemetry tracking
        self._started_at_iso: str | None = None
        self._ended_at_iso: str | None = None
        self._hit_count = 0
        self._hit_object_ids = []
        self._next_obstacle_id = 1
        self._speed_max = float(INITIAL_SPEED)
        self._speed_sum = 0.0
        self._speed_samples = 0

        self.obstacle_sources = {
            0: _resource_path(os.path.join("images", "obstacle_sea.png")),
            1: _resource_path(os.path.join("images", "obstacle_forest.png")),
            2: _resource_path(os.path.join("images", "obstacle_desert.png")),
            3: _resource_path(os.path.join("images", "obstacle_sky.png")),
            4: _resource_path(os.path.join("images", "obstacle_space.png")),
        }

        self._spawn_pause_remaining = 0.0  # spawn pause timer

        # backgrounds
        self.backgrounds = [
            _resource_path(os.path.join("images", "background_sea.png")),
            _resource_path(os.path.join("images", "background_forest.png")),
            _resource_path(os.path.join("images", "background_desert.png")),
            _resource_path(os.path.join("images", "background_sky.png")),
            _resource_path(os.path.join("images", "background_space.png"))
        ]
        self.bg_index = 0
        self.bg_source = self.backgrounds[self.bg_index]

        # background switch timer
        self._bg_elapsed = 0.0
        self.BG_SWITCH_SECONDS = 20.0

        # UI labels
        self.label_countdown = Label(
            text="", font_size=56, color=(0, 0, 0, 1), bold=True
        )
        self.add_widget(self.label_countdown)
        self.hud = Label(
            text="", font_size=22, color=(0, 0, 0, 1), bold=True,
            halign="left", valign="middle"
        )
        self.add_widget(self.hud)
        self.msg = Label(
            text="Press SPACE or ENTER to start", font_size=26,
            color=(0, 0, 0, 1), bold=True, halign="center", valign="middle"
        )
        self.add_widget(self.msg)
        self._layout_overlay()

        Clock.schedule_interval(self.update, 1.0 / 60.0)
        Clock.schedule_once(lambda dt: self.sync_player_sprite_from_app_color(), 0)

    @property
    def viewport_width(self):
        return Window.width or WINDOW_WIDTH

    @property
    def viewport_height(self):
        return Window.height or WINDOW_HEIGHT

    @property
    def floor_height(self):
        return self.viewport_height * FLOOR_HEIGHT_RATIO

    def _layout_overlay(self):
        self.label_countdown.size = (240, 100)
        self.label_countdown.text_size = self.label_countdown.size
        self.label_countdown.center = (self.viewport_width / 2, self.viewport_height / 2)

        self.hud.size = (max(self.viewport_width - 20, 100), 40)
        self.hud.text_size = self.hud.size
        self.hud.pos = (10, self.viewport_height - self.hud.height - 10)

        self.msg.size = (self.viewport_width * 0.7, 120)
        self.msg.text_size = self.msg.size
        self.msg.center = (
            self.viewport_width / 2,
            self.viewport_height / 2 + self.viewport_height * 0.08,
        )

    def _on_resize(self, *_):
        previous_floor_height = getattr(self, "_last_floor_height", self.floor_height)
        vertical_clearance = max(self.player_y - previous_floor_height, PLAYER_RADIUS)

        self.player_x = self.viewport_width * PLAYER_X_RATIO
        if self.is_running or self.is_counting_down:
            self.player_y = max(self.floor_height + PLAYER_RADIUS, self.floor_height + vertical_clearance)
        else:
            self.player_y = self.floor_height + PLAYER_RADIUS

        self._last_floor_height = self.floor_height
        self._layout_overlay()

    def set_active(self, active):
        self.is_active = active

    def dispose(self):
        Window.unbind(on_key_down=self._on_key_down)
        Window.unbind(on_resize=self._on_resize)
        Clock.unschedule(self.update)

    def set_player_color(self, r, g, b, a=1):
        self.player_color = [r, g, b, a]

    
    def set_player_sprite(self, sprite_name):
        if sprite_name in self.player_sprite_sources:
            self.player_sprite = self.player_sprite_sources[sprite_name]

    # Check app.player_color and sync the sprite accordingly
    def _colors_match(self, a, b, tol=0.02):
        if len(a) != len(b):
            return False
        return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))

    def sync_player_sprite_from_app_color(self):
        app = App.get_running_app()
        app_color = list(getattr(app, "player_color", [1, 1, 1, 1]))

        color_to_sprite = {
            "blue": [0.3, 0.5, 1, 1],
            "green": [0.3, 1, 0.3, 1],
            "orange": [1.0, 0.6, 0.2, 1],
            "red": [1, 0.3, 0.3, 1],
        }

        for sprite_name, rgba in color_to_sprite.items():
            if self._colors_match(app_color, rgba):
                self.set_player_sprite(sprite_name)
                self.player_color = app_color
                return

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if not self.is_active:
            return
        if key not in (32, 13):
            return
        if not self.is_running and not self.is_counting_down and not self.game_over:
            self.msg.text = ""
            self.start_countdown(3)
        elif self.is_running and not self.game_over:
            if key == 32 and self.on_ground():
                self.player_vy = JUMP_VELOCITY
        elif self.game_over:
            self.reset_game()

    def start_countdown(self, seconds):
        self.countdown_value = seconds
        self.is_counting_down = True
        self.label_countdown.text = str(int(self.countdown_value))
        Clock.schedule_interval(self._countdown_tick, 1.0)

    def _countdown_tick(self, dt):
        self.countdown_value -= 1
        if self.countdown_value > 0:
            self.label_countdown.text = str(int(self.countdown_value))
            return True
        else:
            self.label_countdown.text = ""
            self.is_counting_down = False
            self.is_running = True
            self._time = time.time()
            self._started_at_iso = datetime.now(timezone.utc).isoformat()
            return False

    def reset_game(self):
        self.speed = INITIAL_SPEED
        self.base_speed = INITIAL_SPEED
        self.player_x = self.viewport_width * PLAYER_X_RATIO
        self.player_y = self.floor_height + PLAYER_RADIUS
        self.player_vy = 0.0

        self.obstacles = []
        self._spawn_accumulator = 0.0

        self.score_distance = 0.0
        self.avoided_count = 0
        self.is_running = False
        self.is_counting_down = False
        self.game_over = False

        self.msg.text = "Press SPACE or ENTER to start"
        self.label_countdown.text = ""
        self.hud.text = ""
        self._slow_start_speed = None

        self._last_speed_milestone = 0
        self.bg_index = 0
        self.bg_source = self.backgrounds[self.bg_index]
        self._bg_elapsed = 0.0
        self._slow_until = None
        self._spawn_pause_remaining = 0.0
        self._last_floor_height = self.floor_height

        
        self.is_flickering = False
        self.flicker_timer = 0.0
        self.player_visible = True

        self._started_at_iso = None
        self._ended_at_iso = None
        self._hit_count = 0
        self._hit_object_ids = []
        self._next_obstacle_id = 1
        self._speed_max = float(INITIAL_SPEED)
        self._speed_sum = 0.0
        self._speed_samples = 0

        self.sync_player_sprite_from_app_color()
        self._layout_overlay()

    def on_ground(self):
        return abs(self.player_y - (self.floor_height + PLAYER_RADIUS)) < 1.0 and self.player_vy <= 0.0

    def spawn_obstacle(self):
        size = 70
        x = self.viewport_width + random.randint(0, 120)
        y = self.floor_height

        time_to_switch = self.BG_SWITCH_SECONDS - self._bg_elapsed
        if time_to_switch <= OBSTACLE_PREVIEW_SECONDS:
            preview_index = (self.bg_index + 1) % len(self.backgrounds)
        else:
            preview_index = self.bg_index

        src = self.obstacle_sources.get(
            preview_index,
            _resource_path(os.path.join("images", "obstacle_default.png"))
        )
        object_id = f"obstacle-{self._next_obstacle_id}"
        self._next_obstacle_id += 1
        self.obstacles.append(Obstacle(x, y, size, src, object_id))

    def update(self, dt):
        if dt <= 0:
            return

        # Continuously sync the sprite with the current app.player_color
        self.sync_player_sprite_from_app_color()

        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(
                pos=(0, 0),
                size=(self.viewport_width, self.viewport_height),
                source=self.bg_source
            )

        if self.is_running and not self.game_over:
            # Track speed telemetry every frame
            if self.speed > self._speed_max:
                self._speed_max = self.speed
            self._speed_sum += self.speed
            self._speed_samples += 1

            elapsed_time = time.time() - self._time
            if elapsed_time >= GAME_DURATION:
                self.end_game()
                return

            self._bg_elapsed += dt
            if self._bg_elapsed >= self.BG_SWITCH_SECONDS:
                self._bg_elapsed = 0.0
                self.bg_index = (self.bg_index + 1) % len(self.backgrounds)
                self.bg_source = self.backgrounds[self.bg_index]

            elapsed_time = time.time() - self._time
            if elapsed_time >= GAME_DURATION:
                self.end_game()
                return

            for ob in list(self.obstacles):
                ob.x -= self.speed * dt

            if self._spawn_pause_remaining > 0.0:
                self._spawn_pause_remaining -= dt
            else:
                spawn_interval = max(0.4, SPAWN_INTERVAL_BASE)
                self._spawn_accumulator += dt
                if self._spawn_accumulator >= spawn_interval:
                    self._spawn_accumulator = 0.0
                    self.spawn_obstacle()

            self.player_vy += GRAVITY * dt
            self.player_y += self.player_vy * dt

            if self.player_y < self.floor_height + PLAYER_RADIUS:
                self.player_y = self.floor_height + PLAYER_RADIUS
                self.player_vy = 0.0

            if self.avoided_count > 0 and (self.avoided_count % 5 == 0):
                self.base_speed = self.base_speed + SPEED_INCREASE_PER_5_AVOIDED

            self.score_distance += self.speed * dt

            # Update the flicker effect after a collision
            if self.is_flickering:
                self.flicker_timer -= dt
                if self.flicker_timer <= 0:
                    self.is_flickering = False
                    self.player_visible = True
                else:
                    blink_phase = int(self.flicker_timer / self.flicker_interval) % 2
                    self.player_visible = (blink_phase == 0)

            for ob in list(self.obstacles):
                ob_left = ob.x
                ob_right = ob.x + ob.size
                ob_bottom = ob.y
                ob_top = ob.y + ob.size

                cx = self.player_x
                cy = self.player_y

                nearest_x = max(ob_left, min(cx, ob_right))
                nearest_y = max(ob_bottom, min(cy, ob_top))
                dx = cx - nearest_x
                dy = cy - nearest_y

                if (dx * dx + dy * dy) <= (self.player_radius * self.player_radius):
                    try:
                        self.obstacles.remove(ob)
                    except ValueError:
                        pass

                    self._hit_count += 1
                    self._hit_object_ids.append(ob.object_id)

                    # Trigger the flicker effect when a collision happens
                    self.is_flickering = True
                    self.flicker_timer = self.flicker_duration
                    self.player_visible = False

                    self._slow_start_speed = self.speed
                    self.base_speed = self.base_speed
                    self.speed = self._slow_start_speed * SLOW_ON_HIT_MULTIPLIER
                    self._slow_start_speed = self.speed
                    if self.speed < 200:
                        self.speed = 200
                    break

            for ob in list(self.obstacles):
                if not ob.passed and (ob.x + ob.size) < 0:
                    ob.passed = True
                    self.avoided_count += 1
                    try:
                        self.obstacles.remove(ob)
                    except ValueError:
                        pass

        with self.canvas.before:
            for ob in self.obstacles:
                Color(1, 1, 1, 1)
                Rectangle(pos=(ob.x, ob.y), size=(ob.size, ob.size), source=ob.source)

            # Draw the player character sprite
            if self.player_visible:
                Color(1, 1, 1, 1)
                Rectangle(
                    pos=(self.player_x - self.player_radius, self.player_y - self.player_radius),
                    size=(self.player_radius * 2, self.player_radius * 2),
                    source=self.player_sprite
                )

        if not self.game_over:
            self.hud.text = f"Distance: {int(self.score_distance)}    Avoided: {self.avoided_count}"
        else:
            final_score = int(self.score_distance) + self.avoided_count * 100
            self.hud.text = f"FINAL - Score: {final_score}"

    def end_game(self):
        self.is_running = False
        self.game_over = True
        self._ended_at_iso = datetime.now(timezone.utc).isoformat()
        final_score = int(self.score_distance) + self.avoided_count * 100
        self.msg.text = f"Game Over - Score: {final_score}\nPress SPACE or ENTER to play again"
        if self.on_game_over_callback:
            self.on_game_over_callback()

    def build_run_summary(self) -> dict:
        now_iso = datetime.now(timezone.utc).isoformat()
        avg_speed = (self._speed_sum / self._speed_samples) if self._speed_samples > 0 else float(INITIAL_SPEED)
        obstacle_size = 70
        return {
            "started_at": self._started_at_iso or now_iso,
            "ended_at": self._ended_at_iso or now_iso,
            "score": int(self.score_distance) + self.avoided_count * 100,
            "objects_hit_total": self._hit_count,
            "hit_object_ids": list(self._hit_object_ids),
            "player_size_px2": round(math.pi * self.player_radius ** 2, 2),
            "obstacle_size_px2": float(obstacle_size * obstacle_size),
            "speed_start_pxps": float(INITIAL_SPEED),
            "speed_avg_pxps": round(avg_speed, 2),
            "speed_max_pxps": round(self._speed_max, 2),
            "speed_end_pxps": round(self.speed, 2),
        }


class CapstoneGameDemoApp(App):
    def build(self):
        lock_window_fullscreen()
        root = GameWidget()
        return root


if __name__ == '__main__':
    CapstoneGameDemoApp().run()
