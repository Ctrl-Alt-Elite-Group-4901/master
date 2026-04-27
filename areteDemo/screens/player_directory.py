from functools import partial

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen

from areteDemo import run_data
from areteDemo.screens.ui_helpers import show_message_popup


class PlayerDirectory(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.is_dev_mode:
            self.manager.current = "login"
            return

        if not run_data.is_cloud_enabled():
            config_error = run_data.get_cloud_config_error()
            self._clear_players_view(config_error or "Cloud API is not configured.")
            self._show_connect_banner(
                config_error or "Player Directory uses cloud database data only. Configure cloud_config.json first.",
                is_error=True,
            )
            return

        if run_data.is_cloud_enabled() and not run_data.has_admin_token():
            self._clear_players_view("Connect an admin token to load player data.")
            self._show_connect_banner("Paste the admin token to view cloud player data.", is_error=False)
            return

        self._hide_connect_banner()
        self.load_players()

    def load_players(self):
        try:
            players = run_data.list_players_for_directory()
        except run_data.CloudAuthError:
            run_data.clear_admin_token()
            self._clear_players_view("Admin token was rejected. Reconnect to continue.")
            self._show_connect_banner("Token rejected by the server. Paste a new one.", is_error=True)
            return
        except Exception as exc:
            self._clear_players_view(f"Failed to load players: {exc}")
            show_message_popup("Directory Notice", str(exc), size_hint=(0.78, 0.38))
            return

        self._hide_connect_banner()

        container = self.ids.players_list
        container.clear_widgets()

        if not players:
            self.ids.status_label.text = "No players found yet."
            return

        self.ids.status_label.text = f"{len(players)} player(s) found."
        for player in players:
            text = (
                f"{player['display_name']} ({player['username']})\n"
                f"{player['email']}  |  Runs: {player['run_count']}"
            )
            btn = Button(
                text=text,
                size_hint_y=None,
                height=dp(78),
                bold=True,
                halign="left",
                valign="middle",
                text_size=(0, 0),
                background_normal="",
                background_down="",
                background_color=(0.12, 0.14, 0.13, 0.96),
                color=(0.77, 1, 0.8, 1),
            )
            btn.bind(size=lambda instance, _value: setattr(instance, "text_size", (instance.width - dp(20), instance.height)))
            btn.bind(
                on_release=partial(
                    self.open_player_runs,
                    player_id=player["id"],
                    display_name=player["display_name"],
                    username=player["username"],
                    email=player["email"],
                )
            )
            container.add_widget(btn)

    def open_player_runs(self, _instance, player_id: int, display_name: str, username: str, email: str):
        runs_screen = self.manager.get_screen("player_runs")
        runs_screen.set_player(
            player_id=player_id,
            display_name=display_name,
            username=username,
            email=email,
        )
        self.manager.current = "player_runs"

    def connect_cloud(self):
        token_input = self.ids.get("token_input")
        token = (token_input.text if token_input else "").strip()
        if not token:
            self._show_connect_banner("Enter a token first.", is_error=True)
            return

        try:
            run_data.verify_and_save_admin_token(token)
        except run_data.CloudAuthError:
            self._show_connect_banner("Invalid token. Ask your administrator for a new one.", is_error=True)
            return
        except Exception as exc:
            self._show_connect_banner(f"Could not reach the cloud: {exc}", is_error=True)
            return

        if token_input:
            token_input.text = ""
        self._hide_connect_banner()
        self.load_players()

    def disconnect_cloud(self):
        run_data.clear_admin_token()
        self._clear_players_view("Disconnected from cloud.")
        self._show_connect_banner("Disconnected. Paste a token to reconnect.", is_error=False)

    def _clear_players_view(self, status_text: str) -> None:
        self.ids.players_list.clear_widgets()
        self.ids.status_label.text = status_text

    def _show_connect_banner(self, message: str, is_error: bool) -> None:
        banner = self.ids.get("connect_banner")
        label = self.ids.get("connect_banner_message")
        if banner is None or label is None:
            return
        label.text = message
        label.color = (1, 0.55, 0.55, 1) if is_error else (0.41, 0.85, 1, 1)
        banner.opacity = 1
        banner.disabled = False
        banner.height = dp(180)

    def _hide_connect_banner(self) -> None:
        banner = self.ids.get("connect_banner")
        if banner is None:
            return
        banner.opacity = 0
        banner.disabled = True
        banner.height = 0

    def go_back(self):
        self.manager.current = "editor_menu"
