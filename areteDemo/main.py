from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty, ListProperty
from kivy.core.window import Window
from arete import db, auth
from capstone_game_demo_kivy import GameWidget

db.init_db()

# Reflection quiz: 5 multiple-choice questions 
# correct = index of correct choice (0=A, 1=B, 2=C, 3=D)
REFLECTION_QUESTIONS = [
    {"text": "What color best describes the ground you jumped on?", "choices": ["Grey", "Blue", "Red", "Brown"], "correct": 3},
    {"text": "How many clusters of seaweed were in the background?", "choices": ["2", "3", "1", "4"], "correct": 1},
    {"text": "What color was the seashell?", "choices": ["Blue", "Red", "Purple", "Green"], "correct": 2},
    {"text": "Which of the following appeared in the background?", "choices": ["orange fish", "red fish", "green fish", "white fish"], "correct": 0},
    {"text": "How many sea rocks were in the background?", "choices": ["1", "2", "3", "4"], "correct": 1},
]

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

class GameScreen(Screen):
    def on_pre_enter(self):
        # Resize window for game and add game widget once
        Window.size = (1920, 1080)
        container = self.ids.game_container
        if len(container.children) == 1:  # only the Back button
            gw = GameWidget(embedded=True, size_hint=(1, 1))
            gw.on_game_over_callback = self._go_to_reflection
            container.add_widget(gw, index=0)

    def _go_to_reflection(self):
        sm = self.manager
        refl = sm.get_screen("reflection")
        refl.return_to = "game"
        refl.start_quiz()
        sm.current = "reflection"

    def on_leave(self):
        # Pause game when leaving the screen
        container = self.ids.game_container
        if len(container.children) >= 2:
            container.children[0].is_running = False  # GameWidget is at index 0


class ReflectionScreen(Screen):
    #Dedicated screen for pysch questions (5 currently)
    return_to = StringProperty("menu")  # "game" or "menu" after quiz
    question_index = NumericProperty(0)
    answers = ListProperty([])

    def start_quiz(self):
        self.question_index = 0
        self.answers = []
        self._show_question()

    def _show_question(self):
        if self.question_index >= len(REFLECTION_QUESTIONS):
            self._show_done()
            return
        q = REFLECTION_QUESTIONS[self.question_index]
        self.ids.question_label.text = q["text"]
        choices = q["choices"]
        for i in range(4):
            self.ids[f"choice_{i}"].text = choices[i] if i < len(choices) else ""
        self.ids.progress_label.text = f"Question {self.question_index + 1} of {len(REFLECTION_QUESTIONS)}"
        self.ids.quiz_box.opacity = 1
        self.ids.done_box.opacity = 0
        self.ids.done_box.disabled = True

    def on_choice(self, index):
        self.answers.append(index)
        self.question_index += 1
        self._show_question()

    def _show_done(self):
        self.ids.quiz_box.opacity = 0
        self.ids.quiz_box.disabled = True
        self.ids.done_box.opacity = 1
        self.ids.done_box.disabled = False
        self.ids.done_label.text = "Thank You for Playing!"
        self.ids.done_back_btn.text = "Back to game" if self.return_to == "game" else "Back to menu"

    def go_back(self):
        self.manager.current = self.return_to

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
        sm.add_widget(ReflectionScreen(name="reflection"))
        return sm

if __name__ == "__main__":
    AreteApp().run()
