# areteDemo/screens/editor_page.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty


class EditorPage(Screen):
    """
    Restricted editor screen shell kept for future sponsor-specific tools.
    """
    page_title = StringProperty("")

    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.is_dev_mode:
            self.manager.current = "login"

    def go_back(self):
        self.manager.current = "editor_menu"
