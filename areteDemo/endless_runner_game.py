# ===== areteDemo/endless_runner_game.py (renamed from capstone_game_demo_kivy.py) =====
import random
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ListProperty
from kivy.app import App
from kivy.core.window import Window


class Player:
    """Represents the player character"""
    def __init__(self, x, y, size=30):
        self.x = x
        self.y = y
        self.size = size
        self.velocity_y = 0
        self.is_jumping = False
        self.base_speed = 5
        self.current_speed = self.base_speed
        
    def jump(self):
        if not self.is_jumping:
            self.velocity_y = 15
            self.is_jumping = True
    
    def update(self, dt):
        self.velocity_y -= 50 * dt
        self.y += self.velocity_y
        
        
        if self.y <= 100:
            self.y = 100
            self.velocity_y = 0
            self.is_jumping = False
    
    def slow_down(self):
        """Reduce speed when hitting obstacle"""
        self.current_speed = max(2, self.current_speed * 0.5)
    
    def reset_speed(self):
        """Reset to base speed"""
        self.current_speed = self.base_speed


class Obstacle:
    """Represents an obstacle in the game"""
    def __init__(self, x, y, width=20, height=40):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.active = True
    
    def update(self, speed):
        self.x -= speed
        if self.x < -self.width:
            self.active = False
    
    def collides_with(self, player):
        """Check collision with player"""
        return (self.x < player.x + player.size and
                self.x + self.width > player.x and
                self.y < player.y + player.size and
                self.y + self.height > player.y)


class EndlessRunnerGame(Widget):
    """
    Endless runner game widget that integrates with the Arete app.
    Player dodges obstacles by jumping, gets slowed down on hit, loses after 3 hits.
    """
    
    countdown = NumericProperty(3)
    in_countdown = BooleanProperty(True)
    play_time = NumericProperty(0)
    current_score = NumericProperty(0)
    game_over = BooleanProperty(False)
    lives = NumericProperty(3)
     
    hud_text = StringProperty("Starting...")
    player_obj = None
    obstacles = ListProperty([])
    
    _update_event = None
    _spawn_timer = 0
    _spawn_interval = 2.0
    _invulnerable = False
    _invulnerable_timer = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.player = Player(100, 100)
        
        with self.canvas.before:
            Color(0.2, 0.6, 1, 1)  
            self.bg = Rectangle(size=self.size, pos=self.pos)
            
            Color(0.4, 0.8, 0.4, 1)  
            self.ground = Rectangle(size=(self.width, 100), pos=(0, 0))
        
        self.bind(size=self._update_graphics, pos=self._update_graphics)
        
        self.hud_label = Label(
            text=self.hud_text,
            pos=(10, self.height - 100),
            size_hint=(None, None),
            size=(300, 80),
            font_size='18sp',
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.hud_label)
        self.bind(hud_text=lambda instance, value: setattr(self.hud_label, 'text', value))
        
        
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        
        self.start_countdown()

    def _update_graphics(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos
        self.ground.size = (self.width, 100)
        self.hud_label.pos = (10, self.height - 100)

    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'spacebar' and not self.game_over and not self.in_countdown:
            self.player.jump()
        return True

    def start_countdown(self):
        self.countdown = 3
        self.in_countdown = True
        self.hud_text = f"Starting in {self.countdown}"
        Clock.schedule_interval(self._countdown_tick, 1)

    def _countdown_tick(self, dt):
        self.countdown -= 1
        if self.countdown > 0:
            self.hud_text = f"Starting in {self.countdown}"
        else:
            self.hud_text = "GO!"
            self.in_countdown = False
            Clock.unschedule(self._countdown_tick)
            Clock.schedule_once(self.start_game_loop, 0.5)

    
    def start_game_loop(self, dt=0):
        self.play_time = 0
        self.current_score = 0
        self.lives = 3
        self.game_over = False
        self.obstacles = []
        self.player.reset_speed()
        self._spawn_timer = 0
        
        self.canvas.remove_group('game_objects')
        
        self._update_event = Clock.schedule_interval(self.update, 1/60)

    def update(self, dt):
        """Called 60 times per second"""
        if self.game_over or self.in_countdown:
            return

        self.play_time += dt
        self.current_score = int(self.play_time * 10)
        
        self.player.update(dt)
        
        self.player.base_speed = 5 + (self.play_time * 0.1)
        if self.player.current_speed < self.player.base_speed:
            self.player.current_speed = min(self.player.base_speed, self.player.current_speed + dt * 2)
        
        self._spawn_timer += dt
        if self._spawn_timer >= self._spawn_interval:
            self._spawn_timer = 0
            self._spawn_interval = max(0.8, 2.0 - (self.play_time * 0.02))
            self.spawn_obstacle()
        
        for obstacle in self.obstacles[:]:
            obstacle.update(self.player.current_speed)
            
            if obstacle.active and obstacle.collides_with(self.player):
                if not self._invulnerable:
                    self.hit_obstacle()
                    obstacle.active = False
            
            if not obstacle.active:
                self.obstacles.remove(obstacle)
        
        if self._invulnerable:
            self._invulnerable_timer -= dt
            if self._invulnerable_timer <= 0:
                self._invulnerable = False
        
        lives_display = "♥ " * self.lives
        self.hud_text = (
            f"Time: {self.play_time:.1f}s | Score: {self.current_score}\n"
            f"Lives: {lives_display} | Speed: {self.player.current_speed:.1f}"
        )
        
        self.render()

    def spawn_obstacle(self):
        """Spawn a new obstacle"""
        x = self.width + 20
        y = 100
        height = random.choice([30, 40, 50])
        obstacle = Obstacle(x, y, width=20, height=height)
        self.obstacles.append(obstacle)

    def hit_obstacle(self):
        """Handle player hitting an obstacle"""
        self.lives -= 1
        self.player.slow_down()
        self._invulnerable = True
        self._invulnerable_timer = 1.0  
        
        if self.lives <= 0:
            self.end_game()

    def render(self):
        """Render game objects"""
        self.canvas.remove_group('game_objects')
        
        with self.canvas:
            
            if not self._invulnerable or int(self.play_time * 10) % 2 == 0:
                Color(1, 1, 0, 1)  # Yellow
                Ellipse(
                    pos=(self.player.x, self.player.y),
                    size=(self.player.size, self.player.size),
                    group='game_objects'
                )
            
            Color(0.8, 0.2, 0.2, 1)  # Red
            for obstacle in self.obstacles:
                if obstacle.active:
                    Rectangle(
                        pos=(obstacle.x, obstacle.y),
                        size=(obstacle.width, obstacle.height),
                        group='game_objects'
                    )

    def end_game(self):
        if self.game_over:
            return

        self.game_over = True

        if self._update_event:
            Clock.unschedule(self._update_event)

        self.hud_text = (
            f"GAME OVER!\n"
            f"Final Score: {self.current_score}\n"
            f"Time: {self.play_time:.1f}s"
        )

        self._attempt_save_score()

    def _attempt_save_score(self):
        """Save score through the app DB"""
        try:
            app = App.get_running_app()
            if hasattr(app, "user_id") and app.user_id is not None:
                from areteDemo.auth import add_score
                add_score(app.user_id, self.current_score)
                print(f"Score saved: {self.current_score}")
        except Exception as e:
            print(f"Failed to save score: {e}")

    def stop(self):
        """Cleanup when leaving GameScreen"""
        try:
            if self._update_event:
                Clock.unschedule(self._update_event)
            if self._keyboard:
                self._keyboard_closed()
        except Exception as e:
            print(f"Error during cleanup: {e}")
