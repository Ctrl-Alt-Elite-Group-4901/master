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

# KNOWN ISSUES/CHANGES
# HUD Display not showing up, specifically during gameplay, though the values seem to be updating accordingly
# Window scaling has been partially added
# Removed health system, replacing it with a timer that ends the game after 5 minutes

# Game constants
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
FLOOR_HEIGHT = 150
PLAYER_X = 400.0

FLOOR_HEIGHT_RATIO = FLOOR_HEIGHT / WINDOW_HEIGHT
PLAYER_X_RATIO = PLAYER_X / WINDOW_WIDTH

# BASE_FLOOR_RATIO = 0.15

PLAYER_RADIUS = 30
GRAVITY = -1200  # pixels per second^2 (negative = pulls down)
JUMP_VELOCITY = 700  # initial jump velocity - tuned for feel

INITIAL_SPEED = 260  # pixels/second (how fast obstacles move left)
SPEED_INCREASE_PER_5_AVOIDED = 20  # speed increases incrementally for every 5 obstacles avoided
OBSTACLE_MIN_GAP = 350
OBSTACLE_MAX_GAP = 900
SPAWN_INTERVAL_BASE = 2.0  # base interval between obstacles (sec) - modified by speed

SLOW_ON_HIT_MULTIPLIER = 0.9  # speed multiplier upon hit
GAME_DURATION = 300  # 5 minute game duration

#SPAWN_PAUSE_ON_BG_SWITCH = 2.0  # pause obstacle spawning after background switches (sec)
OBSTACLE_PREVIEW_SECONDS = 5.5  # spawn NEXT theme obstacles this many seconds before bg switch

def _resource_path(relative_path): # helper to find resource path that works both in dev and when packaged with PyInstaller
    
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
    def __init__(self, x, y, size, source):
        self.x = x
        self.y = y
        self.size = size
        self.source = source
        self.passed = False

class GameWidget(Widget):
    speed = NumericProperty(INITIAL_SPEED)  # current world speed (px/s)
    base_speed = NumericProperty(INITIAL_SPEED)  # base target speed
    
    player_y = NumericProperty(0.0)  # center y of player
    player_vy = NumericProperty(0.0)
    player_x = NumericProperty(400.0)  # horizontal position of player (constant)  # change this number only
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
        
        # Player color property (Merged from our work)
        self.player_color = [1, 1, 1, 1]

        self._spawn_accumulator = 0.0
        self._time = time.time()
        self._slow_start_speed = None
        self._slow_until = None

        self._last_speed_milestone = 0

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

        # UI labels (bold colors so they show on sea background)
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

        # schedule update
        Clock.schedule_interval(self.update, 1.0/60.0)
        # Game graphics drawn to canvas.before so Labels (children) render on top

        # Window resize handler to adjust player and UI positions (not fully implemented)
        #def _on_resize(self, *_):
        #    self.player_x = self.width * 0.15
        #    self.player_y = self.floor_height + PLAYER_RADIUS
        #
        #    self.label_countdown.center = self.center
        #    self.msg.center = (self.width / 2, self.height * 0.6)
        #    self.hud.pos = (10, self.height - 36)
        #
        #@property
        #def floor_height(self):
        #    return self.height * BASE_FLOOR_RATIO

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

    # Helper method to set color (Merged from our work)
    def set_player_color(self, r, g, b, a=1):
        self.player_color = [r, g, b, a]
    
    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        if not self.is_active:
            return
        # SPACE = 32, Enter/Return = 13 (both start countdown and restart; only SPACE jumps)
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
        Clock.schedule_interval(self._countdown_tick, 1.0)  # tick each second

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
            return False  # unschedule

    def reset_game(self):
        # reset all state
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
        self._layout_overlay()

    def on_ground(self):
        # player's center y equals ground + radius
        return abs(self.player_y - (self.floor_height + PLAYER_RADIUS)) < 1.0 and self.player_vy <= 0.0

    def spawn_obstacle(self):
        # spawn a square obstacle at right side
        size = 70
        x = self.viewport_width + random.randint(0, 120)
        y = self.floor_height

        # If we are within N seconds of a background switch,
        # spawn obstacles using the NEXT background's obstacle theme
        time_to_switch = self.BG_SWITCH_SECONDS - self._bg_elapsed
        if time_to_switch <= OBSTACLE_PREVIEW_SECONDS:
            preview_index = (self.bg_index + 1) % len(self.backgrounds)
        else:
            preview_index = self.bg_index

        src = self.obstacle_sources.get(preview_index, _resource_path(os.path.join("images", "obstacle_default.png")))
        self.obstacles.append(Obstacle(x, y, size, src))

    def update(self, dt):
        # dt safety
        if dt <= 0:
            return

        # draw fresh to canvas.before so Labels stay visible on top
        self.canvas.before.clear()
        with self.canvas.before:
            # draw background
            Color(1, 1, 1, 1)
            Rectangle(
                pos=(0, 0),
                size=(self.viewport_width, self.viewport_height),
                source=self.bg_source
            )

        # update only if running (but still draw static HUD)
        if self.is_running and not self.game_over:
            # game end condition
            elapsed_time = time.time() - self._time
            if elapsed_time >= GAME_DURATION:
                self.end_game()
                return           

            # background change every 10 seconds
            self._bg_elapsed += dt
            if self._bg_elapsed >= self.BG_SWITCH_SECONDS:
                self._bg_elapsed = 0.0
                self.bg_index = (self.bg_index + 1) % len(self.backgrounds)
                self.bg_source = self.backgrounds[self.bg_index]
                # self._spawn_pause_remaining = SPAWN_PAUSE_ON_BG_SWITCH
                # self._spawn_accumulator = 0.0

            # game end condition
            elapsed_time = time.time() - self._time
            if elapsed_time >= GAME_DURATION:
                self.end_game()
                return
            
            # move obstacles left by speed*dt
            for ob in list(self.obstacles):
                ob.x -= self.speed * dt

            # spawn logic: spawn when last obstacle sufficiently left
            # simpler: use accumulator and a spawn interval scaled by speed
            # faster speed = shorter intervals
            if self._spawn_pause_remaining > 0.0:
                self._spawn_pause_remaining -= dt
            else:
                spawn_interval = max(0.4, SPAWN_INTERVAL_BASE)
                self._spawn_accumulator += dt
                if self._spawn_accumulator >= spawn_interval:
                    self._spawn_accumulator = 0.0
                    self.spawn_obstacle()

            # physics: player vertical
            self.player_vy += GRAVITY * dt
            self.player_y += self.player_vy * dt
            # collision with ground
            if self.player_y < self.floor_height + PLAYER_RADIUS:
                self.player_y = self.floor_height + PLAYER_RADIUS
                self.player_vy = 0.0

            # speed increase logic: every 5 avoided, increase base speed by fixed amount
            if self.avoided_count > 0 and (self.avoided_count % 5 == 0):
                self.base_speed = self.base_speed + SPEED_INCREASE_PER_5_AVOIDED

            # distance traveled (approx): speed * elapsed_time increments distance
            self.score_distance += self.speed * dt

            # collision detection: circle vs squares
            for ob in list(self.obstacles):
                # obstacle bounding box
                ob_left = ob.x
                ob_right = ob.x + ob.size
                ob_bottom = ob.y
                ob_top = ob.y + ob.size

                # circle center
                cx = self.player_x
                cy = self.player_y

                # AABB-circle collision test
                nearest_x = max(ob_left, min(cx, ob_right))
                nearest_y = max(ob_bottom, min(cy, ob_top))
                dx = cx - nearest_x
                dy = cy - nearest_y
                if (dx*dx + dy*dy) <= (self.player_radius * self.player_radius):
                    # collision!
                    try:
                        self.obstacles.remove(ob)
                    except ValueError:
                        pass
                    # slow effect
                    self._slow_start_speed = self.speed
                    self.base_speed = self.base_speed  # base remains but we'll interpolate from _slow_start_speed up to base
                    # immediately set current speed lower to show impact
                    self.speed = self._slow_start_speed * SLOW_ON_HIT_MULTIPLIER
                    self._slow_start_speed = self.speed
                    if self.speed < 200:  # don't let it get too slow
                        self.speed = 200
                    break  # only one hit per frame

            # obstacles that passed left edge without collision -> avoided
            for ob in list(self.obstacles):
                if not ob.passed and (ob.x + ob.size) < 0:
                    ob.passed = True
                    self.avoided_count += 1
                    try:
                        self.obstacles.remove(ob)
                    except ValueError:
                        pass

        # draw dynamic objects regardless of running (so countdown/score display)
        with self.canvas.before:
            # draw obstacles
            for ob in self.obstacles:
                Color(1, 1, 1, 1)
                Rectangle(pos=(ob.x, ob.y), size=(ob.size, ob.size), source=ob.source)

            # draw player (rolling circle)
            # we draw rotation to visually roll the circle depending on speed
            push = PushMatrix()
            r = Rotate()
            # rotation angle derived from speed and time (simulate rolling)
            # radius = player_radius, angular velocity = speed / radius (rad/s), convert to degrees
            ang_speed = (self.speed / (self.player_radius)) * (180.0 / 3.14159265)  # degrees per second
            # accumulate angle in a simple way using time:
            if not hasattr(self, "_roll_angle"):
                self._roll_angle = 0.0
            self._roll_angle += ang_speed * (Clock.get_time() - getattr(self, "_last_clock_time", Clock.get_time()))
            self._last_clock_time = Clock.get_time()
            r.angle = self._roll_angle
            r.origin = (self.player_x, self.player_y)
            
            # Apply dynamic player color (Merged from our work)
            Color(*self.player_color)
            
            Ellipse(pos=(self.player_x - self.player_radius, self.player_y - self.player_radius),
                    size=(self.player_radius*2, self.player_radius*2))
            PopMatrix()

            # player inner eye or dot
            Color(0.96, 0.96, 0.96)
            small = self.player_radius * 0.5
            Ellipse(pos=(self.player_x - small/2, self.player_y - small/2), size=(small, small))

        # draw HUD text (keep showing during game over so final stats are visible)
        if not self.game_over:
            self.hud.text = f"Distance: {int(self.score_distance)}    Avoided: {self.avoided_count}"
        else:
            final_score = int(self.score_distance) + self.avoided_count * 100
            self.hud.text = f"FINAL - Score: {final_score}"

    def end_game(self):
        self.is_running = False
        self.game_over = True
        final_score = int(self.score_distance) + self.avoided_count * 100
        self.msg.text = f"Game Over - Score: {final_score}\nPress SPACE or ENTER to play again"
        if self.on_game_over_callback:
            self.on_game_over_callback()

class CapstoneGameDemoApp(App):
    def build(self):
        lock_window_fullscreen()
        root = GameWidget()
        return root

if __name__ == '__main__':
    CapstoneGameDemoApp().run()
