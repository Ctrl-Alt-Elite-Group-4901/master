import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.config import Config

Config.set("graphics", "fullscreen", "auto")
Config.set("graphics", "borderless", "1")
Config.set("graphics", "resizable", "0")

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.core.window import Window

BASE_DIR = os.path.dirname(__file__)
KV_DIR = BASE_DIR

from areteDemo.screens.login import Login
from areteDemo.screens.register import Register
from areteDemo.screens.main_menu import MainMenu
from areteDemo.screens.profile import Profile
from areteDemo.screens.settings import Settings
from areteDemo.screens.game import GameScreen
from areteDemo.screens.help import HelpScreen
from areteDemo.screens.reflection import ReflectionScreen

REFLECTION_QUESTIONS = [
    {"text": "How many clusters of purple seaweed were in the background?", "choices": ["2", "3", "1", "4"], "correct": 3},
    {"text": "What color was the seashell in the sea background?", "choices": ["Blue", "Red", "Purple", "Green"], "correct": 2},
    {"text": "How many sea rocks were in the background?", "choices": ["1", "2", "3", "4"], "correct": 1},
    {"text": "How many red flowers were in the forest background?", "choices": ["2", "3", "1", "4"], "correct": 1},
    {"text": "What color was the other flower in the forest background?", "choices": ["Blue", "Red", "Purple", "Green"], "correct": 0},
    {"text": "In the space background how many planets were there?", "choices": ["1", "2", "3", "4"], "correct": 1},
    {"text": "What color was the spaceship in the space background?", "choices": ["Blue", "Red", "White", "Green"], "correct": 2},
]


class AreteApp(App):
    title = "Arete App"
    user_id = None

    # Theme properties
    theme_header = ListProperty([0.12, 0.45, 0.88, 1])
    theme_footer = ListProperty([0.95, 0.95, 0.95, 1])
    theme_background = ListProperty([1, 1, 1, 1])
    theme_card = ListProperty([1, 1, 1, 0.97])
    theme_input = ListProperty([0.96, 0.97, 0.99, 1])
    theme_text_primary = ListProperty([0.11, 0.14, 0.18, 1])
    theme_text_muted = ListProperty([0.43, 0.47, 0.54, 1])
    theme_button_secondary = ListProperty([0.24, 0.29, 0.37, 1])
    theme_button_danger = ListProperty([0.82, 0.28, 0.28, 1])
    theme_footer_text = ListProperty([0.33, 0.36, 0.41, 1])

    # Screen-specific background assets for the login and main menu chrome
    login_background = StringProperty(
        os.path.join(BASE_DIR, "images", "background_sky.png")
    )
    menu_background = StringProperty(
        os.path.join(BASE_DIR, "images", "background_forest.png")
    )

    # Player color (from old branch) - used by GameScreen to tint the runner
    player_color = ListProperty([1, 1, 1, 1])

    @staticmethod
    def _lock_fullscreen():
        Window.fullscreen = "auto"
        Window.borderless = True

    def build(self):
        self._lock_fullscreen()
        main_kv = os.path.join(KV_DIR, "main.kv")
        if os.path.exists(main_kv):
            Builder.load_file(main_kv)

        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(Login(name="login"))
        sm.add_widget(Register(name="register"))
        sm.add_widget(MainMenu(name="main_menu"))
        sm.add_widget(Profile(name="profile"))
        sm.add_widget(Settings(name="settings"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(HelpScreen(name="help"))
        sm.add_widget(ReflectionScreen(name="reflection"))
        return sm

    def on_start(self):
        self._lock_fullscreen()


if __name__ == "__main__":
    if __package__ is None:
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        parent = os.path.dirname(pkg_dir)
        if parent not in sys.path:
            sys.path.insert(0, parent)
    AreteApp().run()
