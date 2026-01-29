# ===== areteDemo/screens/profile.py (UPDATED with score table) =====
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import areteDemo.auth as auth
import sqlite3


class Profile(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.user_id:
            self.manager.current = "login"
            return
        user = auth.get_user_by_id(app.user_id)
        
        if user:
            if 'first_name' in self.ids:
                self.ids.first_name.text = user.get('first_name', '')
            if 'last_name' in self.ids:
                self.ids.last_name.text = user.get('last_name', '')
            if 'email' in self.ids:
                self.ids.email.text = user.get('email', '')
        
        self.load_top_scores()

    def load_top_scores(self):
        """Load and display user's top 5 scores"""
        app = App.get_running_app()
        scores = auth.get_user_scores(app.user_id, limit=5)
        
        if 'scores_table' in self.ids:
            scores_text = "Top 5 Scores:\n" + "-" * 30 + "\n"
            if scores:
                for i, score in enumerate(scores, 1):
                    scores_text += f"{i}. Score: {score['score']}\n"
            else:
                scores_text += "No scores yet. Play a game!"
            
            self.ids.scores_table.text = scores_text

    def save_profile(self):
        app = App.get_running_app()
        if not app.user_id:
            self._show_message("Not logged in.")
            return
        
        first = self.ids.first_name.text.strip()
        last = self.ids.last_name.text.strip()
        email = self.ids.email.text.strip()
        
        if not email:
            self._show_message("Email is required.")
            return
        
        try:
            success = auth.update_user(app.user_id, first, last, email)
            if success:
                self._show_message("Profile updated successfully!")
            else:
                self._show_message("Failed to update profile.")
        except sqlite3.IntegrityError:
            self._show_message("Email already in use.")

    def go_to_settings(self):
        self.manager.current = "settings"

    def _show_message(self, text):
        popup = Popup(title="Profile", content=Label(text=text), size_hint=(0.7, 0.35))