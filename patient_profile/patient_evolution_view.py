from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, DictProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from datetime import datetime
from kivy.metrics import dp
import json
import os

from auxiliary_classes.date_checker import MONTH_NAME_TO_NUM

# Carrega o arquivo .kv associado
Builder.load_file("patient_profile/patient_evolution_view.kv", encoding='utf-8')

class PatientEvolutionView(RelativeLayout):
    """
    Visualização para o paciente registrar sua evolução de saúde.
    Corresponde ao requisito [R027].
    """
    year_list = ListProperty([])
    metric_inputs = DictProperty({})
    logged_in_patient_info = DictProperty({})

    def on_kv_post(self, base_widget):
        """Popula o seletor de ano e carrega as informações do paciente logado."""
        current_year = datetime.now().year
        self.year_list = [str(y) for y in range(current_year + 5, current_year - 20, -1)]
        # Garante que os dados do paciente sejam carregados na criação do widget.
        self.load_logged_in_patient_info()

    def on_enter(self):
        """Chamado quando a tela é exibida. Carrega os dados e preenche com a data de hoje."""
        # Garante que os dados do paciente estão sempre atualizados ao entrar na tela
        self.load_logged_in_patient_info()
        self.fill_today_date()

    def _get_main_dir_path(self, filename):
        """Constrói o caminho completo para um arquivo no diretório principal."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def load_logged_in_patient_info(self):
        """Carrega os dados do paciente logado a partir de session.json e account.json."""
        session_path = self._get_main_dir_path('session.json')
        accounts_path = self._get_main_dir_path('account.json')
        patient_user = ""

        if os.path.exists(session_path):
            try:
                with open(session_path, 'r') as f:
                    session_data = json.load(f)
                if session_data.get('logged_in') and session_data.get('profile_type') == 'patient':
                    patient_user = session_data.get('user')
            except (json.JSONDecodeError, FileNotFoundError):
                print("Erro ao carregar session.json.")

        if patient_user and os.path.exists(accounts_path):
            with open(accounts_path, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
            self.logged_in_patient_info = next((acc for acc in accounts if acc.get('user') == patient_user), {})
        
        if not self.logged_in_patient_info:
            print("Nenhum paciente logado ou dados de sessão inválidos.")

    def fill_today_date(self):
        """Preenche os seletores de data com a data atual (de app_data.json ou do sistema)."""
        # Use the system's current date directly
        date_obj = datetime.now()

        self.ids.day_input.text = str(date_obj.day)
        self.ids.year_spinner.text = str(date_obj.year)
        self.ids.month_spinner.text = list(MONTH_NAME_TO_NUM.keys())[date_obj.month - 1]
        # Força a chamada para popular os campos, pois a mudança programática
        # dos spinners pode não disparar o 'on_text' de forma confiável em todos os cenários.
        self.on_date_selected()

    def on_date_selected(self):
        """Acionado quando a data é alterada. Popula os campos de métricas para a data selecionada."""
        day = self.ids.day_input.text
        month = self.ids.month_spinner.text
        year = self.ids.year_spinner.text

        if not all([day, month != 'Mês', year != 'Ano']):
            self.ids.metrics_grid.clear_widgets()
            return

        try:
            date_obj = datetime(int(year), MONTH_NAME_TO_NUM[month], int(day))
            date_str = date_obj.strftime('%Y-%m-%d')
            self.populate_metric_fields(date_str)
        except (ValueError, KeyError):
            self.ids.metrics_grid.clear_widgets()
            print("Data inválida selecionada.")

    def populate_metric_fields(self, date_str):
        """Carrega as métricas necessárias e cria os campos de entrada, preenchendo com dados existentes."""
        metrics_grid = self.ids.metrics_grid
        metrics_grid.clear_widgets()
        self.metric_inputs = {}

        tracked_metrics = self.logged_in_patient_info.get('patient_info', {}).get('tracked_metrics', [])
        print(f"DEBUG: Métricas a serem exibidas para o paciente: {tracked_metrics}")

        if not tracked_metrics:
            metrics_grid.add_widget(Label(
                text="Nenhuma métrica de saúde foi\nconfigurada pelo seu médico.", padding=(0, dp(20)),
                color=(0,0,0,1), halign='center'
            ))
            return

        patient_id = self.logged_in_patient_info.get('id')
        evolution_data = self._get_evolution_data_for_date(patient_id, date_str)

        available_metrics_map = {
            'weight': 'Peso (kg)', 'blood_glucose': 'Glicemia (mg/dL)',
            'blood_pressure': 'Pressão Arterial (mmHg)', 'heart_rate': 'Frequência Cardíaca (bpm)',
            'temperature': 'Temperatura (°C)', 'oxygen_saturation': 'Saturação de Oxigênio (%)'
        }

        for metric_key in tracked_metrics:
            if metric_key in available_metrics_map:
                container = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
                label = Label(text=available_metrics_map[metric_key], size_hint_x=0.6, color=(0, 0, 0, 1), halign='left', font_size='12sp')
                container.add_widget(label)

                if metric_key == 'blood_pressure':
                    input_layout = BoxLayout(size_hint_x=0.4, spacing=dp(5))
                    systolic_input = TextInput(hint_text="Sist.", multiline=False, input_filter='int')
                    diastolic_input = TextInput(hint_text="Diast.", multiline=False, input_filter='int')
                    
                    bp_value = evolution_data.get(metric_key, '')
                    if '/' in bp_value:
                        systolic, diastolic = bp_value.split('/', 1)
                        systolic_input.text = systolic
                        diastolic_input.text = diastolic

                    input_layout.add_widget(systolic_input)
                    input_layout.add_widget(Label(text='/', size_hint_x=0.2, color=(0,0,0,1)))
                    input_layout.add_widget(diastolic_input)
                    
                    container.add_widget(input_layout)
                    self.metric_inputs['blood_pressure_systolic'] = systolic_input
                    self.metric_inputs['blood_pressure_diastolic'] = diastolic_input
                else:
                    text_input = TextInput(hint_text="Valor", multiline=False, size_hint_x=0.4, input_filter='float')
                    text_input.text = evolution_data.get(metric_key, '')
                    container.add_widget(text_input)
                    self.metric_inputs[metric_key] = text_input
                
                metrics_grid.add_widget(container)

    def save_evolution_data(self):
        """Salva os dados de métricas inseridos para a data selecionada."""
        day = self.ids.day_input.text
        month = self.ids.month_spinner.text
        year = self.ids.year_spinner.text

        if not all([self.logged_in_patient_info, day, month != 'Mês', year != 'Ano']):
            print("Erro: Paciente ou data não selecionados.")
            return

        try:
            date_obj = datetime(int(year), MONTH_NAME_TO_NUM[month], int(day))
            date_str = date_obj.strftime('%Y-%m-%d')
        except (ValueError, KeyError):
            print("Erro: Data inválida para salvar.")
            return

        patient_id = self.logged_in_patient_info.get('id')
        if not patient_id:
            print("Erro: ID do paciente não encontrado.")
            return

        new_data = {}
        for key, input_widget in self.metric_inputs.items():
            if key in ['blood_pressure_systolic', 'blood_pressure_diastolic']:
                continue
            if input_widget.text:
                new_data[key] = input_widget.text
        
        systolic_input = self.metric_inputs.get('blood_pressure_systolic')
        diastolic_input = self.metric_inputs.get('blood_pressure_diastolic')
        if systolic_input and diastolic_input and systolic_input.text and diastolic_input.text:
            new_data['blood_pressure'] = f"{systolic_input.text}/{diastolic_input.text}"

        all_evolutions = {}
        evolution_path = self._get_main_dir_path('patient_evolution.json')
        if os.path.exists(evolution_path):
            with open(evolution_path, 'r', encoding='utf-8') as f:
                try: all_evolutions = json.load(f)
                except json.JSONDecodeError: pass
        
        patient_evolution = all_evolutions.get(patient_id, {})
        patient_evolution[date_str] = new_data
        all_evolutions[patient_id] = patient_evolution

        with open(evolution_path, 'w', encoding='utf-8') as f:
            json.dump(all_evolutions, f, indent=4)

        print(f"Dados de evolução salvos para o paciente {patient_id} na data {date_str}.")

    def _get_evolution_data_for_date(self, patient_id, date_str):
        """Busca dados de evolução salvos para um paciente e data específicos."""
        evolution_path = self._get_main_dir_path('patient_evolution.json')
        if not patient_id or not os.path.exists(evolution_path):
            return {}
        with open(evolution_path, 'r', encoding='utf-8') as f:
            try:
                all_evolutions = json.load(f)
                return all_evolutions.get(patient_id, {}).get(date_str, {})
            except json.JSONDecodeError:
                return {}

    def enforce_text_limit(self, text_input, max_length):
        """Impõe um limite máximo de caracteres em um TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]