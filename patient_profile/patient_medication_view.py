from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import json
import os
from datetime import datetime
from kivy.metrics import dp

# Loads the associated kv file
Builder.load_file("patient_profile/patient_medication_view.kv", encoding='utf-8')

class PatientMedicationsView(RelativeLayout):
    """
    Tela de visualização de medicações para o Paciente.
    Corresponde ao requisito [R025], exibindo apenas a lista de medicações.
    """
    medications = ListProperty([])
    logged_in_patient_email = StringProperty("") # Para armazenar o email do paciente logado

    def on_kv_post(self, base_widget):
        """Chamado após a aplicação das regras KV. Carrega o email do paciente e as medicações."""
        self.load_logged_in_patient_email()
        self.load_medications()

    def _get_main_dir_path(self, filename):
        """Constrói o caminho completo para um arquivo no diretório principal do projeto."""
        # Assume que patient_medication_view.py está em 'PlaceboSRC/patient_profile/'
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def load_logged_in_patient_email(self):
        """Carrega o email do paciente atualmente logado a partir de session.json."""
        if os.path.exists(self._get_main_dir_path('session.json')):
            try:
                with open(self._get_main_dir_path('session.json'), 'r') as f:
                    session_data = json.load(f)
                if session_data.get('logged_in') and session_data.get('profile_type') == 'patient':
                    self.logged_in_patient_email = session_data.get('email')
            except (json.JSONDecodeError, FileNotFoundError):
                print("Erro ao carregar session.json para obter o email do paciente.")
        if not self.logged_in_patient_email:
            print("Nenhum paciente logado ou dados de sessão inválidos.")

    def populate_medications_list(self):
        """Limpa e repopula o widget da lista de medicações."""
        med_list_widget = self.ids.medications_list
        med_list_widget.clear_widgets()

        if not self.medications:
            med_list_widget.add_widget(
                Label(text='Nenhuma medicação cadastrada.', color=(0,0,0,1))
            )
            return

        for med in self.medications:
            item_container = MedicationItem()

            # Nome da Medicação e Dosagem
            med_name_text = f"[b]{med.get('generic_name', 'N/A')}[/b] {med.get('dosage', '')}"
            name_label = Label(
                text=med_name_text,
                markup=True,
                color=(0,0,0,1),
                halign='left',
                valign='middle',
                size_hint=(0.95, None), # Ocupa quase toda a largura
                height='30dp',
                pos_hint={'x': 0.025, 'top': 0.95} # Pequeno padding à esquerda
            )
            name_label.bind(width=lambda s, w: s.setter('font_size')(s, 0.4 * s.height if s.texture_size[0] > w else '16sp'))
            item_container.add_widget(name_label)

            # Detalhes do Horário
            quantity = med.get('quantity', '')
            presentation = med.get('presentation', '')
            times = ', '.join(med.get('times_of_day', []))
            days = ', '.join(med.get('days_of_week', []))
            
            details_layout = BoxLayout(
                orientation='vertical',
                size_hint=(0.95, None), # Ocupa quase toda a largura
                height='50dp',
                pos_hint={'x': 0.025, 'top': 0.55}, # Posição superior ajustada para criar mais espaço
                spacing=dp(8)
            )

            schedule_text = f"Tomar {quantity} {presentation.lower()}(s) às {times} ({days})"
            schedule_label = Label(
                text=schedule_text,
                color=(0.3, 0.3, 0.3, 1),
                halign='left', valign='top', font_size='12sp'
            )
            schedule_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            details_layout.add_widget(schedule_label)

            # Observação (se existir)
            observation = med.get('observation', '')
            if observation:
                obs_label = Label(
                    text=f"Obs: {observation}",
                    color=(0.5, 0.5, 0.5, 1),
                    halign='left', valign='top', font_size='10sp'
                )
                obs_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                details_layout.add_widget(obs_label)

            item_container.add_widget(details_layout)
            med_list_widget.add_widget(item_container)

    def load_medications(self):
        """Carrega a lista de medicações para o paciente logado a partir do arquivo JSON."""
        self.medications = []
        if not self.logged_in_patient_email or not os.path.exists(self._get_main_dir_path('patient_medications.json')):
            self.populate_medications_list()
            return

        try:
            with open(self._get_main_dir_path('patient_medications.json'), 'r', encoding='utf-8') as f:
                all_meds = json.load(f)
            
            patient_meds = all_meds.get(self.logged_in_patient_email, [])
            self.medications = patient_meds
            print(f"Carregadas {len(self.medications)} medicações para {self.logged_in_patient_email}")
            self.populate_medications_list() # Popula a lista após o carregamento
        except (json.JSONDecodeError, FileNotFoundError):
            print("Erro ao carregar patient_medications.json")
            self.medications = []
            self.populate_medications_list() # Exibe mensagem vazia em caso de erro

class MedicationItem(RelativeLayout):
    """
    Um widget personalizado que representa um único item na lista de medicações.
    Sua representação visual é definida no arquivo .kv.
    """
    pass