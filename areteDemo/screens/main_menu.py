# areteDemo/screens/main_menu.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
import areteDemo.auth as auth


class MainMenu(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        # Dev mode bypasses the normal user_id requirement
        if not app.user_id and not app.is_dev_mode:
            self.manager.current = "login"

    def go_to_game(self):
        self.manager.current = "game"

    def go_to_profile(self):
        self.manager.current = "profile"

    def go_to_editor(self):
        self.manager.current = "editor_menu"

    def logout(self):
        app = App.get_running_app()
        app.user_id = None
        app.is_dev_mode = False
        app.pending_run_data = None
        self.manager.current = "login"
