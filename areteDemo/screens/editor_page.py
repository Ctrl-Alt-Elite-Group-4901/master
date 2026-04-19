# areteDemo/screens/editor_page.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.properties import StringProperty


class EditorPage(Screen):
    """
    Reusable placeholder for all four editor sub-pages.
    Set page_title at registration time in main.py.
    Team members replace the body of on_pre_enter / add widgets here
    when they are ready to implement their page.
    """
    page_title = StringProperty("")

    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.is_dev_mode:
            self.manager.current = "login"

    def go_back(self):
        self.manager.current = "editor_menu"
