import os
import sys

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

PLAYER_RADIUS = 18
GRAVITY = -1200          # pixels per second^2
JUMP_VELOCITY = 520      # initial jump velocity

INITIAL_SPEED = 240      # pixels/second
SPEED_INCREASE_PER_5_AVOIDED = 10
SPAWN_INTERVAL_BASE = 1.6

SLOW_ON_HIT_MULTIPLIER = 0.9
MAX_HEALTH = 6           # hits before game over
GAME_DURATION = 300      # 5 minutes (seconds)

# Points awarded per obstacle avoided
POINTS_PER_AVOID = 5
# Points awarded per second survived
POINTS_PER_SECOND = 0


def _resource_path(relative_path):
    """
    Return an absolute path to a bundled resource.

    - Frozen (.exe via PyInstaller): files land in sys._MEIPASS (the _internal
      temp directory), so we resolve relative to that.
    - Normal source run: resolve relative to this file's directory so that
      'images/background_sea.png' still works when running from areteDemo/.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


class Obstacle:
    """Simple struct for obstacles."""
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.passed = False


class GameWidget(Widget):
    speed        = NumericProperty(INITIAL_SPEED)
    base_speed   = NumericProperty(INITIAL_SPEED)

    player_y      = NumericProperty(0.0)
    player_vy     = NumericProperty(0.0)
    player_x      = NumericProperty(160.0)
    player_radius = NumericProperty(PLAYER_RADIUS)

    is_running      = BooleanProperty(False)
    is_counting_down = BooleanProperty(False)
    countdown_value  = NumericProperty(0)

    obstacles      = ListProperty([])
    score_distance = NumericProperty(0.0)
    avoided_count  = NumericProperty(0)
    live_score     = NumericProperty(0)   # displayed live score

    health         = NumericProperty(MAX_HEALTH)   # 6 → 0

    game_over             = BooleanProperty(False)
    on_game_over_callback = ObjectProperty(None, allownone=True)

    # ------------------------------------------------------------------ init
    def __init__(self, embedded=False, **kwargs):
        super().__init__(**kwargs)
        if not embedded:
            Window.size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        Window.bind(on_key_down=self._on_key_down)

        self.player_y     = FLOOR_HEIGHT + PLAYER_RADIUS
        self.player_color = [1, 1, 1, 1]

        self._last_spawn_x      = WINDOW_WIDTH + 100
        self._spawn_accumulator = 0.0
        self._time              = time.time()
        self._slow_start_speed  = None
        self._slow_until        = None
        self._last_speed_milestone = 0
        self._roll_angle        = 0.0
        self._last_clock_time   = Clock.get_time()

        # backgrounds cycle every 10 s — absolute paths work in both source
        # runs and the frozen .exe (PyInstaller _MEIPASS bundle)
        self.backgrounds = [
            _resource_path(os.path.join("images", "background_sea.png")),
            _resource_path(os.path.join("images", "background_forest.png")),
            _resource_path(os.path.join("images", "background_space.png")),
        ]
        self.bg_index   = 0
        self.bg_source  = self.backgrounds[self.bg_index]
        self._bg_elapsed = 0.0
        self.BG_SWITCH_SECONDS = 10.0

        # ---- UI labels ----
        self.label_countdown = Label(
            text="", font_size=56,
            pos=(0, 0),
            color=(1, 1, 1, 1), bold=True,
        )
        self.add_widget(self.label_countdown)

        # HUD: top-left  (score | avoided | timer)
        self.hud = Label(
            text="", font_size=24,
            pos=(10, 0),
            color=(1, 1, 1, 1), bold=True,
        )
        self.add_widget(self.hud)
        self.bind(pos=self._update_label_positions, size=self._update_label_positions)

        self.msg = Label(
            text="Press SPACE or ENTER to start", font_size=26,
            pos=(0, 0),
            color=(1, 1, 1, 1), bold=True,
        )
        self.add_widget(self.msg)

        Clock.schedule_interval(self.update, 1.0 / 60.0)

    # ------------------------------------------------------------------ color
    def set_player_color(self, r, g, b, a=1):
        self.player_color = [r, g, b, a]

    def _update_label_positions(self, *args):
        wx, wy = self.pos
        ww, wh = self.size
        # HUD sits 20% down from the top so it clears the app header bar
        self.hud.pos = (wx + 10, wy + wh * 0.78)
        self.msg.pos = (wx + ww / 2 - 220, wy + wh / 2 + 30)
        self.label_countdown.pos = (wx + ww / 2 - 60, wy + wh / 2 - 28)

    # ------------------------------------------------------------------ health bar colour helper
    @staticmethod
    def _health_color(health):
        """Return (r,g,b) based on remaining health out of MAX_HEALTH."""
        if health > MAX_HEALTH * 2 / 3:      # 5-6  green
            return (0.2, 0.85, 0.2)
        elif health > MAX_HEALTH / 3:         # 3-4  yellow
            return (1.0, 0.85, 0.0)
        else:                                  # 1-2  red
            return (0.9, 0.15, 0.15)

    # ------------------------------------------------------------------ input
    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
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

    # ------------------------------------------------------------------ countdown
    def start_countdown(self, seconds):
        self.countdown_value   = seconds
        self.is_counting_down  = True
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
            self.is_running       = True
            self._time            = time.time()
            return False

    # ------------------------------------------------------------------ reset
    def reset_game(self):
        self.speed      = INITIAL_SPEED
        self.base_speed = INITIAL_SPEED
        self.player_y   = FLOOR_HEIGHT + PLAYER_RADIUS
        self.player_vy  = 0.0
        self.health     = MAX_HEALTH

        self.obstacles            = []
        self._spawn_accumulator   = 0.0
        self.score_distance       = 0.0
        self.avoided_count        = 0
        self.live_score           = 0
        self.is_running           = False
        self.is_counting_down     = False
        self.game_over            = False

        self.msg.text             = "Press SPACE or ENTER to start"
        self.label_countdown.text = ""
        self.hud.text             = ""
        self._slow_start_speed    = None
        self._last_speed_milestone = 0
        self.bg_index             = 0
        self.bg_source            = self.backgrounds[self.bg_index]
        self._bg_elapsed          = 0.0
        self._slow_until          = None
        self._roll_angle          = 0.0
        self._last_clock_time     = Clock.get_time()

    # ------------------------------------------------------------------ helpers
    def on_ground(self):
        return (
            abs(self.player_y - (FLOOR_HEIGHT + PLAYER_RADIUS)) < 1.0
            and self.player_vy <= 0.0
        )

    def spawn_obstacle(self):
        size = random.randint(28, 46)
        x    = WINDOW_WIDTH + random.randint(0, 120)
        self.obstacles.append(Obstacle(x, FLOOR_HEIGHT, size))

    # ------------------------------------------------------------------ update
    def update(self, dt):
        if dt <= 0:
            return

        # ---- background ----
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,
                      source=self.bg_source)

        # ---- game logic ----
        if self.is_running and not self.game_over:
            elapsed_time = time.time() - self._time

            # Time-up end condition
            if elapsed_time >= GAME_DURATION:
                self.end_game()
                return

            # Background cycling
            self._bg_elapsed += dt
            if self._bg_elapsed >= self.BG_SWITCH_SECONDS:
                self._bg_elapsed = 0.0
                self.bg_index  = (self.bg_index + 1) % len(self.backgrounds)
                self.bg_source = self.backgrounds[self.bg_index]

            # Move obstacles
            for ob in list(self.obstacles):
                ob.x -= self.speed * dt

            # Spawn
            self._spawn_accumulator += dt
            if self._spawn_accumulator >= max(0.4, SPAWN_INTERVAL_BASE):
                self._spawn_accumulator = 0.0
                self.spawn_obstacle()

            # Player physics
            self.player_vy += GRAVITY * dt
            self.player_y  += self.player_vy * dt
            if self.player_y < FLOOR_HEIGHT + PLAYER_RADIUS:
                self.player_y  = FLOOR_HEIGHT + PLAYER_RADIUS
                self.player_vy = 0.0

            # Speed milestone
            if self.avoided_count > 0 and (self.avoided_count % 5 == 0):
                new_base = INITIAL_SPEED + (self.avoided_count // 5) * SPEED_INCREASE_PER_5_AVOIDED
                if new_base > self.base_speed:
                    self.base_speed = new_base

            # Distance traveled
            self.score_distance += self.speed * dt

            # Score: distance + avoided bonuses only
            self.live_score = (
                int(self.score_distance)
                + self.avoided_count * POINTS_PER_AVOID
            )

            # Collision detection
            for ob in list(self.obstacles):
                ob_left, ob_right = ob.x, ob.x + ob.size
                ob_bottom, ob_top = ob.y, ob.y + ob.size
                cx, cy = self.player_x, self.player_y
                nx = max(ob_left, min(cx, ob_right))
                ny = max(ob_bottom, min(cy, ob_top))
                if (cx - nx) ** 2 + (cy - ny) ** 2 <= self.player_radius ** 2:
                    try:
                        self.obstacles.remove(ob)
                    except ValueError:
                        pass
                    # Reduce health
                    self.health -= 1
                    if self.health <= 0:
                        self.health = 0
                        self.end_game()
                        return
                    # Slow-down penalty
                    self.speed = max(200, self.speed * SLOW_ON_HIT_MULTIPLIER)
                    self._slow_start_speed = self.speed
                    break

            # Count avoided obstacles
            for ob in list(self.obstacles):
                if not ob.passed and (ob.x + ob.size) < 0:
                    ob.passed = True
                    self.avoided_count += 1
                    try:
                        self.obstacles.remove(ob)
                    except ValueError:
                        pass

            # ---- HUD text ----
            remaining = max(0, int(GAME_DURATION - elapsed_time))
            mins, secs = divmod(remaining, 60)
            self.hud.text = (
                f"Score: {self.live_score}    "
                f"Avoided: {self.avoided_count}    "
                f"Time: {mins}:{secs:02d}"
            )

        elif self.game_over:
            self.hud.text = f"FINAL Score: {self.live_score}"

        # ---- draw objects ----
        wx, wy = self.pos
        ww, wh = self.size

        with self.canvas.before:
            # Obstacles
            for ob in self.obstacles:
                Color(0.86, 0.26, 0.2)
                Rectangle(pos=(wx + ob.x, wy + ob.y), size=(ob.size, ob.size))

            # Player (rolling circle)
            now = Clock.get_time()
            ang_speed = (self.speed / self.player_radius) * (180.0 / 3.14159265)
            self._roll_angle += ang_speed * (now - self._last_clock_time)
            self._last_clock_time = now

            px = wx + self.player_x
            py = wy + self.player_y

            PushMatrix()
            r = Rotate(angle=self._roll_angle, origin=(px, py))
            Color(*self.player_color)
            Ellipse(
                pos=(px - self.player_radius, py - self.player_radius),
                size=(self.player_radius * 2, self.player_radius * 2),
            )
            PopMatrix()

            # Player inner dot
            Color(0.96, 0.96, 0.96)
            small = self.player_radius * 0.5
            Ellipse(pos=(px - small / 2, py - small / 2), size=(small, small))

            # ---- Health bar (top-right of widget) ----
            bar_w  = 240
            bar_h  = 28
            bar_x  = wx + ww - bar_w - 20
            bar_y  = wy + wh - bar_h - 10
            pip_w  = (bar_w - (MAX_HEALTH - 1) * 4) / MAX_HEALTH

            # Background tray
            Color(0.15, 0.15, 0.15, 0.75)
            RoundedRectangle(pos=(bar_x - 4, bar_y - 4),
                             size=(bar_w + 8, bar_h + 8), radius=[6])

            # Individual pip segments
            hc = self._health_color(self.health)
            for i in range(MAX_HEALTH):
                pip_x = bar_x + i * (pip_w + 4)
                Color(*hc) if i < self.health else Color(0.3, 0.3, 0.3, 1)
                RoundedRectangle(pos=(pip_x, bar_y),
                                 size=(pip_w, bar_h), radius=[4])

    # ------------------------------------------------------------------ end
    def end_game(self):
        self.is_running = False
        self.game_over  = True
        self.msg.text   = (
            f"Game Over!  Final Score: {self.live_score}\n"
            f"Obstacles avoided: {self.avoided_count}\n"
            "Press SPACE or ENTER to play again"
        )
        if self.on_game_over_callback:
            self.on_game_over_callback()


# ------------------------------------------------------------------ standalone
class CapstoneGameDemoApp(App):
    def build(self):
        return GameWidget()


if __name__ == "__main__":
    CapstoneGameDemoApp().run()