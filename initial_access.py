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
        Sends a login request to the backend via the outbox.
        The UI will wait for an 'account/success_login' message in the inbox to proceed.
        """
        if not login_user or not login_password:
            App.get_running_app().show_error_popup("Usuário e senha são obrigatórios.")
            return

        print(f"Sending login request for: {login_user}")
        try_login_payload = {"user": login_user, "password": login_password}
        app = App.get_running_app()
        request_id = app.outbox_processor.add_to_outbox("account", "try_login", try_login_payload)
        app.pending_request_id = request_id # Armazena o ID da requisição
        App.get_running_app().show_success_popup("Verificando credenciais...")

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
        Gathers data from the input fields, sends a 'create_account' message
        to the backend via the outbox, and waits for a response to log in.
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

        # --- Adiciona mensagem ao outbox_messages.json ---
        # A mensagem é criada antes de modificar os arquivos locais.
        create_account_payload = {
            "profile_type": self.profile_type,
            "name": self.ids.name_input.text,
            "user": self.ids.user_input.text,
            "password": self.ids.password_input.text,
            "is_also_patient": self.is_also_patient,
            "patient_info": patient_specific_info
        }
        app = App.get_running_app()
        request_id = app.outbox_processor.add_to_outbox("account", "create_account", create_account_payload)
        app.pending_request_id = request_id # Armazena o ID da requisição
        App.get_running_app().show_success_popup("Enviando dados para criação da conta...")

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]
