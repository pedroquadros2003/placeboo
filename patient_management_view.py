from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, DictProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from functools import partial
import json
import os

# Loads the associated kv file
Builder.load_file("patient_management_view.kv", encoding='utf-8')

class PatientManagementView(RelativeLayout):
    """
    Screen for the doctor to manage their linked patients (CRUD).
    """
    patient_list = ListProperty([])
    patient_map = DictProperty({}) # To map patient names to emails

    def on_enter(self):
        """Called when the screen is entered. Loads the list of linked patients."""
        self.load_linked_patients()

    def load_linked_patients(self):
        """Loads the doctor's linked patients to populate the list."""
        doctor_email = self._get_doctor_email()
        if not doctor_email:
            self.patient_list = []
            self.patient_map = {}
            self.populate_patient_list()
            return

        if not os.path.exists('account.json'):
            self.patient_list = []
            self.populate_patient_list()
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
        
        self.patient_list = patient_names
        self.populate_patient_list()

    def populate_patient_list(self):
        """Clears and repopulates the patient list widget."""
        patient_list_widget = self.ids.patient_list
        patient_list_widget.clear_widgets()

        if not self.patient_list:
            patient_list_widget.add_widget(Label(text='Nenhum paciente vinculado.', color=(0,0,0,1)))
            return

        for name in self.patient_list:
            item_container = RelativeLayout(size_hint_y=None, height='48dp')
            
            name_label = Label(
                text=f'[b]{name}[/b]', markup=True, color=(0,0,0,1),
                halign='left', valign='middle', size_hint=(0.6, 1),
                pos_hint={'x': 0.05, 'center_y': 0.5}
            )
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            item_container.add_widget(name_label)
            
            remove_button = Button(text='Remover', size_hint=(None, None), size=('100dp', '38dp'), pos_hint={'right': 0.98, 'center_y': 0.5})
            remove_button.bind(on_press=partial(self.remove_patient, name))
            item_container.add_widget(remove_button)

            patient_list_widget.add_widget(item_container)

    def add_patient(self):
        """Links a new patient to the doctor using a 6-digit code."""
        code = self.ids.patient_code_input.text
        if not code or len(code) != 8:
            print("Validation Error: Por favor, insira um código de 8 dígitos.")
            # TODO: Show popup
            return

        doctor_email = self._get_doctor_email()
        if not doctor_email or not os.path.exists('account.json'):
            return

        with open('account.json', 'r+', encoding='utf-8') as f:
            accounts = json.load(f)
            
            # Find patient by code
            patient_account = next((acc for acc in accounts if acc.get('id') == code and acc.get('profile_type') == 'patient'), None)
            if not patient_account:
                print(f"Erro: Paciente com código {code} não encontrado.")
                return

            patient_id = patient_account['id']

            # Find doctor and update linked_patients
            doctor_id = None
            for i, acc in enumerate(accounts):
                if acc['email'] == doctor_email:
                    doctor_id = acc.get('id')
                    if 'linked_patients' not in acc:
                        accounts[i]['linked_patients'] = []
                    
                    if patient_id in accounts[i]['linked_patients']:
                        print(f"Info: Paciente {patient_id} já está vinculado.")
                        self.ids.patient_code_input.text = ''
                        return

                    accounts[i]['linked_patients'].append(patient_id)
                    break
            
            if not doctor_id: return

            # Find patient and update responsible_doctors
            for i, acc in enumerate(accounts):
                if acc.get('id') == patient_id:
                    if 'patient_info' not in acc: accounts[i]['patient_info'] = {}
                    if 'responsible_doctors' not in acc['patient_info']: accounts[i]['patient_info']['responsible_doctors'] = []
                    
                    if doctor_id not in accounts[i]['patient_info']['responsible_doctors']:
                        accounts[i]['patient_info']['responsible_doctors'].append(doctor_id)
                    break

            # Save changes back to file
            f.seek(0)
            json.dump(accounts, f, indent=4)
            f.truncate()

        print(f"Paciente {patient_id} vinculado com sucesso ao doutor {doctor_id}.")
        self.ids.patient_code_input.text = ''
        self.load_linked_patients()

    def remove_patient(self, patient_name, *args):
        """Unlinks a patient from the doctor."""
        patient_email = self.patient_map.get(patient_name)
        doctor_email = self._get_doctor_email()
        if not doctor_email or not os.path.exists('account.json'):
            return

        with open('account.json', 'r+', encoding='utf-8') as f:
            accounts = json.load(f)
            for i, acc in enumerate(accounts):
                # Find doctor
                if acc['email'] == doctor_email:
                    doctor_id = acc.get('id')
                    patient_account = next((p_acc for p_acc in accounts if p_acc.get('email') == patient_email), None)
                    if not patient_account: return
                    patient_id = patient_account.get('id')

                    # Remove patient from doctor's list
                    if 'linked_patients' in acc and patient_id in acc['linked_patients']:
                        accounts[i]['linked_patients'].remove(patient_id)

                    # Remove doctor from patient's list
                    for j, p_acc_inner in enumerate(accounts):
                        if p_acc_inner.get('id') == patient_id:
                            if 'responsible_doctors' in p_acc_inner.get('patient_info', {}) and doctor_id in p_acc_inner['patient_info']['responsible_doctors']:
                                accounts[j]['patient_info']['responsible_doctors'].remove(doctor_id)
                            break
                    
                    f.seek(0)
                    json.dump(accounts, f, indent=4)
                    f.truncate()
                    print(f"Paciente {patient_id} desvinculado.")
                    self.load_linked_patients()
                    break

    def _get_doctor_email(self):
        """Helper to get the current doctor's email from the session file."""
        if os.path.exists('session.json'):
            with open('session.json', 'r') as f:
                return json.load(f).get('email')
        return None

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]