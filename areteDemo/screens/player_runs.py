import logging

from kivy.app import App
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen

from areteDemo import run_data
from areteDemo.screens.ui_helpers import show_message_popup


logger = logging.getLogger(__name__)


class PlayerRuns(Screen):
    player_id = NumericProperty(0)
    player_name = StringProperty("")
    player_username = StringProperty("")
    player_email = StringProperty("")
    run_list_text = StringProperty("")
    status_text = StringProperty("")

    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.is_dev_mode:
            self.manager.current = "login"
            return
        if self.player_id:
            self.load_runs()

    def set_player(self, player_id: int, display_name: str, username: str, email: str):
        self.player_id = int(player_id)
        self.player_name = display_name
        self.player_username = username
        self.player_email = email
        self.status_text = "Loading runs..."
        self.load_runs()

    def load_runs(self):
        if not self.player_id:
            self.status_text = "No player selected."
            self.run_list_text = ""
            return

        try:
            runs = run_data.get_player_runs(self.player_id)
        except run_data.CloudAuthError:
            run_data.clear_admin_token()
            self.status_text = "Cloud token rejected. Reconnect from the Player Directory."
            self.run_list_text = ""
            self.manager.current = "player_directory"
            return
        except Exception:
            logger.exception("Failed to load runs for player_id=%s", self.player_id)
            self.status_text = "Run history is unavailable. Check the cloud connection and try again."
            self.run_list_text = ""
            show_message_popup(
                "Run History Notice",
                "Run history is unavailable. Check the cloud connection and try again.",
                size_hint=(0.8, 0.4),
            )
            return

        self.status_text = f"{len(runs)} completed run(s)."

        if not runs:
            self.run_list_text = "No completed runs for this player yet."
            return

        lines: list[str] = []
        for run in runs:
            lines.append(
                f"Run {run['id']} | {run['started_at']} -> {run['ended_at']} | Score: {run['score']}"
            )
            lines.append(
                f"Hits: {run['objects_hit_total']} | IDs: {run['hit_object_ids'] or '-'}"
            )
            lines.append(
                f"Quiz: {run['quiz_correct_count']}/{run['quiz_total_questions']} correct "
                f"({run['quiz_incorrect_count']} incorrect)"
            )
            lines.append(
                f"Speed px/s start {run['speed_start_pxps']:.2f}, avg {run['speed_avg_pxps']:.2f}, "
                f"max {run['speed_max_pxps']:.2f}, end {run['speed_end_pxps']:.2f}"
            )
            lines.append(
                f"Sizes px^2 player {run['player_size_px2']:.2f}, obstacle {run['obstacle_size_px2']:.2f}"
            )
            lines.append("-" * 78)

        self.run_list_text = "\n".join(lines)

    def export_csv(self):
        if not self.player_id:
            show_message_popup("Export Notice", "No player selected.", size_hint=(0.72, 0.35))
            return
        try:
            output = run_data.export_player_runs_csv(self.player_id)
        except run_data.CloudAuthError:
            run_data.clear_admin_token()
            show_message_popup(
                "Export Notice",
                "Cloud token rejected. Reconnect from the Player Directory.",
                size_hint=(0.8, 0.38),
            )
            self.manager.current = "player_directory"
            return
        except Exception:
            logger.exception("CSV export failed for player_id=%s", self.player_id)
            show_message_popup(
                "Export Notice",
                "CSV export failed. Check the cloud connection and try again.",
                size_hint=(0.78, 0.38),
            )
            return

        show_message_popup(
            "Export Notice",
            f"CSV exported:\n{output}",
            size_hint=(0.84, 0.4),
        )

    def go_back(self):
        self.manager.current = "player_directory"
