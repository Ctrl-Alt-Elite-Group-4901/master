# areteDemo/screens/reflection.py
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ListProperty

from areteDemo.reflection_questions import get_questions


class ReflectionScreen(Screen):
    return_to = StringProperty("main_menu")
    question_index = NumericProperty(0)
    answers = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._questions = []

    def on_pre_enter(self, *args):
        self._sync_to_manager()
        Clock.schedule_once(self._sync_to_manager, 0)
        return super().on_pre_enter(*args)

    def on_enter(self, *args):
        self._sync_to_manager()
        return super().on_enter(*args)

    def _sync_to_manager(self, *_):
        if self.manager:
            self.size = self.manager.size
            self.pos = self.manager.pos

    def start_quiz(self):
        try:
            self._questions = get_questions()
        except Exception:
            self._questions = []
        self.question_index = 0
        self.answers = []
        self._show_question()

    def _show_question(self):
        if self.question_index >= len(self._questions):
            self._show_done()
            return
        q = self._questions[self.question_index]
        self.ids.question_label.text = q["text"]
        choices = q["choices"]
        for i in range(4):
            self.ids[f"choice_{i}"].text = choices[i] if i < len(choices) else ""
        self.ids.progress_label.text = (
            f"Question {self.question_index + 1} of {len(self._questions)}"
        )
        self.ids.quiz_box.opacity = 1
        self.ids.quiz_box.disabled = False
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
        if not self._questions:
            self._correct_count = 0
            self.ids.done_label.text = "No reflection questions are configured."
            self.ids.done_back_btn.text = "Play Again"
            self.ids.menu_btn.text = "Main Menu"
            return

        correct = sum(
            1
            for i, a in enumerate(self.answers)
            if a == self._questions[i]["correct"]
        )
        total = len(self._questions)
        self._correct_count = correct
        self.ids.done_label.text = (
            f"Thank You for Playing!\n"
            f"You got {correct} out of {total} reflection questions correct."
        )
        self.ids.done_back_btn.text = "Play Again"
        self.ids.menu_btn.text = f"Main Menu  ({correct}/{total} correct)"

    def go_back(self):
        dest = self.return_to
        if dest == "game":
            game_screen = self.manager.get_screen("game")
            if game_screen._game_widget:
                game_screen._game_widget.reset_game()
        self.manager.current = dest

    def go_to_menu(self):
        self.manager.current = "main_menu"
