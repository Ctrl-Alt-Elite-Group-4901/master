# areteDemo/screens/settings.py
import os

from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
import areteDemo.auth as auth
from areteDemo.screens.ui_helpers import (
    show_message_popup,
    themed_button,
    themed_frame,
    themed_input,
    themed_label,
    themed_popup,
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class Settings(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.user_id:
            self.manager.current = "login"

    def toggle_theme(self):
        app = App.get_running_app()
        current = app.theme_background
        if current[0] == 1:
            app.theme_background = [0.1, 0.1, 0.1, 1]
            app.theme_header = [0.05, 0.25, 0.55, 1]
            app.theme_footer = [0.15, 0.15, 0.15, 1]
            app.theme_card = [0.16, 0.18, 0.23, 0.98]
            app.theme_input = [0.2, 0.23, 0.29, 1]
            app.theme_text_primary = [0.94, 0.96, 0.99, 1]
            app.theme_text_muted = [0.67, 0.72, 0.79, 1]
            app.theme_button_secondary = [0.3, 0.36, 0.47, 1]
            app.theme_button_danger = [0.78, 0.32, 0.32, 1]
            app.theme_footer_text = [0.75, 0.78, 0.83, 1]
            app.login_background = os.path.join(BASE_DIR, "images", "background_space.png")
            app.menu_background = os.path.join(BASE_DIR, "images", "background_sea.png")
            self._show_message("Theme changed to dark mode.")
        else:
            app.theme_background = [1, 1, 1, 1]
            app.theme_header = [0.12, 0.45, 0.88, 1]
            app.theme_footer = [0.95, 0.95, 0.95, 1]
            app.theme_card = [1, 1, 1, 0.97]
            app.theme_input = [0.96, 0.97, 0.99, 1]
            app.theme_text_primary = [0.11, 0.14, 0.18, 1]
            app.theme_text_muted = [0.43, 0.47, 0.54, 1]
            app.theme_button_secondary = [0.24, 0.29, 0.37, 1]
            app.theme_button_danger = [0.82, 0.28, 0.28, 1]
            app.theme_footer_text = [0.33, 0.36, 0.41, 1]
            app.login_background = os.path.join(BASE_DIR, "images", "background_sky.png")
            app.menu_background = os.path.join(BASE_DIR, "images", "background_forest.png")
            self._show_message("Theme changed to light mode.")

    def show_change_password_dialog(self):
        content = themed_frame(spacing=10, padding=16)
        old_pass = themed_input("Old Password", password=True)
        new_pass = themed_input("New Password", password=True)
        confirm_pass = themed_input("Confirm New Password", password=True)
        content.add_widget(themed_label("Change Password", font_size="18sp", bold=True))
        content.add_widget(old_pass)
        content.add_widget(new_pass)
        content.add_widget(confirm_pass)
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        popup = themed_popup(
            "Change Password", content=content, size_hint=(0.8, 0.6), auto_dismiss=False
        )

        def change_password_action(instance):
            if new_pass.text != confirm_pass.text:
                self._show_message("New passwords don't match.")
                return
            if len(new_pass.text) < 4:
                self._show_message("Password must be at least 4 characters.")
                return
            app = App.get_running_app()
            success = auth.change_password(app.user_id, old_pass.text, new_pass.text)
            if success:
                popup.dismiss()
                self._show_message("Password changed successfully!")
            else:
                self._show_message("Old password is incorrect.")

        btn_change = themed_button("Change Password", variant="primary")
        btn_change.bind(on_release=change_password_action)
        btn_cancel = themed_button("Cancel", variant="secondary")
        btn_cancel.bind(on_release=popup.dismiss)
        button_layout.add_widget(btn_change)
        button_layout.add_widget(btn_cancel)
        content.add_widget(button_layout)
        popup.open()

    def show_delete_account_dialog(self):
        content = themed_frame(spacing=10, padding=16)
        content.add_widget(
            themed_label(
                "Are you sure you want to delete your account?\nThis action cannot be undone.",
                halign="center",
            )
        )
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        popup = themed_popup(
            "Delete Account", content=content, size_hint=(0.8, 0.4), auto_dismiss=False
        )

        def delete_action(instance):
            app = App.get_running_app()
            success = auth.delete_user(app.user_id)
            if success:
                popup.dismiss()
                app.user_id = None
                self.manager.current = "login"
            else:
                self._show_message("Failed to delete account.")

        btn_delete = themed_button("Delete Account", variant="danger")
        btn_delete.bind(on_release=delete_action)
        btn_cancel = themed_button("Cancel", variant="secondary")
        btn_cancel.bind(on_release=popup.dismiss)
        button_layout.add_widget(btn_delete)
        button_layout.add_widget(btn_cancel)
        content.add_widget(button_layout)
        popup.open()

    def _show_message(self, text):
        show_message_popup("Settings Notice", text, size_hint=(0.7, 0.35))
