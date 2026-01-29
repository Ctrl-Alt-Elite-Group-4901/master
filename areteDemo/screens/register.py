# areteDemo/screens/register.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import areteDemo.auth as auth
import sqlite3


class Register(Screen):
    def signup_user(self):
        first = self.ids.get("first_name").text.strip()
        last = self.ids.get("last_name").text.strip()
        email = self.ids.get("email").text.strip()
        password = self.ids.get("password").text
        if not email or not password:
            self._show_message("Email and password required.")
            return
        try:
            uid = auth.signup(first, last, email, password)
        except sqlite3.IntegrityError:
            self._show_message("Email already registered.")
            return
        app = App.get_running_app()
        app.user_id = uid
        self.manager.current = "main_menu"

    def go_to_login(self):
        self.ids.first_name.text = ""
        self.ids.last_name.text = ""
        self.ids.email.text = ""
        self.ids.password.text = ""
        self.manager.current = "login"

    def _show_message(self, text):
        popup = Popup(title="Sign Up", content=Label(text=text), size_hint=(0.7, 0.35))
        popup.open()
