from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty
from kivy.lang import Builder
import json


Builder.load_file("initial_acess.kv")


class InitialAccessScreen(Screen):
    """
    The very first screen of the application. Corresponds to requirement [R001].
    The user chooses their access profile here.
    """
    def on_profile_selection(self, profile_type: str):
        # Set the profile type on the sign_up screen so it knows which fields to show.
        self.manager.get_screen('sign_up').profile_type = profile_type

class SignUpScreen(Screen):
    """
    Account creation screen. Corresponds to requirements [R002], [R003], and [R004].
    The fields displayed change based on the profile type selected.
    """
    profile_type = StringProperty('')
    is_also_patient = BooleanProperty(False)

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
            "password": self.ids.password_input.text, # Note: In a real app, you must hash the password!
        }

        # --- Gather patient-specific data if applicable ---
        is_patient = self.profile_type == 'patient' or self.is_also_patient
        if is_patient:
            user_data["patient_info"] = {
                "height_cm": self.ids.height_input.text,
                "date_of_birth": self.ids.dob_input.text,
                "sex": self.ids.sex_input.text
            }

        # --- Save data to a JSON file ---
        with open('account.json', 'w') as json_file:
            json.dump(user_data, json_file, indent=4)

        print(f"Account created successfully! Data saved to account.json")
        # Here you would navigate to the main part of the app, e.g., app.manager.push('home_screen')
