from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.app import App
import os
import json

# Loads the associated kv file
Builder.load_file("doctor_profile/doctor_settings_view.kv", encoding='utf-8')

class DoctorSettingsView(RelativeLayout):
    """
    Screen for doctor-specific settings, such as logging out.
    """
    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def logout(self):
        """
        Logs the user out by deleting the session file and returning to the initial screen.
        """
        print("Logging out...")
        session_path = self._get_main_dir_path('session.json')
        if os.path.exists(session_path):
            try:
                os.remove(self._get_main_dir_path('session.json'))
                print("Session file deleted.")
            except OSError as e:
                print(f"Error deleting session file: {e}")
        
        App.get_running_app().manager.reset_to('initial_access')

    def change_password(self):
        """Navigates to the change password screen."""
        session_path = self._get_main_dir_path('session.json')
        if os.path.exists(session_path):
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            user_name = session_data.get('user')
            if user_name:
                change_password_screen = App.get_running_app().manager.get_screen('change_password')
                change_password_screen.ids.change_password_view_content.current_user_name = user_name
                App.get_running_app().manager.push('change_password')
            else:
                print("Erro: Usuário não encontrado na sessão.")
                # TODO: Show popup

    def delete_account(self):
        """
        Deletes all data associated with the current doctor's account.
        This is a destructive and irreversible action.
        """
        session_path = self._get_main_dir_path('session.json')
        # Get current doctor's user and ID from session
        if not os.path.exists(session_path): return
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        doctor_user = session_data.get('user')
        if not doctor_user: return

        # --- Update account.json ---
        accounts_path = self._get_main_dir_path('account.json')
        if os.path.exists(accounts_path):
            with open(accounts_path, 'r+', encoding='utf-8') as f:
                try:
                    accounts = json.load(f)
                    
                    # Get doctor ID before removing the account
                    doctor_account = next((acc for acc in accounts if acc.get('user') == doctor_user), None)
                    doctor_id = doctor_account.get('id') if doctor_account else None

                    # Remove the doctor's account
                    accounts = [acc for acc in accounts if acc.get('user') != doctor_user]

                    # Unlink this doctor from any patient's responsible_doctors list
                    for i, acc in enumerate(accounts):
                        if acc.get('profile_type') == 'patient' and doctor_id:
                            if 'responsible_doctors' in acc.get('patient_info', {}) and doctor_id in acc['patient_info']['responsible_doctors']:
                                accounts[i]['patient_info']['responsible_doctors'].remove(doctor_id)

                    f.seek(0)
                    json.dump(accounts, f, indent=4)
                    f.truncate()

                    # --- Update doctor_ids.json ---
                    doctor_ids_path = self._get_main_dir_path('doctor_ids.json')
                    if doctor_id and os.path.exists(doctor_ids_path):
                        with open(doctor_ids_path, 'r+', encoding='utf-8') as id_f:
                            doctor_ids = json.load(id_f)
                            if doctor_id in doctor_ids:
                                doctor_ids.remove(doctor_id)
                            id_f.seek(0)
                            json.dump(doctor_ids, id_f, indent=4)
                            id_f.truncate()

                except (json.JSONDecodeError, FileNotFoundError):
                    pass

        App.get_running_app().show_success_popup(f"Conta e todos os dados associados para {doctor_user} foram deletados.")
        self.logout() # Log out to clear session and return to initial screen