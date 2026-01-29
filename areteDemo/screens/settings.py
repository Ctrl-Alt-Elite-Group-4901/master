from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
import areteDemo.auth as auth


class Settings(Screen):
    def on_pre_enter(self):
        app = App.get_running_app()
        if not app.user_id:
            self.manager.current = "login"

    def toggle_theme(self):
        app = App.get_running_app()
        current = app.theme_background
        if current[0] == 1:  
            app.theme_background = [0, 0, 0, 1]  
            self._show_message("Theme changed to dark mode.")
        else:
            app.theme_background = [1, 1, 1, 1]  
            self._show_message("Theme changed to light mode.")

    def show_change_password_dialog(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        old_pass = TextInput(hint_text='Old Password', password=True, multiline=False)
        new_pass = TextInput(hint_text='New Password', password=True, multiline=False)
        confirm_pass = TextInput(hint_text='Confirm New Password', password=True, multiline=False)
        
        content.add_widget(Label(text='Change Password'))
        content.add_widget(old_pass)
        content.add_widget(new_pass)
        content.add_widget(confirm_pass)
        
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        popup = Popup(title='Change Password', content=content, size_hint=(0.8, 0.6))
        
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
        
        btn_change = Button(text='Change Password')
        btn_change.bind(on_release=change_password_action)
        btn_cancel = Button(text='Cancel')
        btn_cancel.bind(on_release=popup.dismiss)
        
        button_layout.add_widget(btn_change)
        button_layout.add_widget(btn_cancel)
        content.add_widget(button_layout)
        
        popup.open()

    def show_delete_account_dialog(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text='Are you sure you want to delete your account?\nThis action cannot be undone.'))
        
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        popup = Popup(title='Delete Account', content=content, size_hint=(0.8, 0.4))
        
        def delete_action(instance):
            app = App.get_running_app()
            success = auth.delete_user(app.user_id)
            
            if success:
                popup.dismiss()
                app.user_id = None
                self.manager.current = "login"
                self._show_message("Account deleted successfully.")
            else:
                self._show_message("Failed to delete account.")
        
        btn_delete = Button(text='Delete Account', background_color=(1, 0, 0, 1))
        btn_delete.bind(on_release=delete_action)
        btn_cancel = Button(text='Cancel')
        btn_cancel.bind(on_release=popup.dismiss)
        
        button_layout.add_widget(btn_delete)
        button_layout.add_widget(btn_cancel)
        content.add_widget(button_layout)
        
        popup.open()

    def _show_message(self, text):
        popup = Popup(title="Settings", content=Label(text=text), size_hint=(0.7, 0.35))
        popup.open()