from copy import deepcopy

from kivy.app import App
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from areteDemo.reflection_questions import get_questions, reset_to_defaults, save_questions
from areteDemo.screens.ui_helpers import show_message_popup


class MemoryQuestionEditor(Screen):
    page_title = StringProperty("Memory Question Editor")
    question_list_text = StringProperty("")
    status_text = StringProperty("")
    selected_index = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._questions = []

    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.is_dev_mode:
            self.manager.current = "login"
            return
        self._reload_questions()

    def go_back(self):
        self.manager.current = "editor_menu"

    def load_selected(self):
        idx_text = self.ids.selected_index_input.text.strip()
        if not idx_text.isdigit():
            self._set_status("Enter a numeric question index.")
            return

        idx = int(idx_text) - 1
        if idx < 0 or idx >= len(self._questions):
            self._set_status("Selected index is out of range.")
            return

        self.selected_index = idx
        self._load_form_from_question(idx)
        self._set_status(f"Loaded question {idx + 1}.")

    def save_selected(self):
        if not self._questions:
            self._set_status("No questions available.")
            return

        question, error = self._build_question_from_form()
        if error:
            self._set_status(error)
            return

        self._questions[self.selected_index] = question
        self._persist_and_refresh(f"Updated question {self.selected_index + 1}.")

    def add_question(self):
        question, error = self._build_question_from_form()
        if error:
            self._set_status(error)
            return

        self._questions.append(question)
        self.selected_index = len(self._questions) - 1
        self._persist_and_refresh(f"Added question {self.selected_index + 1}.")

    def remove_selected(self):
        if len(self._questions) <= 1:
            self._set_status("At least one question is required.")
            return

        removed = self.selected_index + 1
        del self._questions[self.selected_index]
        if self.selected_index >= len(self._questions):
            self.selected_index = len(self._questions) - 1
        self._persist_and_refresh(f"Removed question {removed}.")

    def reset_defaults(self):
        try:
            self._questions = reset_to_defaults()
        except Exception as e:
            self._set_status(f"Failed to reset defaults: {e}")
            return
        self.selected_index = 0
        self._load_form_from_question(0)
        self._refresh_list_text()
        self._set_status("Restored default reflection questions.")
        show_message_popup(
            "Editor Notice",
            "Reflection questions were reset to defaults.",
            size_hint=(0.74, 0.35),
        )

    def _persist_and_refresh(self, status: str):
        try:
            self._questions = save_questions(self._questions)
        except Exception as e:
            self._set_status(f"Failed to save questions: {e}")
            return
        self.ids.selected_index_input.text = str(self.selected_index + 1)
        self._refresh_list_text()
        self._set_status(status)

    def _reload_questions(self):
        try:
            self._questions = get_questions()
        except Exception as e:
            self._questions = []
            self._set_status(f"Failed to load questions: {e}")
            return
        if self.selected_index >= len(self._questions):
            self.selected_index = 0
        self.ids.selected_index_input.text = str(self.selected_index + 1)
        self._load_form_from_question(self.selected_index)
        self._refresh_list_text()
        self._set_status("Editor ready.")

    def _load_form_from_question(self, idx: int):
        q = self._questions[idx]
        self.ids.question_text.text = q["text"]
        self.ids.choice_1.text = q["choices"][0]
        self.ids.choice_2.text = q["choices"][1]
        self.ids.choice_3.text = q["choices"][2]
        self.ids.choice_4.text = q["choices"][3]
        self.ids.correct_choice_input.text = str(q["correct"] + 1)
        self.ids.selected_index_input.text = str(idx + 1)

    def _refresh_list_text(self):
        lines = []
        for idx, question in enumerate(self._questions, start=1):
            marker = "*" if idx - 1 == self.selected_index else " "
            lines.append(f"{marker} {idx}. {question['text']}")
            for choice_idx, choice in enumerate(question["choices"], start=1):
                answer_marker = "(correct)" if question["correct"] == choice_idx - 1 else ""
                lines.append(f"    {choice_idx}) {choice} {answer_marker}".rstrip())
        self.question_list_text = "\n".join(lines)

    def _build_question_from_form(self):
        text = self.ids.question_text.text.strip()
        choices = [
            self.ids.choice_1.text.strip(),
            self.ids.choice_2.text.strip(),
            self.ids.choice_3.text.strip(),
            self.ids.choice_4.text.strip(),
        ]
        correct_text = self.ids.correct_choice_input.text.strip()

        if not text:
            return None, "Question text is required."
        if any(not c for c in choices):
            return None, "All four choices are required."
        if not correct_text.isdigit():
            return None, "Correct choice must be 1, 2, 3, or 4."

        correct = int(correct_text) - 1
        if correct < 0 or correct > 3:
            return None, "Correct choice must be 1, 2, 3, or 4."

        question = {"text": text, "choices": deepcopy(choices), "correct": correct}
        return question, None

    def _set_status(self, message: str):
        self.status_text = message
