import os
import json
from kivy.config import Config
from kivy.utils import platform

def load_window_settings():
    """Loads window size from config.json and applies it BEFORE Kivy is fully imported."""
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                settings = json.load(f)
                width = settings.get("window_width", 1080)
                height = settings.get("window_height", 2340)
                if platform in ('win', 'linux', 'macosx'):
                    scale = settings.get("dev_scale_factor", 1.0)
                    width = int(width * scale)
                    height = int(height * scale)
                Config.set('graphics', 'width', str(width))
                Config.set('graphics', 'height', str(height))
        except (json.JSONDecodeError, ValueError, FileNotFoundError):
            print("Error loading config.json, using default window size.")

# Must be called before other Kivy modules are imported
load_window_settings()

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from navigation_screen_manager import NavigationScreenManager
# Importa as telas para que o Kivy as reconheça ao carregar os arquivos .kv
from initial_access import InitialAccessScreen, LoginScreen, SignUpScreen
from patient_profile.patient_screens import PatientHomeScreen, PatientMenuScreen
from patient_profile.patient_screens import PatientAppSettingsScreen, AddDoctorScreen # Novas: Importa estas como telas de nível superior
from doctor_profile.doctor_screens import DoctorHomeScreen, DoctorMenuScreen, DoctorSettingsScreen
from doctor_profile.graph_view_screen import GraphViewScreen
 
# Importa as classes de view que não são telas, mas são usadas nos arquivos .kv
from patient_profile.add_doctor_view import AddDoctorView
from patient_profile.patient_settings_view import PatientAppSettingsView


class MyScreenManager(NavigationScreenManager):
    pass

class PlaceboApp (App):  ## Aplicações em Kivy terminam em App
    manager = ObjectProperty(None)
    
    def build(self):
        self.manager = MyScreenManager()
        return self.manager

PlaceboApp().run()