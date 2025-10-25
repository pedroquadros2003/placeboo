from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import StringProperty, DictProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from inbox_handler.inbox_processor import InboxProcessor
from kivy.uix.label import Label
from kivy.app import App
import json
from datetime import datetime
import uuid
import os

# Loads the associated kv file
Builder.load_file("doctor_profile/patient_settings_view.kv", encoding='utf-8')

class PatientSettingsView(RelativeLayout):
    """
    A view for the doctor to configure which health metrics a patient should track.
    Corresponds to requirement [R013].
    """
    current_patient_user = StringProperty("")
    
    # List of available health metrics for tracking
    AVAILABLE_METRICS = {
        'weight': 'Peso (kg)',
        'blood_glucose': 'Glicemia (mg/dL)',
        'blood_pressure': 'Pressão Arterial (mmHg)',
        'heart_rate': 'Frequência Cardíaca (bpm)',
        'temperature': 'Temperatura (°C)',
        'oxygen_saturation': 'Saturação de Oxigênio (%)'
    }

    def _get_main_dir_path(self, filename): # Isso é para arquivos como cid10.json
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def on_current_patient_user(self, instance, value):
        """When the patient changes, load their specific settings."""
        if value:
            self.load_settings()
        else:
            self.ids.settings_grid.clear_widgets()

    def load_settings(self):
        """Loads the saved settings for the current patient and populates the checkboxes."""
        settings_grid = self.ids.settings_grid
        settings_grid.clear_widgets()

        patient_settings = self._get_patient_settings()

        for key, description in self.AVAILABLE_METRICS.items():
            container = BoxLayout(size_hint_y=None, height='48dp')
            
            checkbox = CheckBox(size_hint_x=0.2, color=(0,0,0,1))
            checkbox.active = key in patient_settings.get('tracked_metrics', [])
            checkbox.metric_key = key # Store the key in the checkbox

            label = Label(text=description, color=(0,0,0,1), halign='left', valign='middle')
            label.bind(size=label.setter('text_size'))

            container.add_widget(checkbox)
            container.add_widget(label)
            settings_grid.add_widget(container)

    def save_settings(self):
        """Saves the selected metrics for the current patient."""
        if not self.current_patient_user:
            App.get_running_app().show_error_popup("Nenhum paciente selecionado.")
            return

        # Get old settings to find out which metrics were removed
        old_settings = self._get_patient_settings() # This already returns a dict with 'id' at the top level
        patient_id = old_settings.get('id') # Get patient_id before any file modification
        old_tracked_metrics = old_settings.get('tracked_metrics', [])

        new_selected_metrics = []
        for container in self.ids.settings_grid.children:
            checkbox = container.children[1] # Checkbox is the second child added
            if checkbox.active:
                new_selected_metrics.append(checkbox.metric_key)

        # --- Save new settings to account.json ---
        accounts_path = self._get_main_dir_path('account.json')
        if not os.path.exists(accounts_path):
            return

        with open(accounts_path, 'r+', encoding='utf-8') as f:
            try:
                accounts = json.load(f)
            except json.JSONDecodeError:
                accounts = []

            # Find the patient and update their settings
            for i, acc in enumerate(accounts):
                if acc.get('user') == self.current_patient_user:
                    if 'patient_info' not in acc:
                        accounts[i]['patient_info'] = {}
                    accounts[i]['patient_info']['tracked_metrics'] = new_selected_metrics
                    break
            
            # Write the updated accounts list back to the file
            f.seek(0)
            json.dump(accounts, f, indent=4)
            f.truncate()

        # Adiciona mensagem ao inbox_messages.json para o InboxProcessor
        payload = {"patient_id": patient_id, "tracked_metrics": new_selected_metrics} # patient_id is already defined
        App.get_running_app().inbox_processor.add_to_inbox_messages("evolution", "update_tracked_metrics", payload)

        # --- Remove data for unselected metrics from patient_evolution.json ---
        metrics_to_remove = set(old_tracked_metrics) - set(new_selected_metrics)
        if metrics_to_remove and old_settings.get('id'):
            evolution_path = self._get_main_dir_path('patient_evolution.json') # patient_id is already defined
            if os.path.exists(evolution_path):
                with open(evolution_path, 'r+', encoding='utf-8') as f:
                    try:
                        all_evolutions = json.load(f)
                        patient_evolution = all_evolutions.get(patient_id, {})
                        
                        if patient_evolution:
                            # Iterate through each day's record and remove the unselected metric
                            for date_record in patient_evolution.values():
                                for metric_key in metrics_to_remove:
                                    if metric_key in date_record:
                                        del date_record[metric_key]
                            
                            all_evolutions[patient_id] = patient_evolution
                            f.seek(0)
                            json.dump(all_evolutions, f, indent=4)
                            f.truncate()
                            print(f"Removed data for metrics {list(metrics_to_remove)} for patient {patient_id}")

                    except json.JSONDecodeError:
                        pass # File is empty or corrupt

        App.get_running_app().show_success_popup(f"Configurações salvas para {self.current_patient_user}.")

    def _get_patient_settings(self):
        """Helper to safely load settings for the current patient."""
        accounts_path = self._get_main_dir_path('account.json')
        if not self.current_patient_user or not os.path.exists(accounts_path):
            return {}
        
        try:
            with open(accounts_path, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
            
            patient_account = next((acc for acc in accounts if acc.get('user') == self.current_patient_user), None)
            if patient_account:
                # Return a combined dict with patient_info and the top-level ID
                settings = patient_account.get('patient_info', {})
                settings['id'] = patient_account.get('id')
                return settings
            return {}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}