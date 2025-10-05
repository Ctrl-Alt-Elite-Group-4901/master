from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty
from arete import db, auth

db.init_db()

# Load KV files
Builder.load_file("main.kv")

class LoginScreen(Screen):
    def attempt_login(self, email, password):
        user = auth.login(email, password)
        if user:
            self.manager.current = "menu"
            self.manager.get_screen("menu").current_user_id = user[0]
        else:
            self.ids.message.text = "Invalid email or password."

class SignupScreen(Screen):
    def attempt_signup(self, email, password, first_name, last_name):
        success = auth.signup(email, password, first_name, last_name)
        if success:
            self.manager.current = "login"
        else:
            self.ids.message.text = "Email already in use."

class MenuScreen(Screen):
    current_user_id = NumericProperty(-1)

class ProfileScreen(Screen):
    user_email = StringProperty("")
    user_first_name = StringProperty("")
    user_last_name = StringProperty("")

    def on_pre_enter(self):
        menu_screen = self.manager.get_screen("menu")
        user = auth.get_user(menu_screen.current_user_id)
        if user:
            self.user_email, self.user_first_name, self.user_last_name = user

    def save_profile(self, first_name, last_name):
        user_id = self.manager.get_screen("menu").current_user_id
        auth.update_user(user_id, first_name, last_name)
        self.on_pre_enter()

class StatsScreen(Screen): pass
class InfoScreen(Screen): pass

class SettingsScreen(Screen):
    def delete_account(self):
        user_id = self.manager.get_screen("menu").current_user_id
        auth.delete_user(user_id)
        self.manager.current = "login"

class GameScreen(Screen): pass

class AreteApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(SignupScreen(name="signup"))
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(ProfileScreen(name="profile"))
        sm.add_widget(StatsScreen(name="stats"))
        sm.add_widget(InfoScreen(name="info"))
        sm.add_widget(SettingsScreen(name="settings"))
        sm.add_widget(GameScreen(name="game"))
        return sm

if __name__ == "__main__":
    AreteApp().run()
