from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, DictProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from outbox_handler.outbox_processor import OutboxProcessor
from kivy.app import App
from functools import partial
import json
from datetime import datetime
import uuid
import os

# Loads the associated kv file
Builder.load_file("doctor_profile/patient_management_view.kv", encoding='utf-8')

class PatientManagementView(RelativeLayout):
    """
    Screen for the doctor to manage their linked patients (CRUD).
    """
    patient_data = ListProperty([]) # Will store list of dicts: [{'name': '...', 'id': '...', 'user': '...'}]
    patient_map = DictProperty({}) # To map patient names to emails
    self_patient_id = StringProperty(None, allownone=True)

    def on_enter(self):
        """Called when the screen is entered. Loads the list of linked patients."""
        self.load_linked_patients()

    def load_linked_patients(self):
        """Loads the doctor's linked patients to populate the list."""
        doctor_user = self._get_doctor_user()
        if not doctor_user:
            self.patient_data = []
            self.patient_map = {}
            self.populate_patient_list()
            return

        accounts_path = self._get_main_dir_path('account.json')
        if not os.path.exists(accounts_path):
            self.patient_data = []
            self.populate_patient_list()
            return

        with open(accounts_path, 'r', encoding='utf-8') as f:
            accounts = json.load(f)

        doctor_account = next((acc for acc in accounts if acc['user'] == doctor_user), None)
        if not doctor_account:
            self.patient_data = []
            self.populate_patient_list()
            return

        linked_patient_ids = doctor_account.get('linked_patients', []) if doctor_account else []
        self.self_patient_id = doctor_account.get('self_patient_id')

        temp_patient_data = []
        self.patient_map = {}
        for patient_id in linked_patient_ids:
            patient_account = next((acc for acc in accounts if acc.get('id') == patient_id), None)
            if patient_account:
                user = patient_account.get('user')
                # Use "__Eu__" for the doctor's own patient profile
                name = "__Eu__" if patient_id == self.self_patient_id else patient_account.get('name', user)
                
                patient_info = {
                    'id': patient_id,
                    'name': name,
                    'user': user
                }
                temp_patient_data.append(patient_info)
                self.patient_map[name] = user
        
        self.patient_data = temp_patient_data
        self.populate_patient_list()

    def populate_patient_list(self):
        """Clears and repopulates the patient list widget."""
        patient_list_widget = self.ids.patient_list
        patient_list_widget.clear_widgets()

        if not self.patient_data:
            patient_list_widget.add_widget(Label(text='Nenhum paciente vinculado.', color=(0,0,0,1)))
            return

        for patient in self.patient_data:
            item_container = RelativeLayout(size_hint_y=None, height='48dp')
            
            name_label = Label(
                text=f'[b]{patient["name"]}[/b]', markup=True, color=(0,0,0,1),
                halign='left', valign='middle', size_hint=(0.6, 1),
                pos_hint={'x': 0.05, 'center_y': 0.5}
            )
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            item_container.add_widget(name_label)

            # Do not show the "Remove" button if the patient ID matches the doctor's self_patient_id
            if patient['id'] != self.self_patient_id:
                remove_button = Button(text='Remover', size_hint=(None, None), size=('100dp', '38dp'), pos_hint={'right': 0.98, 'center_y': 0.5})
                remove_button.bind(on_press=partial(self.remove_patient, patient['name']))
                item_container.add_widget(remove_button)

            patient_list_widget.add_widget(item_container)

    def invite_patient(self):
        """Sends an invitation to a patient by their username."""
        patient_user_to_invite = self.ids.patient_code_input.text
        if not patient_user_to_invite:
            App.get_running_app().show_error_popup("Por favor, insira o nome de usuário do paciente.")
            return

        doctor_user = self._get_doctor_user()
        accounts_path = self._get_main_dir_path('account.json')
        if not doctor_user or not os.path.exists(accounts_path):
            App.get_running_app().show_error_popup("Erro ao identificar o médico logado.")
            return

        # A lógica de validação e escrita foi movida para o backend.
        # A view apenas envia a solicitação.
        payload = {"patient_user_to_invite": patient_user_to_invite}
        App.get_running_app().outbox_processor.add_to_outbox("linking_accounts", "invite_patient", payload)
        App.get_running_app().show_success_popup(f"Convite enviado para {patient_user_to_invite}.")
        self.ids.patient_code_input.text = ''

    def remove_patient(self, patient_name, *args):
        """Unlinks a patient from the doctor."""
        patient_user = self.patient_map.get(patient_name)
        
        # A lógica de escrita foi movida para o backend.
        payload = {"target_user": patient_user}
        App.get_running_app().outbox_processor.add_to_outbox("linking_accounts", "unlink_accounts", payload)
        App.get_running_app().show_success_popup(f"Solicitação para desvincular {patient_name} enviada.")
        self.load_linked_patients() # Atualização otimista da UI

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def _get_doctor_user(self):
        """Helper to get the current doctor's user from the session file in user_data."""
        session_path = self._get_main_dir_path('session.json')
        if os.path.exists(session_path):
            with open(session_path, 'r') as f:
                try:
                    return json.load(f).get('user')
                except json.JSONDecodeError:
                    return None
        return None