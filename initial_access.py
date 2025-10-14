from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty
from kivy.lang import Builder
import json
import os

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
                    self.manager.reset_to('home')
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

    def update_day_spinner(self):
        """
        Called when year or month changes.
        Updates the 'day' spinner with the correct number of days.
        """
        year_text = self.ids.year_spinner.text
        month_text = self.ids.month_spinner.text

        if year_text != 'Ano' and month_text != 'Mês':
            # Get the correct number of days
            num_days = get_days_for_month(year_text, month_text)
            # Update the spinner values
            self.ids.day_spinner.values = [str(i) for i in range(1, num_days + 1)]
            # Enable the spinner
            self.ids.day_spinner.disabled = False
        else:
            # If year or month is not selected, disable the day spinner
            self.ids.day_spinner.disabled = True
            self.ids.day_spinner.text = 'Dia'

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

        # --- Gather common data ---
        user_data = {
            "profile_type": self.profile_type,
            "name": self.ids.name_input.text,
            "email": self.ids.email_input.text,
            "password": self.ids.password_input.text,  # DANGER: In a real app, you MUST hash the password!
        }

        # --- Gather patient-specific data if applicable ---
        is_patient = self.profile_type == 'patient' or self.is_also_patient
        if is_patient:
            day = self.ids.day_spinner.text
            month_name = self.ids.month_spinner.text
            year = self.ids.year_spinner.text

            # Create a dictionary for the date of birth
            dob_dict = {}
            if day != 'Dia' and month_name != 'Mês' and year != 'Ano':
                month_num = MONTH_NAME_TO_NUM.get(month_name)
                dob_dict = {
                    "day": day,
                    "month": str(month_num),
                    "year": year
                }

            user_data["patient_info"] = {
                "height_cm": self.ids.height_input.text,
                "date_of_birth": dob_dict,
                "sex": self.ids.sex_input.text
            }

        # --- Load existing accounts and append the new one ---
        accounts = []
        if os.path.exists('account.json'):
            try:
                with open('account.json', 'r') as f:
                    accounts = json.load(f)
                    # Ensure it's a list
                    if not isinstance(accounts, list):
                        accounts = []
            except json.JSONDecodeError:
                accounts = []  # File is corrupted or empty, start fresh

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
            self.manager.reset_to('home')

class HomeScreen(Screen):
    """
    The main screen after a user is logged in.
    """
    pass
