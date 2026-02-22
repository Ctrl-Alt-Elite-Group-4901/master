# areteDemo/screens/help.py
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label


class HelpScreen(Screen):
    def show_about(self):
        Popup(
            title="About",
            content=Label(text="Arete Demo\nHelp & About\n\nUse SPACE to jump over obstacles.\nSurvive for 5 minutes!"),
            size_hint=(0.7, 0.4),
        ).open()
