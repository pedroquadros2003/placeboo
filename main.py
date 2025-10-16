from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.config import Config
import json
from kivy.utils import platform
import os
from navigation_screen_manager import NavigationScreenManager


def load_window_settings():
    """Loads window size from config.json and applies it."""
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                settings = json.load(f)
                width = settings.get("window_width", 1080)
                height = settings.get("window_height", 2340)

                # Apply a scaling factor for desktop development for a more manageable window size
                if platform in ('win', 'linux', 'macosx'):
                    scale = settings.get("dev_scale_factor", 1.0)
                    width = int(width * scale)
                    height = int(height * scale)

                Config.set('graphics', 'width', str(width))
                Config.set('graphics', 'height', str(height))
        except (json.JSONDecodeError, ValueError, FileNotFoundError):
            print("Error loading config.json, using default window size.")


class MyScreenManager(NavigationScreenManager):
    pass


class PlaceboApp (App):  ## Aplicações em Kivy terminam em App
    manager = ObjectProperty(None)
    
    def build(self):
        self.manager = MyScreenManager()
        return self.manager

load_window_settings()
PlaceboApp().run()