# ===== areteDemo/screens/game.py =====
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_widget = None
    
    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.user_id:
            self.manager.current = "login"
            return

    def on_enter(self):
        """Called when screen is displayed"""
        if self.game_widget:
            try:
                self.game_widget.stop()
                self.ids.game_container.remove_widget(self.game_widget)
            except:
                pass
        
        from areteDemo.endless_runner_game import EndlessRunnerGame
        self.game_widget = EndlessRunnerGame()
        self.ids.game_container.add_widget(self.game_widget)
    
    def on_leave(self):
        """Called when leaving screen"""
        if self.game_widget:
            try:
                self.game_widget.stop()
                self.ids.game_container.remove_widget(self.game_widget)
                self.game_widget = None
            except Exception as e:
                print(f"Error stopping game: {e}")
    
    def return_to_menu(self):
        """Return to main menu"""
        if self.game_widget:
            self.game_widget.stop()
        self.manager.current = "main_menu"

