from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock
import os
import json


class NavigationScreenManager(ScreenManager):  # Example base class, adjust as needed
	
    screen_stack = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # We use Clock.schedule_once to ensure this runs after the .kv rules have been applied
        # and all screens are available in the manager.
        Clock.schedule_once(self.check_session)

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(__file__), filename)

    def check_session(self, dt):
        """Checks for a saved session and sets the initial screen."""
        session_path = self._get_main_dir_path('session.json')
        if os.path.exists(session_path):
            try:
                with open(session_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                if session_data.get('logged_in'):
                    profile_type = session_data.get('profile_type')
                    print(f"Found active session for profile: {profile_type}")

                    if profile_type == 'doctor':
                        self.current = 'doctor_home'
                    else:
                        self.current = 'patient_home'
                    return

            except (json.JSONDecodeError, FileNotFoundError):
                pass  # If file is corrupted or not found, default to initial_access
        
        self.current = 'initial_access'

    def push(self, screen_name):
        ## empilhamos a screen atual e colocamos uma nova
        if not screen_name in self.screen_stack:
            self.screen_stack.append(self.current)
            self.current = screen_name
            self.transition.direction = "left"

    def pop(self):
        if len(self.screen_stack)>0:
            last_screen = self.screen_stack[-1]
            del self.screen_stack[-1]
            self.current = last_screen
            self.transition.direction = "right"

    def reset_to(self, screen_name):
        """
        Clears the screen stack and sets the current screen.
        This is used to set a new root screen, e.g., after login.
        """
        self.screen_stack.clear()
        self.current = screen_name