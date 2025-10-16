from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.app import App
import os

# Loads the associated kv file
Builder.load_file("doctor_settings_view.kv", encoding='utf-8')

class DoctorSettingsView(RelativeLayout):
    """
    Screen for doctor-specific settings, such as logging out.
    """
    def logout(self):
        """
        Logs the user out by deleting the session file and returning to the initial screen.
        """
        print("Logging out...")
        if os.path.exists('session.json'):
            try:
                os.remove('session.json')
                print("Session file deleted.")
            except OSError as e:
                print(f"Error deleting session file: {e}")
        
        App.get_running_app().manager.reset_to('initial_access')