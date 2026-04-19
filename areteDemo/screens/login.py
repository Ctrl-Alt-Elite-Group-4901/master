# areteDemo/screens/login.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
import areteDemo.auth as auth
from areteDemo.screens.ui_helpers import show_message_popup


class Login(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if app.user_id or app.is_dev_mode:
            self.manager.current = "main_menu"

    def login_user(self):
        email = self.ids.get("email").text.strip()
        password = self.ids.get("password").text

        # Allow blank email only for dev login; normal users always need one
        if not email and password != "BobRoss5":
            self._show_message("Please enter email and password.")
            return

        result = auth.validate_login(email, password)

        if result == "dev":
            app = App.get_running_app()
            app.is_dev_mode = True
            # user_id intentionally left None — dev has no DB account
            self.manager.current = "main_menu"
        elif result:
            app = App.get_running_app()
            app.user_id = result
            self.manager.current = "main_menu"
        else:
            self._show_message("Invalid credentials.")

    def go_to_signup(self):
        self.ids.email.text = ""
        self.ids.password.text = ""
        self.manager.current = "register"

    def _show_message(self, text):
        show_message_popup("Access Notice", text, size_hint=(0.7, 0.35))
