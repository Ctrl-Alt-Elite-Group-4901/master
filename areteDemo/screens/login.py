# areteDemo/screens/login.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
import areteDemo.auth as auth
from areteDemo.screens.ui_helpers import show_message_popup


class Login(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if app.user_id:
            self.manager.current = "main_menu"

    def login_user(self):
        email = self.ids.get("email").text.strip()
        password = self.ids.get("password").text
        if not email or not password:
            self._show_message("Please enter email and password.")
            return
        uid = auth.validate_login(email, password)
        if uid:
            app = App.get_running_app()
            app.user_id = uid
            self.manager.current = "main_menu"
        else:
            self._show_message("Invalid credentials.")

    def go_to_signup(self):
        self.ids.email.text = ""
        self.ids.password.text = ""
        self.manager.current = "register"

    def _show_message(self, text):
        show_message_popup("Access Notice", text, size_hint=(0.7, 0.35))
