from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty
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
        self.ids.login_email.text = ''
        self.ids.login_password.text = ''

    def do_login(self, login_email, login_password):
        """
        Validates user credentials against the list of accounts in account.json.
        """
        print(f"Attempting login for: {login_email}")

        # Check if the account file exists.
        if not os.path.exists('account.json'):
            print("Login Error: No accounts found. Please sign up first.")
            # TODO: Show a popup to the user
            return

        with open('account.json', 'r') as f:
            accounts = json.load(f)

        # Find the user in the list of accounts
        for account in accounts:
            # IMPORTANT: In a real-world application, use a secure password hashing comparison.
            if account.get('email') == login_email and account.get('password') == login_password:
                print("Login successful!")
                profile_type = account.get('profile_type')
                # Save session state
                session_data = {
                    'logged_in': True, 
                    'email': login_email, 
                    'profile_type': profile_type
                }
                with open('session.json', 'w') as f:
                    json.dump(session_data, f)
                
                # Redirect based on profile type
                if profile_type == 'doctor':
                    self.manager.reset_to('doctor_home')
                else: # Default to patient home
                    self.manager.reset_to('patient_home')
                return  # Exit the function on success

        # If the loop completes, no user was found
        print("Login Failed: Invalid email or password.")
        # TODO: Show a popup to the user

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
        self.ids.email_input.text = ''
        self.ids.password_input.text = ''
        self.ids.height_input.text = ''
        self.ids.day_input.text = ''
        self.ids.month_spinner.text = 'Mês'
        self.ids.year_spinner.text = 'Ano'
        self.ids.sex_input.text = 'Sexo'
        self.ids.is_also_patient_switch.active = False

    def _generate_unique_id(self, id_type):
        """
        Generates a unique 8-digit numeric ID for a given profile type (doctor or patient).
        It checks for uniqueness against a corresponding JSON file.
        """
        filename = f"{id_type}_ids.json"
        existing_ids = []
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    existing_ids = json.load(f)
            except json.JSONDecodeError:
                pass # File is empty or corrupt, will be overwritten

        while True:
            new_id = str(random.randint(10000000, 99999999))
            if new_id not in existing_ids:
                # Save the new ID to the list
                existing_ids.append(new_id)
                with open(filename, 'w') as f:
                    json.dump(existing_ids, f, indent=4)
                return new_id

    def _load_accounts(self):
        """Safely loads accounts from the JSON file."""
        if os.path.exists('account.json'):
            with open('account.json', 'r') as f:
                try: return json.load(f)
                except json.JSONDecodeError: return []
        return []

    def create_account(self):
        """
        Gathers data from the input fields and saves it to a JSON file.
        """
        # --- Basic Validation (check if fields are empty) ---
        # A more robust validation would be needed for a real application.
        if not self.ids.name_input.text or not self.ids.email_input.text or not self.ids.password_input.text:
            print("Error: Name, Email, and Password are required.")
            # In a real app, you would show a popup here.
            return

        accounts = self._load_accounts()

        # --- Gather common data ---
        user_data = {
            "profile_type": self.profile_type,
            "name": self.ids.name_input.text,
            "email": self.ids.email_input.text,
            "password": self.ids.password_input.text,  # DANGER: In a real app, you MUST hash the password!
        }

        # Generate and add the unique ID based on profile type
        user_id = self._generate_unique_id(self.profile_type)
        user_data['id'] = user_id

        # --- Gather patient-specific data if applicable ---
        is_patient = self.profile_type == 'patient' or self.is_also_patient
        if is_patient:
            day = self.ids.day_input.text
            month_name = self.ids.month_spinner.text
            year = self.ids.year_spinner.text

            # --- Add validation for patient-specific fields ---
            if not self.ids.height_input.text or day == 'Dia' or month_name == 'Mês' or year == 'Ano' or self.ids.sex_input.text == 'Sexo':
                print("Validation Error: Para pacientes, todos os campos (altura, data de nascimento, sexo) são obrigatórios.")
                # TODO: Show a popup to the user
                return

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
                    print(f"Validation Error: Data de nascimento inválida. Valores recebidos: Dia='{day}', Mês='{month_name}', Ano='{year}'")
                    return # Stop account creation if date is bad

            user_data["patient_info"] = {
                "height_cm": self.ids.height_input.text,
                "date_of_birth": dob_dict,
                "sex": self.ids.sex_input.text
            }
            # The patient code is now the main user ID
            user_data["patient_info"]["patient_code"] = user_id


        # --- Load existing accounts and append the new one ---
        
        # Check for duplicate email
        if any(acc['email'] == user_data['email'] for acc in accounts):
            print(f"Error: Account with email {user_data['email']} already exists.")
            # TODO: Show a popup to the user
            return

        accounts.append(user_data)
        with open('account.json', 'w') as json_file:
            json.dump(accounts, json_file, indent=4)

        print(f"Account created successfully! Data saved to account.json")
        
        # Also create a session for the new user, including profile type
        session_data = {
            'logged_in': True,
            'email': user_data['email'],
            'profile_type': user_data['profile_type']
        }
        with open('session.json', 'w') as f:
            json.dump(session_data, f)

        # Redirect to the correct home screen based on the new profile
        if user_data['profile_type'] == 'doctor':
            self.manager.reset_to('doctor_home')
        else:
            self.manager.reset_to('patient_home')

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]
