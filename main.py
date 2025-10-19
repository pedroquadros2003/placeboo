from kivy.config import Config

# Desabilita a simulação de multitoque (bolinhas vermelhas) com o mouse
Config.set('input', 'mouse', 'mouse,disable_multitouch')

def load_window_settings():
    """Define um tamanho de janela fixo para simular um dispositivo móvel."""
    width = 360
    height = 640
    Config.set('graphics', 'width', str(width))
    Config.set('graphics', 'height', str(height))

# Must be called before other Kivy modules are imported
load_window_settings()

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from navigation_screen_manager import NavigationScreenManager
# Importa as telas para que o Kivy as reconheça ao carregar os arquivos .kv
from initial_access import InitialAccessScreen, LoginScreen, SignUpScreen
from patient_profile.patient_screens import PatientHomeScreen, PatientMenuScreen
from patient_profile.patient_screens import PatientAppSettingsScreen, ManageDoctorsScreen
from doctor_profile.doctor_screens import DoctorHomeScreen, DoctorMenuScreen, DoctorSettingsScreen
from doctor_profile.graph_view_screen import GraphViewScreen
 
# Importa as classes de view que não são telas, mas são usadas nos arquivos .kv
from patient_profile.patient_settings_view import PatientAppSettingsView
from auxiliary_classes.popup_label import PopupLabel
from auxiliary_classes.change_password_view import ChangePasswordScreen # Import the screen


class MyScreenManager(NavigationScreenManager):
    pass

class PlaceboApp (App):  ## Aplicações em Kivy terminam em App
    manager = ObjectProperty(None)
    
    def build(self):
        self.manager = MyScreenManager()
        return self.manager

    def show_popup(self, message, is_success=False):
        """Exibe um popup (erro ou sucesso) na parte inferior da tela."""
        popup = PopupLabel(text=message)
        if is_success:
            popup.bg_color = (0.2, 0.8, 0.2, 1) # Green for success
        else:
            popup.bg_color = (0.8, 0.2, 0.2, 1) # Red for error
        popup.show(message)

    def show_error_popup(self, message): self.show_popup(message, is_success=False)
    def show_success_popup(self, message): self.show_popup(message, is_success=True)

PlaceboApp().run()