# areteDemo/screens/main_menu.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
import areteDemo.auth as auth


class MainMenu(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.user_id:
            self.manager.current = "login"

    def go_to_game(self):
        self.manager.current = "game"

    def go_to_profile(self):
        self.manager.current = "profile"

    def logout(self):
        app = App.get_running_app()
        app.user_id = None
        self.manager.current = "login"
