from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty
from kivy.app import App
from kivy.lang import Builder
import json
import os
import random

from auxiliary_classes.date_checker import get_days_for_month, MONTH_NAME_TO_NUM


Builder.load_file("initial_access.kv", encoding='utf-8')

class InitialAccessScreen(Screen):
    """
    The very first screen of the application. Corresponds to requirement [R001].
    The user chooses their access profile here.
    """
    def on_profile_selection(self, profile_type: str):
        # Set the profile type on the sign_up screen so it knows which fields to show.
        # We also pass it to the login screen to be forwarded to the sign up screen if needed.
        self.manager.get_screen('login').profile_type = profile_type

class LoginScreen(Screen):
    """
    Login screen for existing users.
    Provides an option to navigate to the SignUpScreen.
    """
    profile_type = StringProperty('')

    def on_leave(self, *args):
        """Clear input fields when leaving the screen."""
        self.ids.login_user.text = ''
        self.ids.login_password.text = ''

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(__file__), filename)

    def do_login(self, login_user, login_password):
        """
        Validates user credentials against the list of accounts in account.json.
        """
        print(f"Attempting login for: {login_user}")

        accounts_path = self._get_main_dir_path('account.json')
        session_path = self._get_main_dir_path('session.json')

        # Check if the account file exists.
        if not os.path.exists(accounts_path):
            App.get_running_app().show_error_popup("Nenhuma conta encontrada. Cadastre-se primeiro.")
            return

        with open(accounts_path, 'r', encoding='utf-8') as f:
            accounts = json.load(f)

        # Find the user in the list of accounts
        user_found = False
        for account in accounts:
            # IMPORTANT: In a real-world application, use a secure password hashing comparison.
            if account.get('user') == login_user and account.get('password') == login_password:
                print("Login successful!")
                profile_type = account.get('profile_type')
                # Save session state
                session_data = {
                    'logged_in': True,
                    'user': login_user,
                    'profile_type': profile_type
                }
                with open(session_path, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f)
                
                # Redirect based on profile type
                if profile_type == 'doctor':
                    self.manager.reset_to('doctor_home')
                else: # Default to patient home
                    user_found = True
                    self.manager.reset_to('patient_home')
                return  # Exit the function on success

        # If the loop completes, no user was found
        App.get_running_app().show_error_popup("Usuário ou senha inválidos.")

    def go_to_signup(self):
        self.manager.get_screen('sign_up').profile_type = self.profile_type
        self.manager.push('sign_up')

class SignUpScreen(Screen):
    """
    Account creation screen. Corresponds to requirements [R002], [R003], and [R004].
    The fields displayed change based on the profile type selected.
    """
    profile_type = StringProperty('')
    is_also_patient = BooleanProperty(False)

    def on_leave(self, *args):
        """Clear all input fields when leaving the screen."""
        self.ids.name_input.text = ''
        self.ids.user_input.text = ''
        self.ids.password_input.text = ''
        self.ids.height_input.text = ''
        self.ids.day_input.text = ''
        self.ids.month_spinner.text = 'Mês'
        self.ids.year_spinner.text = 'Ano'
        self.ids.sex_input.text = 'Sexo'
        self.ids.is_also_patient_switch.active = False

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(__file__), filename)

    def _generate_unique_id(self, id_type):
        """
        Generates a unique 8-digit numeric ID for a given profile type (doctor or patient).
        It checks for uniqueness against a corresponding JSON file in the main project directory.
        """
        filename = f"{id_type}_ids.json"
        existing_ids = []
        ids_path = self._get_main_dir_path(filename)
        if os.path.exists(ids_path):
            try:
                with open(ids_path, 'r') as f:
                    existing_ids = json.load(f)
            except json.JSONDecodeError:
                pass # File is empty or corrupt, will be overwritten

        while True:
            new_id = str(random.randint(10000000, 99999999)) # 8-digit ID
            if new_id not in existing_ids:
                # Save the new ID to the list
                existing_ids.append(new_id)
                with open(self._get_main_dir_path(filename), 'w', encoding='utf-8') as f:
                    json.dump(existing_ids, f, indent=4)
                return new_id

    def _load_accounts(self):
        """Safely loads accounts from the JSON file."""
        accounts_path = self._get_main_dir_path('account.json')
        if os.path.exists(accounts_path):
            with open(accounts_path, 'r', encoding='utf-8') as f:
                try: return json.load(f)
                except json.JSONDecodeError: return []
        return []

    def create_account(self):
        """
        Gathers data from the input fields and saves it to a JSON file.
        """
        # --- Basic Validation (check if fields are empty) ---
        # A more robust validation would be needed for a real application.
        if not self.ids.name_input.text or not self.ids.user_input.text or not self.ids.password_input.text:
            App.get_running_app().show_error_popup("Nome, Usuário e Senha são obrigatórios.")
            return

        accounts = self._load_accounts()

        # --- Gather common data ---
        base_user_data = {
            "profile_type": self.profile_type,
            "name": self.ids.name_input.text,
            "user": self.ids.user_input.text,
            "password": self.ids.password_input.text,  # DANGER: In a real app, you MUST hash the password!
        }

        # Generate and add the unique ID based on profile type
        user_id = self._generate_unique_id(base_user_data['profile_type'])
        base_user_data['id'] = user_id

        # --- Gather patient-specific data if applicable ---
        is_patient = self.profile_type == 'patient' or self.is_also_patient
        if is_patient:
            # --- Add validation for patient-specific fields ---
            if not self.ids.height_input.text or self.ids.day_input.text == '' or self.ids.month_spinner.text == 'Mês' or self.ids.year_spinner.text == 'Ano' or self.ids.sex_input.text == 'Sexo':
                App.get_running_app().show_error_popup("Para pacientes, todos os campos são obrigatórios.")
                return

        # --- Check for duplicate user ---
        if any(acc['user'] == base_user_data['user'] for acc in accounts):
            App.get_running_app().show_error_popup(f"Usuário '{base_user_data['user']}' já existe.")
            return

        # --- Patient-specific data gathering (moved after validation) ---
        patient_specific_info = None
        if is_patient:
            day = self.ids.day_input.text
            month_name = self.ids.month_spinner.text
            year = self.ids.year_spinner.text

            # Create a dictionary for the date of birth
            dob_dict = {}
            if day and day != 'Dia' and month_name != 'Mês' and year != 'Ano':
                try:
                    num_days_in_month = get_days_for_month(year, month_name)
                    day_int = int(day)
                    if not (1 <= day_int <= num_days_in_month):
                        raise ValueError("Dia inválido para o mês selecionado.")
                    
                    month_num = MONTH_NAME_TO_NUM.get(month_name)
                    dob_dict = {
                        "day": day,
                        "month": str(month_num),
                        "year": year
                    }
                except (ValueError, KeyError):
                    App.get_running_app().show_error_popup("Data de nascimento inválida.")
                    return

            patient_specific_info = {
                "height_cm": self.ids.height_input.text,
                "date_of_birth": dob_dict,
                "sex": self.ids.sex_input.text
            }
            # If it's a regular patient, add info to the base data
            if self.profile_type == 'patient':
                base_user_data["patient_info"] = patient_specific_info
                # O patient_code é o próprio ID do paciente
                base_user_data["patient_info"]["patient_code"] = user_id 

        # --- Adiciona mensagem ao inbox_messages.json ---
        # A mensagem é criada antes de modificar os arquivos locais.
        create_account_payload = {
            "profile_type": self.profile_type,
            "name": self.ids.name_input.text,
            "user": self.ids.user_input.text,
            "password": self.ids.password_input.text,
            "is_also_patient": self.is_also_patient,
            "patient_info": patient_specific_info
        }
        App.get_running_app().inbox_processor.add_to_inbox_messages("account", "create_account", create_account_payload)

        accounts_path = self._get_main_dir_path('account.json')
        session_path = self._get_main_dir_path('session.json')

        # --- Handle the "Doctor is also a Patient" case ---
        if self.profile_type == 'doctor' and self.is_also_patient:
            # 1. Create the patient account for the doctor
            patient_id = self._generate_unique_id('patient')
            doctor_as_patient_account = {
                "profile_type": "patient",
                "name": base_user_data['name'],
                # Create a unique, internal username for this patient profile
                "user": f"{base_user_data['user']}_patient_profile",
                "password": "internal_use_only", # This account is not for direct login
                "id": patient_id,
                "patient_info": patient_specific_info
            }
            doctor_as_patient_account["patient_info"]["patient_code"] = patient_id
            # The doctor is responsible for their own patient profile
            doctor_as_patient_account["patient_info"]["responsible_doctors"] = [base_user_data['id']]
            accounts.append(doctor_as_patient_account)

            # 2. Update the doctor account to link to this new patient profile
            base_user_data['linked_patients'] = [patient_id]
            # Add a flag to easily identify this doctor as a self-patient
            base_user_data['self_patient_id'] = patient_id

            print(f"Created patient profile ({patient_id}) for doctor {base_user_data['id']}.")

        # Add the main account (doctor or patient) to the list
        accounts.append(base_user_data)

        with open(accounts_path, 'w', encoding='utf-8') as json_file:
            json.dump(accounts, json_file, indent=4)

        App.get_running_app().show_success_popup("Conta criada com sucesso!")
        
        # Also create a session for the new user, including profile type
        session_data = { 
            'logged_in': True,
            'user': base_user_data['user'],
            'profile_type': base_user_data['profile_type']
        }
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f)

        # Redirect to the correct home screen based on the new profile 
        if base_user_data['profile_type'] == 'doctor':
            self.manager.reset_to('doctor_home')
        else:
            self.manager.reset_to('patient_home')

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]
