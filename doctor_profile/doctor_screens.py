from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty, DictProperty
import json
import os
from datetime import datetime
from doctor_profile import medication_view
from doctor_profile import events_view
from doctor_profile import diagnostics_view
from doctor_profile import doctor_settings_view
from doctor_profile import patient_management_view
from doctor_profile import patient_settings_view
from doctor_profile import doctor_patient_evolution_view

# Loads the associated kv file
Builder.load_file("doctor_profile/doctor_screens.kv", encoding='utf-8')

class DoctorHomeScreen(Screen):
    """
    Main screen for the Doctor/Caregiver profile.
    Corresponds to requirements [R010], [R011], [R012].
    """
    title = StringProperty("Hoje: ")  # Default value
    patient_list = ListProperty([])
    patient_map = DictProperty({}) # To map patient names to emails

    def on_enter(self, *args):
        """
        Called when the screen is about to be shown.
        Loads date and linked patients.
        """
        self.load_and_set_date()
        self.load_linked_patients()

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        # Assumes main.py is in the parent directory of 'doctor_profile'
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def load_linked_patients(self):
        """Loads the doctor's linked patients to populate the spinner."""
        doctor_user = ""
        # Get logged-in doctor's user from session
        if os.path.exists(self._get_main_dir_path('session.json')):
            with open(self._get_main_dir_path('session.json'), 'r') as f:
                session_data = json.load(f)
                if session_data.get('profile_type') == 'doctor':
                    doctor_user = session_data.get('user')

        if not doctor_user or not os.path.exists(self._get_main_dir_path('account.json')):
            self.patient_list = ["Nenhum paciente vinculado"]
            return

        with open(self._get_main_dir_path('account.json'), 'r', encoding='utf-8') as f:
            accounts = json.load(f)

        doctor_account = next((acc for acc in accounts if acc['user'] == doctor_user), None)
        if not doctor_account:
            self.patient_list = ["Nenhum paciente vinculado"]
            return
            
        linked_patient_ids = doctor_account.get('linked_patients', []) if doctor_account else []
        self_patient_id = doctor_account.get('self_patient_id')

        patient_names = []
        self.patient_map = {}

        # Add the "self" patient profile first if it exists
        if self_patient_id and self_patient_id in linked_patient_ids:
            self_patient_account = next((acc for acc in accounts if acc.get('id') == self_patient_id), None)
            if self_patient_account:
                patient_names.append("__Eu__")
                self.patient_map["__Eu__"] = self_patient_account.get('user')

        for patient_id in linked_patient_ids:
            # Skip the self patient, as it's already added
            if patient_id == self_patient_id:
                continue
            patient_account = next((acc for acc in accounts if acc.get('id') == patient_id), None)
            if patient_account:
                user = patient_account.get('user')
                name = patient_account.get('name', user)
                patient_names.append(name)
                self.patient_map[name] = user
        
        self.patient_list = patient_names if patient_names else ["Nenhum paciente vinculado"]

    def load_and_set_date(self):
        """
        Loads the date from app_data.json and updates the title.
        If the file doesn't exist or is invalid, it uses the current system date.
        """
        # Use the system's current date directly
        date_str = datetime.now().strftime('%d/%m/%Y')
        self.title = f"Hoje: {date_str}"

    def on_patient_selected(self, patient_name):
        """Updates the medication view when a new patient is selected."""
        patient_user = self.patient_map.get(patient_name)
        if not patient_user:
            return

        # Update Medications View
        med_screen = self.ids.content_manager.get_screen('doctor_medications')
        med_screen.children[0].current_patient_user = patient_user
        med_screen.children[0].load_medications()

        # Update Events View
        events_screen = self.ids.content_manager.get_screen('doctor_events')
        events_screen.children[0].current_patient_user = patient_user
        events_screen.children[0].load_events()

        # Update Diagnostics View
        diagnostics_screen = self.ids.content_manager.get_screen('doctor_diagnostics')
        diagnostics_screen.children[0].current_patient_user = patient_user
        # The load_diagnostics method is called automatically by the on_current_patient_user property

        # Update Patient Settings View
        patient_settings_screen = self.ids.content_manager.get_screen('patient_settings')
        patient_settings_screen.children[0].current_patient_user = patient_user
        # The load_settings method is called automatically by the on_current_patient_user property

        # Update Patient Evolution View
        patient_evolution_screen = self.ids.content_manager.get_screen('doctor_evolution')
        patient_evolution_screen.children[0].current_patient_user = patient_user
        # The view will clear itself via on_current_patient_user


class DoctorMenuScreen(Screen):
    """
    Menu screen for the doctor, showing main navigation options.
    Corresponds to requirement [R011].
    """
    def go_to_screen(self, screen_name):
        # Special handling for app settings, which is a separate screen
        if screen_name == 'doctor_settings':
            if self.manager.has_screen(screen_name):
                self.manager.push(screen_name)
            else:
                print(f"Error: Screen '{screen_name}' not found.")
            return

        # For other options, switch the content on DoctorHomeScreen
        doctor_home_screen = self.manager.get_screen('doctor_home')
        if doctor_home_screen.ids.content_manager.has_screen(screen_name):
            doctor_home_screen.ids.content_manager.current = screen_name
            self.manager.pop() # Go back to the home screen to show the new content
        else:
            print(f"Error: Screen '{screen_name}' not found.")

class DoctorMedicationsContentScreen(Screen):
    """A screen to host the MedicationsView widget inside the content manager."""
    pass

class DoctorEventsContentScreen(Screen):
    """A screen to host the EventsView widget inside the content manager."""
    pass

class DoctorDiagnosticsContentScreen(Screen):
    """A screen to host the DiagnosticsView widget inside the content manager."""
    pass

class DoctorSettingsScreen(Screen):
    """A screen to host the DoctorSettingsView widget."""
    pass

class DoctorPatientSettingsContentScreen(Screen):
    """A screen to host the PatientSettingsView widget."""
    pass

class DoctorPatientEvolutionContentScreen(Screen):
    """A screen to host the PatientEvolutionView widget."""
    pass