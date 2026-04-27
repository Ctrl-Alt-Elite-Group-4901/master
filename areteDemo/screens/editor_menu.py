# areteDemo/screens/editor_menu.py
from kivy.uix.screenmanager import Screen
from kivy.app import App


class EditorMenu(Screen):
    def on_pre_enter(self):
        # Guard: only reachable in dev mode
        app = App.get_running_app()
        if not app.is_dev_mode:
            self.manager.current = "login"

    def go_to_page(self, page_number: int):
        self.manager.current = f"editor_page_{page_number}"

    def go_to_player_directory(self):
        self.manager.current = "player_directory"

    def go_back(self):
        self.manager.current = "main_menu"
