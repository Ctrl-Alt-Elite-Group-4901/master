from kivy.app import App
from kivy.uix.label import Label

# This is your main application class
class AreteApp(App):
    def build(self):
        # The build() method defines what shows on screen
        return Label(text="Hello, ARETE!")

# This makes sure the app runs when you start main.py
if __name__ == "__main__":
    AreteApp().run()
