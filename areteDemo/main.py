import os
import sys
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.properties import ListProperty

BASE_DIR = os.path.dirname(__file__)
KV_DIR = BASE_DIR

# import screeens before KV required
from areteDemo.screens.login import Login
from areteDemo.screens.register import Register
from areteDemo.screens.main_menu import MainMenu
from areteDemo.screens.profile import Profile
from areteDemo.screens.settings import Settings
from areteDemo.screens.game import GameScreen
from areteDemo.screens.help import HelpScreen

`class AreteApp(App):
    title = "Arete App"
    user_id = None 
    theme_header = ListProperty([0.12, 0.45, 0.88, 1])
    theme_footer = ListProperty([0.95, 0.95, 0.95, 1])
    theme_background = ListProperty([1, 1, 1, 1])

    def build(self):
        # load main.kv for screen definitions
        main_kv = os.path.join(KV_DIR, "main.kv")
        if os.path.exists(main_kv):
            Builder.load_file(main_kv)
        
        # create ScreenManager
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(Login(name="login"))
        sm.add_widget(Register(name="register"))
        sm.add_widget(MainMenu(name="main_menu"))
        sm.add_widget(Profile(name="profile"))
        sm.add_widget(Settings(name="settings"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(HelpScreen(name="help"))
        
        return sm

if __name__ == "__main__":
    # support running as "python -m areteDemo.main"
    if __package__ is None:
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        parent = os.path.dirname(pkg_dir)
        if parent not in sys.path:
            sys.path.insert(0, parent)
    AreteApp().run()

