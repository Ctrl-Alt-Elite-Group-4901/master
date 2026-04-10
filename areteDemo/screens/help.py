# areteDemo/screens/help.py
from kivy.uix.screenmanager import Screen
from areteDemo.screens.ui_helpers import show_message_popup


class HelpScreen(Screen):
    def show_about(self):
        show_message_popup(
            "About Arete",
            "Arete Demo\nHelp & About\n\nUse SPACE to jump over obstacles.\nSurvive for 5 minutes!",
            size_hint=(0.7, 0.4),
        )
