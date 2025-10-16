from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.app import App
import os
import json

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

    def delete_account(self):
        """
        Deletes all data associated with the current doctor's account.
        This is a destructive and irreversible action.
        """
        # Get current doctor's email and ID from session
        if not os.path.exists('session.json'): return
        with open('session.json', 'r') as f:
            session_data = json.load(f)
        doctor_email = session_data.get('email')
        if not doctor_email: return

        # --- Update account.json ---
        if os.path.exists('account.json'):
            with open('account.json', 'r+', encoding='utf-8') as f:
                try:
                    accounts = json.load(f)
                    
                    # Get doctor ID before removing the account
                    doctor_account = next((acc for acc in accounts if acc.get('email') == doctor_email), None)
                    doctor_id = doctor_account.get('id') if doctor_account else None

                    # Remove the doctor's account
                    accounts = [acc for acc in accounts if acc.get('email') != doctor_email]

                    # Unlink this doctor from any patient's responsible_doctors list
                    for i, acc in enumerate(accounts):
                        if acc.get('profile_type') == 'patient' and doctor_id:
                            if 'responsible_doctors' in acc.get('patient_info', {}) and doctor_id in acc['patient_info']['responsible_doctors']:
                                accounts[i]['patient_info']['responsible_doctors'].remove(doctor_id)

                    f.seek(0)
                    json.dump(accounts, f, indent=4)
                    f.truncate()

                    # --- Update doctor_ids.json ---
                    if doctor_id and os.path.exists('doctor_ids.json'):
                        with open('doctor_ids.json', 'r+', encoding='utf-8') as id_f:
                            doctor_ids = json.load(id_f)
                            if doctor_id in doctor_ids:
                                doctor_ids.remove(doctor_id)
                            id_f.seek(0)
                            json.dump(doctor_ids, id_f, indent=4)
                            id_f.truncate()

                except (json.JSONDecodeError, FileNotFoundError):
                    pass

        print(f"Account and all associated data for {doctor_email} have been deleted.")
        self.logout() # Log out to clear session and return to initial screen