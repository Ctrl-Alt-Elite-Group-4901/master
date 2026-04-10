from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput


TEXT_PRIMARY = (0.89, 0.91, 0.87, 1)
TEXT_MUTED = (0.64, 0.68, 0.64, 1)
ACCENT = (0.41, 0.85, 1, 1)
PRIMARY = (0.77, 1, 0.8, 1)
DANGER = (0.9, 0.36, 0.23, 1)
SURFACE = (0.05, 0.06, 0.05, 0.98)
INPUT = (0.14, 0.16, 0.15, 0.98)


def _bind_rect(widget, rect):
    def sync(instance, _value):
        rect.pos = instance.pos
        rect.size = instance.size

    widget.bind(pos=sync, size=sync)


def themed_frame(spacing=12, padding=16):
    frame = BoxLayout(orientation="vertical", spacing=spacing, padding=padding)
    with frame.canvas.before:
        Color(*SURFACE)
        background = Rectangle(pos=frame.pos, size=frame.size)
    _bind_rect(frame, background)
    return frame


def themed_label(text, font_size="15sp", bold=False, halign="center", color=TEXT_PRIMARY):
    label = Label(
        text=text,
        font_size=font_size,
        bold=bold,
        color=color,
        halign=halign,
        valign="middle",
    )
    label.bind(size=lambda instance, value: setattr(instance, "text_size", value))
    return label


def themed_button(text, variant="primary", height=46):
    palette = {
        "primary": ((0.77, 1, 0.8, 1), (0.0, 0.29, 0.13, 1)),
        "secondary": ((0.12, 0.14, 0.13, 0.96), PRIMARY),
        "danger": (DANGER, (1, 0.94, 0.93, 1)),
    }
    background_color, text_color = palette[variant]
    return Button(
        text=text,
        size_hint_y=None,
        height=height,
        bold=True,
        background_normal="",
        background_down="",
        background_color=background_color,
        color=text_color,
    )


def themed_input(hint_text="", password=False):
    return TextInput(
        hint_text=hint_text,
        password=password,
        multiline=False,
        background_normal="",
        background_active="",
        background_color=INPUT,
        foreground_color=(0.93, 0.96, 0.92, 1),
        hint_text_color=TEXT_MUTED,
        cursor_color=PRIMARY,
        padding=[dp(14), dp(14), dp(14), dp(14)],
    )


def themed_popup(title, content, size_hint=(0.72, 0.35), auto_dismiss=True):
    popup = Popup(title=title, content=content, size_hint=size_hint, auto_dismiss=auto_dismiss)
    popup.title_align = "center"
    popup.title_color = PRIMARY
    popup.separator_color = ACCENT
    popup.background = ""
    popup.background_color = (0.02, 0.03, 0.02, 0.96)
    return popup


def show_message_popup(title, text, size_hint=(0.72, 0.35)):
    content = themed_frame()
    message = themed_label(text, halign="center")
    dismiss = themed_button("OK", variant="primary", height=44)
    content.add_widget(message)
    content.add_widget(dismiss)
    popup = themed_popup(title, content, size_hint=size_hint)
    dismiss.bind(on_release=popup.dismiss)
    popup.open()
    return popup
