from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, DictProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from datetime import datetime, timedelta
from kivy.metrics import dp
import json
import os

from auxiliary_classes.date_checker import get_days_for_month, MONTH_NAME_TO_NUM

# Loads the associated kv file
Builder.load_file("doctor_profile/doctor_patient_evolution_view.kv", encoding='utf-8')

class DoctorPatientEvolutionView(RelativeLayout):
    """
    A view for the doctor to input and track a patient's health metrics over time.
    """
    current_patient_user = StringProperty("")
    year_list = ListProperty([])
    graph_metric_list = ListProperty([])
    
    # To hold references to the dynamically created input fields
    metric_inputs = DictProperty({})

    def on_current_patient_user(self, instance, value):
        """When the patient changes, reload the data for the currently selected date."""
        # If a date is already selected, this will refresh the metric fields for the new patient.
        self.on_date_selected()

    def on_kv_post(self, base_widget):
        """Populate the year spinner and set the initial date."""
        current_year = datetime.now().year
        self.year_list = [str(y) for y in range(current_year + 5, current_year - 20, -1)]
        
    def on_enter(self):
        """Called when the screen is entered. Clears the view."""
        self.clear_view()

    def fill_today_date(self):
        """
        Sets the date selectors to the current date (from app_data.json or system).
        This will also trigger on_date_selected to load the metrics.
        """
        # Use the system's current date directly
        date_obj = datetime.now()

        self.ids.day_input.text = str(date_obj.day)
        self.ids.year_spinner.text = str(date_obj.year)
        self.ids.month_spinner.text = list(MONTH_NAME_TO_NUM.keys())[date_obj.month - 1]

    def clear_view(self):
        """Resets the view to its initial state."""
        self.ids.day_input.text = ''
        self.ids.month_spinner.text = 'Mês'
        self.ids.year_spinner.text = 'Ano'
        self.ids.metrics_grid.clear_widgets()
        self.ids.metric_graph_spinner.text = 'Selecione a Métrica'
        self.graph_metric_list = []

    def on_date_selected(self):
        """
        Triggered when a date component (day, month, or year) is changed.
        It populates the metric fields for the selected date.
        """
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
        """
        Loads the required metrics for the patient and creates input fields.
        Also loads any existing data for the selected date.
        """
        metrics_grid = self.ids.metrics_grid
        metrics_grid.clear_widgets()
        self.metric_inputs = {}

        # 1. Get the patient's required metrics
        patient_info = self._get_patient_info()
        tracked_metrics = patient_info.get('patient_info', {}).get('tracked_metrics', [])
        if not tracked_metrics:
            metrics_grid.add_widget(Label(
                text="Nenhuma métrica configurada\npara este paciente.", padding=(0, dp(20)),
                color=(0,0,0,1), halign='center'
            ))
            return

        # 2. Get existing data for that date
        patient_id = patient_info.get('id')
        evolution_data = self._get_evolution_data_for_date(patient_id, date_str)

        # 3. Create the input fields
        available_metrics_map = {
            'weight': 'Peso (kg)', 'blood_glucose': 'Glicemia (mg/dL)',
            'blood_pressure': 'Pressão Arterial (mmHg)', 'heart_rate': 'Frequência Cardíaca (bpm)',
            'temperature': 'Temperatura (°C)', 'oxygen_saturation': 'Saturação de Oxigênio (%)'
        }

        # 4. Populate the graph spinner with available metrics
        self.graph_metric_list = [
            available_metrics_map[key] for key in tracked_metrics 
            if key in available_metrics_map
        ]

        for metric_key in tracked_metrics:
            if metric_key in available_metrics_map:
                container = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
                label = Label(text=available_metrics_map[metric_key], size_hint_x=0.6, color=(0, 0, 0, 1), halign='left', font_size='12sp')
                container.add_widget(label)

                # Special handling for blood pressure: split into two inputs
                if metric_key == 'blood_pressure':
                    input_layout = BoxLayout(size_hint_x=0.4, spacing=dp(5))
                    
                    systolic_input = TextInput(hint_text="Sist.", multiline=False, input_filter='int')
                    diastolic_input = TextInput(hint_text="Diast.", multiline=False, input_filter='int')
                    
                    # Pre-fill with existing data if available
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
                else: # For all other metrics
                    text_input = TextInput(hint_text="Valor", multiline=False, size_hint_x=0.4, input_filter='float', halign='right', size_hint_y=None, height=dp(32))
                    text_input.text = evolution_data.get(metric_key, '')
                    container.add_widget(text_input)
                    self.metric_inputs[metric_key] = text_input
                
                metrics_grid.add_widget(container)

    def save_evolution_data(self):
        """Saves the entered metric data for the selected patient and date."""
        day = self.ids.day_input.text
        month = self.ids.month_spinner.text
        year = self.ids.year_spinner.text

        if not all([self.current_patient_user, day, month != 'Mês', year != 'Ano']):
            print("Erro: Paciente ou data não selecionados.")
            return

        try:
            date_obj = datetime(int(year), MONTH_NAME_TO_NUM[month], int(day))
            date_str = date_obj.strftime('%Y-%m-%d')
        except (ValueError, KeyError):
            print("Erro: Data inválida para salvar.")
            return

        patient_info = self._get_patient_info()
        patient_id = patient_info.get('id')
        if not patient_id:
            print("Erro: ID do paciente não encontrado.")
            return

        # Collect data from input fields
        new_data = {}
        for key, input_widget in self.metric_inputs.items():
            # Skip the special blood pressure keys, they will be handled separately
            if key in ['blood_pressure_systolic', 'blood_pressure_diastolic']:
                continue
            if input_widget.text:
                new_data[key] = input_widget.text
        
        # Handle blood pressure separately
        systolic_input = self.metric_inputs.get('blood_pressure_systolic')
        diastolic_input = self.metric_inputs.get('blood_pressure_diastolic')
        if systolic_input and diastolic_input and systolic_input.text and diastolic_input.text:
            new_data['blood_pressure'] = f"{systolic_input.text}/{diastolic_input.text}"

        # Load, update, and save the evolution data file
        evolution_path = self._get_main_dir_path('patient_evolution.json')
        all_evolutions = {}
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
        # TODO: Show confirmation popup

    def generate_report(self, days):
        """
        Gathers data for the last N days and navigates to the report screen.
        """
        selected_metric = self.ids.metric_graph_spinner.text
        if selected_metric == 'Selecione a Métrica':
            return
        
        # Find the internal key for the selected metric description
        metric_key = None
        available_metrics_map = {
            'weight': 'Peso (kg)', 'blood_glucose': 'Glicemia (mg/dL)',
            'blood_pressure': 'Pressão Arterial (mmHg)', 'heart_rate': 'Frequência Cardíaca (bpm)',
            'temperature': 'Temperatura (°C)', 'oxygen_saturation': 'Saturação de Oxigênio (%)'
        }
        for key, value in available_metrics_map.items():
            if value == selected_metric:
                metric_key = key
                break
        
        if not metric_key: return

        # Gather data for the last 7 days from the current date
        patient_id = self._get_patient_info().get('id')
        if not patient_id: return

        data_points = []
        # Use the system's current date directly
        today = datetime.now()

        for i in range(days):
            date_to_check = today - timedelta(days=i)
            date_str = date_to_check.strftime('%Y-%m-%d')
            
            day_data = self._get_evolution_data_for_date(patient_id, date_str)
            value_str = day_data.get(metric_key)

            if value_str:
                # Handle blood pressure as a string, others as float
                if metric_key == 'blood_pressure':
                    data_points.append((date_to_check.strftime('%d/%m'), value_str))
                else:
                    try:
                        value = float(value_str)
                        data_points.append((date_to_check.strftime('%d/%m'), value))
                    except (ValueError, TypeError):
                        continue # Skip non-floatable values for other metrics

        if not data_points:
            print(f"Não há dados suficientes nos últimos {days} dias para gerar o relatório.")
            return

        graph_screen = App.get_running_app().manager.get_screen('graph_view')
        graph_screen.metric_name = selected_metric
        graph_screen.data_points = list(reversed(data_points)) # Show oldest to newest
        App.get_running_app().manager.push('graph_view')

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def _get_patient_info(self):
        """Helper to get the full info dict for the current patient."""
        accounts_path = self._get_main_dir_path('account.json')
        if not self.current_patient_user or not os.path.exists(accounts_path):
            return {}
        with open(accounts_path, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        return next((acc for acc in accounts if acc.get('user') == self.current_patient_user), {})

    def _get_evolution_data_for_date(self, patient_id, date_str):
        """Helper to get saved evolution data for a specific patient and date."""
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
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]
