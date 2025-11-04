# capstone_game_demo_kivy.py
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Ellipse, RoundedRectangle, PushMatrix, PopMatrix, Rotate
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty, BooleanProperty, ListProperty
import random
import time

# KNOWN ISSUES/CHANGES
# HUD Display not showing up, though the values seem to be updating accordingly
# Window scaling is currently static, need to add scaling
# Added player rotation to simulate movement, needs a better player model

# Game constants
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
FLOOR_HEIGHT = 60
PLAYER_RADIUS = 18
GRAVITY = -1200  # pixels per second^2 (negative = pulls down)
JUMP_VELOCITY = 520  # initial jump velocity - tuned for feel
INITIAL_SPEED = 240  # pixels/second (how fast obstacles move left)
SPEED_INCREASE_PER_SEC = 6  # speed increases over time
OBSTACLE_MIN_GAP = 350
OBSTACLE_MAX_GAP = 900
SPAWN_INTERVAL_BASE = 1.6  # base interval between obstacles (sec) - modified by speed
SLOW_ON_HIT_MULTIPLIER = 0.45  # speed multiplier upon hit
SLOW_RECOVER_TIME = 1.6  # seconds to recover from slow to normal (smooth interpolate)


class Obstacle:
    """Simple struct for obstacles."""
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.passed = False  # whether it passed left edge without collision


class GameWidget(Widget):
    speed = NumericProperty(INITIAL_SPEED)  # current world speed (px/s)
    base_speed = NumericProperty(INITIAL_SPEED)  # base target speed
    player_y = NumericProperty(0.0)  # center y of player
    player_vy = NumericProperty(0.0)
    player_x = NumericProperty(160.0)  # horizontal position of player (constant)
    player_radius = NumericProperty(PLAYER_RADIUS)
    is_running = BooleanProperty(False)
    is_counting_down = BooleanProperty(False)
    countdown_value = NumericProperty(0)
    health = NumericProperty(3)
    obstacles = ListProperty([])
    score_distance = NumericProperty(0.0)
    avoided_count = NumericProperty(0)
    game_over = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.size = (WINDOW_WIDTH, WINDOW_HEIGHT)
        Window.bind(on_key_down=self._on_key_down)
        self.player_y = FLOOR_HEIGHT + PLAYER_RADIUS
        self._last_spawn_x = WINDOW_WIDTH + 100
        self._spawn_accumulator = 0.0
        self._time = time.time()
        self._slow_until = None
        self._slow_start_speed = None

        # UI labels
        self.label_countdown = Label(text="", font_size=48, pos=(WINDOW_WIDTH/2 - 60, WINDOW_HEIGHT/2 - 24))
        self.add_widget(self.label_countdown)
        self.hud = Label(text="", font_size=18, pos=(10, WINDOW_HEIGHT - 30))
        self.add_widget(self.hud)
        self.msg = Label(text="Press SPACE to start", font_size=22, pos=(WINDOW_WIDTH/2 - 140, WINDOW_HEIGHT/2 + 40))
        self.add_widget(self.msg)

        # schedule update
        Clock.schedule_interval(self.update, 1.0/60.0)

        with self.canvas:
            pass  # we'll draw each frame in update()

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        # space key -> 32
        if key == 32:
            if not self.is_running and not self.is_counting_down and not self.game_over:
                # start countdown
                self.msg.text = ""
                self.start_countdown(3)
            elif self.is_running and not self.game_over:
                # player jump input
                if self.on_ground():
                    self.player_vy = JUMP_VELOCITY
            elif self.game_over:
                # restart the game
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
        self.player_y = FLOOR_HEIGHT + PLAYER_RADIUS
        self.player_vy = 0.0
        self.health = 3
        self.obstacles = []
        self._spawn_accumulator = 0.0
        self.score_distance = 0.0
        self.avoided_count = 0
        self.is_running = False
        self.is_counting_down = False
        self.game_over = False
        self.msg.text = "Press SPACE to start"
        self.label_countdown.text = ""
        self.hud.text = ""
        self._slow_until = None
        self._slow_start_speed = None

    def on_ground(self):
        # player's center y equals ground + radius
        return abs(self.player_y - (FLOOR_HEIGHT + PLAYER_RADIUS)) < 1.0 and self.player_vy <= 0.0

    def spawn_obstacle(self):
        # spawn a square obstacle at right side
        size = random.randint(28, 46)
        x = WINDOW_WIDTH + random.randint(0, 120)
        y = FLOOR_HEIGHT
        self.obstacles.append(Obstacle(x, y, size))

    def update(self, dt):
        # dt safety
        if dt <= 0:
            return

        # draw fresh
        self.canvas.clear()
        with self.canvas:
            # draw background
            Color(0.08, 0.09, 0.12)
            Rectangle(pos=(0, 0), size=(WINDOW_WIDTH, WINDOW_HEIGHT))

            # draw floor
            Color(0.16, 0.18, 0.22)
            Rectangle(pos=(0, 0), size=(WINDOW_WIDTH, FLOOR_HEIGHT))

            # draw a ground stripe for depth
            Color(0.12, 0.13, 0.17)
            Rectangle(pos=(0, FLOOR_HEIGHT-6), size=(WINDOW_WIDTH, 6))

        # update only if running (but still draw static HUD)
        if self.is_running and not self.game_over:
            # speed increases gradually
            self.base_speed += SPEED_INCREASE_PER_SEC * dt
            # handle slow effect interpolation if in slow recovery
            if self._slow_until is not None:
                now = time.time()
                if now >= self._slow_until:
                    # end slow effect
                    self.speed = self.base_speed
                    self._slow_until = None
                    self._slow_start_speed = None
                else:
                    # smooth interpolate speed back to base_speed
                    t = 1.0 - (self._slow_until - now) / SLOW_RECOVER_TIME  # 0->1
                    self.speed = (1.0 - t) * self._slow_start_speed + t * self.base_speed
            else:
                self.speed = self.base_speed

            # move obstacles left by speed*dt
            for ob in list(self.obstacles):
                ob.x -= self.speed * dt

            # spawn logic: spawn when last obstacle sufficiently left
            # simpler: use accumulator and a spawn interval scaled by speed
            # faster speed = shorter intervals
            spawn_interval = max(0.4, SPAWN_INTERVAL_BASE * (INITIAL_SPEED / (self.base_speed)))
            self._spawn_accumulator += dt
            if self._spawn_accumulator >= spawn_interval:
                self._spawn_accumulator = 0.0
                self.spawn_obstacle()

            # physics: player vertical
            self.player_vy += GRAVITY * dt
            self.player_y += self.player_vy * dt
            # collision with ground
            if self.player_y < FLOOR_HEIGHT + PLAYER_RADIUS:
                self.player_y = FLOOR_HEIGHT + PLAYER_RADIUS
                self.player_vy = 0.0

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
                    self.health -= 1
                    # slow effect
                    self._slow_start_speed = self.speed
                    self._slow_until = time.time() + SLOW_RECOVER_TIME
                    self.base_speed = self.base_speed  # base remains but we'll interpolate from _slow_start_speed up to base
                    # immediately set current speed lower to show impact
                    self.speed = self._slow_start_speed * SLOW_ON_HIT_MULTIPLIER
                    self._slow_start_speed = self.speed
                    # if health reaches 0 -> game over
                    if self.health <= 0:
                        self.end_game()
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
        with self.canvas:
            # draw obstacles
            for ob in self.obstacles:
                Color(0.86, 0.26, 0.2)
                Rectangle(pos=(ob.x, ob.y), size=(ob.size, ob.size))

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
            Ellipse(pos=(self.player_x - self.player_radius, self.player_y - self.player_radius),
                    size=(self.player_radius*2, self.player_radius*2))
            PopMatrix()

            # player inner eye or dot
            Color(0.96, 0.96, 0.96)
            small = self.player_radius * 0.5
            Ellipse(pos=(self.player_x - small/2, self.player_y - small/2), size=(small, small))

        # draw HUD text
        if not self.game_over:
            self.hud.text = f"Health: {self.health}    Distance: {int(self.score_distance)}    Avoided: {self.avoided_count}"
        else:
            self.hud.text = ""

    def end_game(self):
        self.is_running = False
        self.game_over = True
        final_score = int(self.score_distance) + self.avoided_count * 100
        self.msg.text = f"Game Over — Score: {final_score}\nPress SPACE to restart"

class CapstoneGameDemoApp(App):
    def build(self):
        root = GameWidget()
        return root

if __name__ == '__main__':
    CapstoneGameDemoApp().run()
