from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty, DictProperty
import json
import os
from datetime import datetime
import medication_view # Import the new module
import events_view # Import the new module
import diagnostics_view # Import the new module
import doctor_settings_view # Import the new module
import patient_management_view # Import the new module
import patient_settings_view # Import the new module
import patient_evolution_view # Import the new module

# Loads the associated kv file
Builder.load_file("doctor_screens.kv", encoding='utf-8')

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

    def load_linked_patients(self):
        """Loads the doctor's linked patients to populate the spinner."""
        doctor_email = ""
        # Get logged-in doctor's email from session
        if os.path.exists('session.json'):
            with open('session.json', 'r') as f:
                session_data = json.load(f)
                if session_data.get('profile_type') == 'doctor':
                    doctor_email = session_data.get('email')

        if not doctor_email or not os.path.exists('account.json'):
            self.patient_list = ["Nenhum paciente vinculado"]
            return

        with open('account.json', 'r', encoding='utf-8') as f:
            accounts = json.load(f)

        doctor_account = next((acc for acc in accounts if acc['email'] == doctor_email), None)
        linked_patient_ids = doctor_account.get('linked_patients', []) if doctor_account else []

        patient_names = []
        self.patient_map = {}
        for patient_id in linked_patient_ids:
            patient_account = next((acc for acc in accounts if acc.get('id') == patient_id), None)
            if patient_account:
                email = patient_account.get('email')
                name = patient_account.get('name', email)
                patient_names.append(name)
                self.patient_map[name] = email
        
        self.patient_list = patient_names if patient_names else ["Nenhum paciente vinculado"]

    def load_and_set_date(self):
        """
        Loads the date from app_data.json and updates the title.
        If the file doesn't exist or is invalid, it uses the current system date.
        """
        date_str = ""
        if os.path.exists('app_data.json'):
            try:
                with open('app_data.json', 'r') as f:
                    data = json.load(f)
                date_from_json = data.get("current_date")  # Expected format: "YYYY-MM-DD"
                if date_from_json:
                    date_obj = datetime.strptime(date_from_json, '%Y-%m-%d')
                    date_str = date_obj.strftime('%d/%m/%Y')
            except (json.JSONDecodeError, ValueError, FileNotFoundError):
                pass  # Fallback to current date if file is bad

        if not date_str:
            date_str = datetime.now().strftime('%d/%m/%Y')

        self.title = f"Hoje: {date_str}"

    def on_patient_selected(self, patient_name):
        """Updates the medication view when a new patient is selected."""
        patient_email = self.patient_map.get(patient_name)
        if not patient_email:
            return

        # Update Medications View
        med_screen = self.ids.content_manager.get_screen('doctor_medications')
        med_screen.children[0].current_patient_email = patient_email
        med_screen.children[0].load_medications()

        # Update Events View
        events_screen = self.ids.content_manager.get_screen('doctor_events')
        events_screen.children[0].current_patient_email = patient_email
        events_screen.children[0].load_events()

        # Update Diagnostics View
        diagnostics_screen = self.ids.content_manager.get_screen('doctor_diagnostics')
        diagnostics_screen.children[0].current_patient_email = patient_email
        # The load_diagnostics method is called automatically by the on_current_patient_email property

        # Update Patient Settings View
        patient_settings_screen = self.ids.content_manager.get_screen('patient_settings')
        patient_settings_screen.children[0].current_patient_email = patient_email
        # The load_settings method is called automatically by the on_current_patient_email property

        # Update Patient Evolution View
        patient_evolution_screen = self.ids.content_manager.get_screen('doctor_evolution')
        patient_evolution_screen.children[0].current_patient_email = patient_email
        # The view will clear itself via on_current_patient_email


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