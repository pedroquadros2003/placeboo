from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.app import App
from functools import partial
import json
import os
from kivy.metrics import dp

Builder.load_file("patient_profile/manage_doctors_view.kv")

class ManageDoctorsView(RelativeLayout):
    """
    View for the patient to manage invitations and linked doctors.
    """
    invitations_data = ListProperty([])
    linked_doctors_data = ListProperty([])

    def on_enter(self):
        self.load_data()

    def _get_main_dir_path(self, filename):
        return os.path.join(App.get_running_app().get_user_data_path(), filename)

    def load_data(self):
        """Loads both pending invitations and linked doctors for the logged-in patient."""
        self.invitations_data = []
        self.linked_doctors_data = []
        accounts_path = self._get_main_dir_path('account.json')
        session_path = self._get_main_dir_path('session.json')

        if not os.path.exists(session_path) or not os.path.exists(accounts_path):
            self.populate_lists()
            return

        with open(session_path, 'r') as f:
            patient_user = json.load(f).get('user')
        
        with open(accounts_path, 'r') as f:
            accounts = json.load(f)

        patient_account = next((acc for acc in accounts if acc.get('user') == patient_user), None)
        if not patient_account:
            self.populate_lists()
            return

        # Load Invitations
        inviting_doctor_ids = patient_account.get('invitations', [])
        temp_invitations = []
        for doc_id in inviting_doctor_ids:
            doctor_account = next((acc for acc in accounts if acc.get('id') == doc_id), None)
            if doctor_account:
                temp_invitations.append({'id': doc_id, 'name': doctor_account.get('name', 'Médico Desconhecido')})
        self.invitations_data = temp_invitations

        # Load Linked Doctors
        responsible_doctor_ids = patient_account.get('patient_info', {}).get('responsible_doctors', [])
        temp_linked_doctors = []
        for doc_id in responsible_doctor_ids:
            doctor_account = next((acc for acc in accounts if acc.get('id') == doc_id), None)
            if doctor_account:
                temp_linked_doctors.append({'id': doc_id, 'name': doctor_account.get('name', 'Médico Desconhecido')})
        self.linked_doctors_data = temp_linked_doctors

        self.populate_lists()

    def populate_lists(self):
        """Clears and repopulates both the invitations and linked doctors lists."""
        # Populate Invitations
        invitations_list_widget = self.ids.invitations_list
        invitations_list_widget.clear_widgets()
        if not self.invitations_data:
            invitations_list_widget.add_widget(Label(text='Nenhum convite pendente.', color=(0,0,0,1)))
        else:
            for invitation in self.invitations_data:
                item_container = RelativeLayout(size_hint_y=None, height='48dp')
                name_label = Label(text=f'[b]{invitation["name"]}[/b]', markup=True, color=(0,0,0,1), halign='left', valign='middle', size_hint=(0.5, 1), pos_hint={'x': 0.05, 'center_y': 0.5})
                name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                item_container.add_widget(name_label)

                # Use a BoxLayout for the buttons to handle spacing
                button_layout = BoxLayout(size_hint=(None, None), size=('190dp', '38dp'), pos_hint={'right': 0.98, 'center_y': 0.5}, spacing=dp(10))
                
                reject_button = Button(text='Recusar')
                reject_button.bind(on_press=partial(self.handle_invitation, invitation['id'], 'reject'))
                button_layout.add_widget(reject_button)

                accept_button = Button(text='Aceitar')
                accept_button.bind(on_press=partial(self.handle_invitation, invitation['id'], 'accept'))
                button_layout.add_widget(accept_button)

                item_container.add_widget(button_layout)
                invitations_list_widget.add_widget(item_container)

        # Populate Linked Doctors
        linked_doctors_list_widget = self.ids.linked_doctors_list
        linked_doctors_list_widget.clear_widgets()
        if not self.linked_doctors_data:
            linked_doctors_list_widget.add_widget(Label(text='Nenhum médico vinculado.', color=(0,0,0,1)))
        else:
            for doctor in self.linked_doctors_data:
                item_container = RelativeLayout(size_hint_y=None, height='48dp')
                name_label = Label(text=f'[b]{doctor["name"]}[/b]', markup=True, color=(0,0,0,1), halign='left', valign='middle', size_hint=(0.6, 1), pos_hint={'x': 0.05, 'center_y': 0.5})
                name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                item_container.add_widget(name_label)
                remove_button = Button(text='Remover', size_hint=(None, None), size=('100dp', '38dp'), pos_hint={'right': 0.98, 'center_y': 0.5})
                remove_button.bind(on_press=partial(self.remove_doctor, doctor['id']))
                item_container.add_widget(remove_button)
                linked_doctors_list_widget.add_widget(item_container)

    def handle_invitation(self, doctor_id, action, *args):
        """Accepts or rejects an invitation."""
        # A lógica de escrita foi movida para o backend.
        # A view apenas envia a mensagem e atualiza a UI otimisticamente.
        payload = {"doctor_id": doctor_id, "response": action}
        App.get_running_app().outbox_processor.add_to_outbox("linking_accounts", "respond_to_invitation", payload)
        App.get_running_app().show_success_popup(f"Convite {'aceito' if action == 'accept' else 'recusado'}.")
        self.load_data() # Atualização otimista da UI

    def remove_doctor(self, doctor_id, *args):
        """Unlinks a doctor from the patient."""
        # A lógica de escrita foi movida para o backend.
        payload = {"target_user_id": doctor_id} # O alvo da desvinculação é o médico
        App.get_running_app().outbox_processor.add_to_outbox("linking_accounts", "unlink_accounts", payload)
        App.get_running_app().show_success_popup("Solicitação para desvincular médico enviada.")
        self.load_data() # Atualização otimista da UI

class ManageDoctorsScreen(Screen):
    """Screen to host the ManageDoctorsView."""
    def on_enter(self, *args):
        # Chama o método on_enter da view filha para carregar os dados
        self.children[0].children[0].on_enter()