from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import json
import os
from datetime import datetime
from kivy.metrics import dp
from kivy.app import App


# Loads the associated kv file
Builder.load_file("patient_profile/patient_medication_view.kv", encoding='utf-8')

class PatientMedicationsView(RelativeLayout):
    """
    Tela de visualização de medicações para o Paciente.
    Corresponde ao requisito [R025], exibindo apenas a lista de medicações.
    """
    medications = ListProperty([])
    logged_in_patient_user = StringProperty("") # Para armazenar o usuário do paciente logado

    def on_kv_post(self, base_widget):
        """Chamado após a aplicação das regras KV. Carrega o usuário do paciente e as medicações."""
        self.load_logged_in_patient_user()
        self.load_medications()

    def _get_main_dir_path(self, filename):
        """Constrói o caminho completo para um arquivo no diretório principal do projeto."""
        # Assume que patient_medication_view.py está em 'PlaceboSRC/patient_profile/'
        return os.path.join(App.get_running_app().get_user_data_path(), filename)

    def load_logged_in_patient_user(self):
        """Carrega o usuário do paciente atualmente logado a partir de session.json."""
        if os.path.exists(self._get_main_dir_path('session.json')):
            try:
                with open(self._get_main_dir_path('session.json'), 'r') as f:
                    session_data = json.load(f)
                if session_data.get('logged_in') and session_data.get('profile_type') == 'patient':
                    self.logged_in_patient_user = session_data.get('user')
            except (json.JSONDecodeError, FileNotFoundError):
                print("Erro ao carregar session.json para obter o usuário do paciente.")
        if not self.logged_in_patient_user:
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

        now = datetime.now()
        weekday_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'}
        today_weekday_str = weekday_map[now.weekday()]

        for med in self.medications:
            item_container = MedicationItem() # Agora herda de BoxLayout
            item_container.orientation = 'vertical'

            # --- Nome da Medicação e Dosagem ---
            name_label = Label(
                text=f"[b]{med.get('generic_name', 'N/A')}[/b] {med.get('dosage', '')}",
                markup=True, color=(0,0,0,1), halign='left', valign='top',
                size_hint_y=None, padding=(dp(10), dp(10))
            )
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            name_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
            item_container.add_widget(name_label)

            # --- Detalhes do Horário ---
            quantity = med.get('quantity', '')
            presentation = med.get('presentation', '')
            times = ', '.join(med.get('times_of_day', []))
            days = ', '.join(med.get('days_of_week', []))

            schedule_text = f"Tomar {quantity} {presentation.lower()}(s) às {times} ({days})"
            schedule_label = Label(
                text=schedule_text, color=(0.3, 0.3, 0.3, 1),
                halign='left', valign='top', font_size='12sp',
                size_hint_y=None, padding=(dp(10), dp(5))
            )
            schedule_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            schedule_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
            item_container.add_widget(schedule_label)

            # --- Status da Próxima Dose ---
            is_for_today = "Todos os dias" in days or today_weekday_str in days
            next_dose_status = ""
            if is_for_today:
                dose_times_today = sorted([datetime.strptime(t, '%H:%M').time() for t in med.get('times_of_day', [])])
                next_dose_time = next((t for t in dose_times_today if now.replace(hour=t.hour, minute=t.minute) > now), None)
                
                if next_dose_time:
                    delta = now.replace(hour=next_dose_time.hour, minute=next_dose_time.minute) - now
                    hours, remainder = divmod(delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    next_dose_status = f"Próxima dose em: {hours}h {minutes}m"
                    status_color = (0.1, 0.5, 0.1, 1) # Verde
                else:
                    next_dose_status = "Doses de hoje já foram tomadas."
                    status_color = (0.1, 0.1, 0.5, 1) # Azul

                status_label = Label(
                    text=next_dose_status, color=status_color, font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                status_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                status_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(status_label)

            # --- Observação (se existir) ---
            observation = med.get('observation', '')
            if observation:
                obs_label = Label(
                    text=f"[b]Obs:[/b] {observation}", markup=True, color=(0.5, 0.5, 0.5, 1),
                    halign='left', valign='top', font_size='11sp',
                    size_hint_y=None, padding=(dp(10), dp(5))
                )
                obs_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                obs_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(obs_label)

            med_list_widget.add_widget(item_container)

    def load_medications(self):
        """Carrega a lista de medicações para o paciente logado a partir do arquivo JSON."""
        self.medications = []
        if not self.logged_in_patient_user or not os.path.exists(self._get_main_dir_path('patient_medications.json')):
            self.populate_medications_list()
            return

        try:
            with open(self._get_main_dir_path('patient_medications.json'), 'r', encoding='utf-8') as f:
                all_meds = json.load(f)
            
            patient_meds = all_meds.get(self.logged_in_patient_user, [])
            self.medications = patient_meds
            print(f"Carregadas {len(self.medications)} medicações para {self.logged_in_patient_user}")
            self.populate_medications_list() # Popula a lista após o carregamento
        except (json.JSONDecodeError, FileNotFoundError):
            print("Erro ao carregar patient_medications.json")
            self.medications = []
            self.populate_medications_list() # Exibe mensagem vazia em caso de erro

class MedicationItem(BoxLayout):
    """
    Um widget personalizado que representa um único item na lista de medicações.
    Sua representação visual é definida no arquivo .kv.
    """
    pass