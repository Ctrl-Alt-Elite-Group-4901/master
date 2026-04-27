import logging

from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from kivy.properties import BooleanProperty, StringProperty, NumericProperty, ListProperty

from areteDemo import run_data
from areteDemo.reflection_questions import get_questions
from areteDemo.screens.ui_helpers import show_message_popup


logger = logging.getLogger(__name__)


class ReflectionScreen(Screen):
    return_to = StringProperty("main_menu")
    question_index = NumericProperty(0)
    answers = ListProperty([])
    save_status_text = StringProperty("")
    can_retry_save = BooleanProperty(False)
    save_status_is_error = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._questions = []
        self._question_load_error = ""
        self._run_saved = False
        self._correct_count = 0
        self._total_count = 0

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
            self._question_load_error = ""
        except Exception:
            self._questions = []
            self._question_load_error = "Reflection questions could not be loaded. Check the local question file."
        self.question_index = 0
        self.answers = []
        self._run_saved = False
        self._correct_count = 0
        self._total_count = 0
        self.save_status_text = ""
        self.can_retry_save = False
        self.save_status_is_error = False
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
            self._total_count = 0
            self._persist_completed_run(correct=0, total=0)
            self._refresh_done_message(self._empty_questions_message())
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
        self._total_count = total
        self._persist_completed_run(correct=correct, total=total)
        self._refresh_done_message(
            f"Thank You for Playing!\n"
            f"You got {correct} out of {total} reflection questions correct."
        )
        self.ids.done_back_btn.text = "Play Again"
        self.ids.menu_btn.text = f"Main Menu  ({correct}/{total} correct)"

    def _refresh_done_message(self, base_message: str | None = None):
        if base_message is None:
            if self._total_count > 0:
                base_message = (
                    f"Thank You for Playing!\n"
                    f"You got {self._correct_count} out of {self._total_count} reflection questions correct."
                )
            else:
                base_message = self._empty_questions_message()

        self.ids.done_label.text = base_message

    def _empty_questions_message(self) -> str:
        return self._question_load_error or "No reflection questions are configured."

    def _set_save_status(self, text: str, retryable: bool, is_error: bool):
        self.save_status_text = text
        self.can_retry_save = retryable
        self.save_status_is_error = is_error

    def _has_unsaved_in_memory_run(self) -> bool:
        app = App.get_running_app()
        return bool(not self._run_saved and getattr(app, "pending_run_data", None))

    def go_back(self):
        if self._has_unsaved_in_memory_run():
            show_message_popup(
                "Run Save Notice",
                "This run has not been saved yet. Retry the save before starting another run.",
                size_hint=(0.78, 0.38),
            )
            return
        dest = self.return_to
        if dest == "game":
            game_screen = self.manager.get_screen("game")
            if game_screen._game_widget:
                game_screen._game_widget.reset_game()
        self.manager.current = dest

    def go_to_menu(self):
        if self._has_unsaved_in_memory_run():
            show_message_popup(
                "Run Save Notice",
                "This run has not been saved yet. Retry the save before leaving this screen.",
                size_hint=(0.78, 0.38),
            )
            return
        self.manager.current = "main_menu"

    def retry_save(self):
        app = App.get_running_app()
        if not app.user_id:
            self._set_save_status("Run save is unavailable because no player is logged in.", False, True)
            self._refresh_done_message()
            return

        if self._has_unsaved_in_memory_run():
            self._persist_completed_run(correct=self._correct_count, total=self._total_count)
            if self._has_unsaved_in_memory_run():
                self._refresh_done_message()
                return

        try:
            retried = run_data.retry_pending_run_uploads(user_id=int(app.user_id))
            remaining = self._pending_count_for_current_user()
        except Exception:
            logger.exception("Pending run retry failed for user_id=%s", app.user_id)
            remaining = self._pending_count_for_current_user()
            self._set_save_status(
                f"Retry failed. {remaining} run(s) still waiting to upload.",
                True,
                True,
            )
            self._refresh_done_message()
            show_message_popup(
                "Run Save Notice",
                "The retry did not complete. Check the connection and try again.",
                size_hint=(0.82, 0.42),
            )
            return

        if remaining:
            self._set_save_status(
                f"Retried {retried} run(s). {remaining} run(s) still waiting to upload.",
                True,
                True,
            )
        else:
            self._set_save_status("Run data uploaded successfully.", False, False)
        self._refresh_done_message()

    def _persist_completed_run(self, correct: int, total: int):
        if self._run_saved:
            pending_count = self._pending_count_for_current_user()
            if pending_count:
                self._set_save_status(
                    f"{pending_count} run(s) still waiting to upload.",
                    True,
                    True,
                )
            return True

        app = App.get_running_app()
        run_payload = getattr(app, "pending_run_data", None)
        if not app.user_id or not run_payload:
            self._run_saved = True
            self._set_save_status("", False, False)
            return True

        quiz_payload = self._build_quiz_payload(correct, total)

        try:
            save_result = run_data.save_completed_run(int(app.user_id), run_payload, quiz_payload)
        except run_data.RunSavePendingError as exc:
            app.pending_run_data = None
            self._run_saved = True
            pending_count = self._pending_count_for_current_user()
            self._set_save_status(
                f"Cloud upload is pending. {pending_count} run(s) are saved locally for retry.",
                True,
                True,
            )
            show_message_popup(
                "Run Save Notice",
                f"{exc}\n\nRetry from this screen when the connection is available.",
                size_hint=(0.82, 0.42),
            )
            return False
        except Exception:
            logger.exception("Run save failed for user_id=%s", app.user_id)
            self._run_saved = False
            self._set_save_status(
                "Run data is not saved yet. Retry before starting another run.",
                True,
                True,
            )
            show_message_popup(
                "Run Save Notice",
                "Run data could not be saved yet. Retry before starting another run.",
                size_hint=(0.82, 0.42),
            )
            return False

        app.pending_run_data = None
        self._run_saved = True
        pending_count = self._pending_count_for_current_user()
        if save_result.storage == "local":
            self._set_save_status(
                "Run saved locally because cloud upload is unavailable.",
                False,
                False,
            )
        elif pending_count:
            self._set_save_status(
                f"Run saved. {pending_count} earlier run(s) still waiting to upload.",
                True,
                True,
            )
        else:
            self._set_save_status("Run saved.", False, False)
        return True

    def _build_quiz_payload(self, correct: int, total: int):
        answer_details = []
        for idx, question in enumerate(self._questions):
            selected_idx = self.answers[idx] if idx < len(self.answers) else None
            correct_idx = question.get("correct")
            choices = question.get("choices", [])
            selected_text = (
                choices[selected_idx] if isinstance(selected_idx, int) and 0 <= selected_idx < len(choices) else ""
            )
            correct_text = (
                choices[correct_idx] if isinstance(correct_idx, int) and 0 <= correct_idx < len(choices) else ""
            )
            answer_details.append(
                {
                    "question_order": idx + 1,
                    "question_text": question.get("text", ""),
                    "selected_index": selected_idx,
                    "selected_text": selected_text,
                    "correct_index": correct_idx,
                    "correct_text": correct_text,
                    "is_correct": bool(selected_idx == correct_idx),
                }
            )
        quiz_payload = {
            "quiz_total_questions": int(total),
            "quiz_correct_count": int(correct),
            "quiz_incorrect_count": int(max(total - correct, 0)),
            "answers": answer_details,
        }
        return quiz_payload

    def _pending_count_for_current_user(self) -> int:
        app = App.get_running_app()
        if not app.user_id:
            return 0
        try:
            return run_data.count_pending_run_uploads(user_id=int(app.user_id))
        except Exception:
            logger.exception("Pending upload count lookup failed for user_id=%s", app.user_id)
            return 0
