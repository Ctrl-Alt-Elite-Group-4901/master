# areteDemo/screens/game.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from capstone_game_demo_kivy import GameWidget


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._game_widget = None

    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.user_id:
            self.manager.current = "login"
            return

        container = self.ids.game_container

        # Create GameWidget once per screen visit
        if self._game_widget is None:
            self._game_widget = GameWidget(embedded=True, size_hint=(1, 1))
            self._game_widget.on_game_over_callback = self._on_game_over
            container.add_widget(self._game_widget)

        self._game_widget.set_active(True)
        # Apply current player color from app
        self._apply_player_color()

    def _apply_player_color(self):
        app = App.get_running_app()
        gw = self._game_widget
        if gw is None:
            return
        if hasattr(gw, "set_player_color"):
            gw.set_player_color(*app.player_color)
        elif hasattr(gw, "player_color"):
            gw.player_color = list(app.player_color)

    def _on_game_over(self):
        """Called by GameWidget when the game ends. Save score and go to reflection."""
        app = App.get_running_app()
        gw = self._game_widget
        if gw and app.user_id:
            final_score = int(gw.score_distance) + gw.avoided_count * 100
            try:
                import areteDemo.auth as auth
                auth.add_score(app.user_id, final_score)
            except Exception as e:
                print(f"Score save error: {e}")

        sm = self.manager
        refl = sm.get_screen("reflection")
        refl.return_to = "game"
        refl.start_quiz()
        sm.current = "reflection"

    def on_leave(self):
        """Pause game when leaving screen."""
        if self._game_widget:
            self._game_widget.is_running = False
            self._game_widget.set_active(False)

    def return_to_menu(self):
        """Return to main menu and clean up game widget."""
        if self._game_widget:
            self._game_widget.is_running = False
            self._game_widget.dispose()
            try:
                self.ids.game_container.remove_widget(self._game_widget)
            except Exception:
                pass
            self._game_widget = None
        self.manager.current = "main_menu"
