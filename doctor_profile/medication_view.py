from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ListProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.app import App
from kivy.clock import Clock
import json
import os
from datetime import datetime
from functools import partial
from kivy.metrics import dp

# Loads the associated kv file
Builder.load_file("doctor_profile/medication_view.kv", encoding='utf-8')

class MedicationsView(RelativeLayout):
    """
    Medications CRUD screen for the doctor.
    Corresponds to requirements [R014] and [R015].
    """
    medications = ListProperty([])
    generic_med_list = ListProperty([])
    hour_list = ListProperty([f"{h:02d}" for h in range(24)])
    minute_list = ListProperty([f"{m:02d}" for m in range(60)])
    # This is dynamically set by DoctorHomeScreen
    current_patient_user = StringProperty("")
    editing_med_id = StringProperty(None, allownone=True)

    def on_kv_post(self, base_widget):
        """Load data when the screen is displayed."""
        self.load_generic_medications()
        self._is_selecting_med = False # Flag to control search feedback loop
        self._updating_checkboxes = False # Flag to prevent recursion
        # The on_text event is now handled directly in the .kv file
        self.load_medications()
    
    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def load_generic_medications(self):
        """Loads the list of generic medications from a JSON file."""
        if os.path.exists(self._get_main_dir_path('generic_medications.json')):
            try:
                with open('generic_medications.json', 'r', encoding='utf-8') as f:
                    self.generic_med_list = json.load(f)
                print("Loaded generic medications list.")
            except (json.JSONDecodeError, FileNotFoundError):
                App.get_running_app().show_error_popup("Erro ao carregar lista de medicações.")
                self.generic_med_list = []
        else:
            App.get_running_app().show_error_popup("Arquivo de medicações não encontrado.")
            self.generic_med_list = []

    def populate_medications_list(self):
        """Clears and repopulates the medication list widget."""
        med_list_widget = self.ids.medications_list
        med_list_widget.clear_widgets()

        if not self.medications:
            med_list_widget.add_widget(
                Label(text='Nenhuma medicação cadastrada.', color=(0,0,0,1))
            )
            return

        for med in self.medications:
            item_container = MedicationItem()
            item_container.orientation = 'vertical' # Usaremos um BoxLayout para empilhar os widgets

            # --- Determine color based on next dose status ---
            now = datetime.now()
            weekday_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'}
            today_weekday_str = weekday_map[now.weekday()]
            days = ', '.join(med.get('days_of_week', []))
            is_for_today = "Todos os dias" in days or today_weekday_str in days
            
            color_status = 'neutral' # neutral, upcoming, taken
            if is_for_today:
                dose_times_today = sorted([datetime.strptime(t, '%H:%M').time() for t in med.get('times_of_day', [])])
                has_upcoming_dose = any(now.replace(hour=t.hour, minute=t.minute) > now for t in dose_times_today)
                if has_upcoming_dose:
                    color_status = 'upcoming'
                else:
                    color_status = 'taken'

            # Top part with name and buttons
            top_layout = RelativeLayout(size_hint_y=None, height=dp(65))

            name_label = Label(
                text=f"[b]{med.get('generic_name', 'N/A')}[/b] {med.get('dosage', '')}",
                markup=True,
                color=(0,0,0,1),
                halign='left',
                valign='middle',
                size_hint=(0.60, 1), # Ocupa a altura do pai
                pos_hint={'x': 0.05, 'center_y': 0.5} # Centraliza verticalmente
            )
            # Garante que o texto quebre a linha se for muito longo
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            top_layout.add_widget(name_label)

            # Button Layout
            button_layout = BoxLayout(
                orientation='vertical',
                size_hint=(0.25, None),
                height=dp(65),
                spacing=dp(5),
                pos_hint={'right': 0.95, 'top': 0.95}
            )
            remove_button = Button(text='Remover')
            remove_button.bind(on_press=partial(self.remove_medication, med.get('id')))
            button_layout.add_widget(remove_button)

            edit_button = Button(text='Ver/Editar')
            edit_button.bind(on_press=partial(self.start_editing_medication, med))
            button_layout.add_widget(edit_button)
            top_layout.add_widget(button_layout)

            item_container.add_widget(top_layout)

            # Schedule details
            quantity = med.get('quantity', '')
            presentation = med.get('presentation', '')
            times = ', '.join(med.get('times_of_day', []))
            days = ', '.join(med.get('days_of_week', []))
            observation = med.get('observation', '')
            
            # Schedule Label
            schedule_text = f"Tomar {quantity} {presentation.lower()}(s) às {times} ({days})"
            schedule_label = Label(
                text=schedule_text,
                color=(0.3, 0.3, 0.3, 1),
                halign='left', valign='top', font_size='12sp',
                size_hint_y=None, padding=(dp(10), dp(5))
            )
            schedule_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            schedule_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
            item_container.add_widget(schedule_label)

            # --- Time until next dose ---
            now = datetime.now()
            weekday_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sab', 6: 'Dom'}
            today_weekday_str = weekday_map[now.weekday()]
            
            is_for_today = "Todos os dias" in days or today_weekday_str in days
            
            next_dose_status = ""
            if is_for_today:
                dose_times_today = sorted([datetime.strptime(t, '%H:%M').time() for t in med.get('times_of_day', [])])
                
                next_dose_time = None
                for dose_time in dose_times_today:
                    dose_datetime = now.replace(hour=dose_time.hour, minute=dose_time.minute, second=0, microsecond=0)
                    if dose_datetime > now:
                        next_dose_time = dose_datetime
                        break
                
                if next_dose_time:
                    delta = next_dose_time - now
                    hours, remainder = divmod(delta.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    next_dose_status = f"Próxima dose em: {hours}h {minutes}m"
                    status_color = (0.1, 0.5, 0.1, 1) # Green for upcoming
                else:
                    next_dose_status = "Doses de hoje já foram tomadas."
                    status_color = (0.1, 0.1, 0.5, 1) # Blue for taken

            if next_dose_status:
                status_label = Label(
                    text=next_dose_status, color=status_color, font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                status_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                status_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(status_label)

            # Observation Label (only if observation exists)
            if observation:
                obs_label = Label(
                    text=f"[b]Obs:[/b] {observation}", markup=True,
                    color=(0.5, 0.5, 0.5, 1), font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                obs_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                obs_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(obs_label)

            med_list_widget.add_widget(item_container)

    def load_medications(self):
        """Loads medication list for the selected patient from the JSON file."""
        self.medications = []
        medications_path = self._get_main_dir_path('patient_medications.json')
        if not self.current_patient_user or not os.path.exists(medications_path):
            self.populate_medications_list()
            return

        try:
            with open(medications_path, 'r', encoding='utf-8') as f:
                all_meds = json.load(f)
            
            patient_meds = all_meds.get(self.current_patient_user, [])
            self.medications = patient_meds
            print(f"Loaded {len(self.medications)} medications for {self.current_patient_user}")
            self.populate_medications_list() # Populate the list after loading
        except (json.JSONDecodeError, FileNotFoundError):
            App.get_running_app().show_error_popup("Erro ao carregar medicações do paciente.")
            self.medications = []
            self.populate_medications_list() # Show empty message on error

    def remove_medication(self, med_id, *args):
        """Removes a medication from the list and updates the JSON file."""
        med_to_remove = next((med for med in self.medications if med['id'] == med_id), None)
        if not med_to_remove:
            return

        self.medications.remove(med_to_remove)
        self.populate_medications_list()

        medications_path = self._get_main_dir_path('patient_medications.json')
        try:
            with open(medications_path, 'r+', encoding='utf-8') as f:
                all_meds = json.load(f)
                all_meds[self.current_patient_user] = self.medications
                f.seek(0)
                json.dump(all_meds, f, indent=4)
                f.truncate()
            print(f"Removed medication {med_id} and updated file.")
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            App.get_running_app().show_error_popup("Erro ao salvar alterações.")

    def add_medication(self):
        """
        Adds a new medication based on the inputs and updates the list.
        """
        generic_name = self.ids.generic_name_input.text
        if not generic_name or generic_name == 'Busque a Medicação (ex: Paracetamol)':
            App.get_running_app().show_error_popup("Por favor, selecione uma medicação.")
            return
        
        # Validate if the medication exists in the generic list
        if generic_name not in self.generic_med_list:
            App.get_running_app().show_error_popup(f"'{generic_name}' não é uma medicação válida.")
            return

        presentation = self.ids.presentation_input.text
        dosage = self.ids.dosage_input.text
        quantity = self.ids.quantity_input.text
        hour = self.ids.hour_spinner.text
        minute = self.ids.minute_spinner.text
        observation = self.ids.observation_input.text

        days_of_week = []
        day_ids = ['day_seg', 'day_ter', 'day_qua', 'day_qui', 'day_sex', 'day_sab', 'day_dom']
        for day_key in day_ids:
            if self.ids[day_key].active:
                day_name = day_key.split('_')[1].capitalize()
                days_of_week.append(day_name)

        if len(days_of_week) == 7:
            days_of_week = ["Todos os dias"]

        # Clear inputs after adding
        self.clear_input_fields()


        time_selected = "08:00" # Default time
        if hour != 'Hora' and minute != 'Min':
            time_selected = f"{hour}:{minute}"


        new_med = {
            "id": f"med{int(datetime.now().timestamp())}",
            "generic_name": generic_name,
            "presentation": presentation if presentation != 'Apresentação' else 'Comprimido',
            "dosage": dosage,
            "quantity": quantity,
            "days_of_week": days_of_week if days_of_week else ["Todos os dias"],
            "times_of_day": [time_selected],
            "start_date": datetime.now().strftime('%Y-%m-%d'),
            "end_date": "",
            "observation": observation
        }

        all_meds = {}
        medications_path = self._get_main_dir_path('patient_medications.json')
        if os.path.exists(medications_path):
            try:
                with open(medications_path, 'r', encoding='utf-8') as f:
                    all_meds = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        patient_meds = all_meds.get(self.current_patient_user, [])
        patient_meds.append(new_med)
        all_meds[self.current_patient_user] = patient_meds

        with open(medications_path, 'w', encoding='utf-8') as f:
            json.dump(all_meds, f, indent=4)

        App.get_running_app().show_success_popup(f"Medicação '{generic_name}' adicionada.")
        self.load_medications()

    def start_editing_medication(self, med_data, *args):
        """Populates the input fields with the data of the medication to be edited."""
        self.editing_med_id = med_data.get('id')

        self.ids.generic_name_input.text = med_data.get('generic_name', '')
        self.ids.presentation_input.text = med_data.get('presentation', 'Apresentação')
        self.ids.dosage_input.text = med_data.get('dosage', '')
        self.ids.quantity_input.text = med_data.get('quantity', '')
        self.ids.observation_input.text = med_data.get('observation', '')

        # Set time spinners
        time_str = med_data.get('times_of_day', ['08:00'])[0]
        hour, minute = time_str.split(':')
        self.ids.hour_spinner.text = hour
        self.ids.minute_spinner.text = minute

        # Set day checkboxes
        days = med_data.get('days_of_week', [])
        day_ids = ['day_seg', 'day_ter', 'day_qua', 'day_qui', 'day_sex', 'day_sab', 'day_dom']
        if "Todos os dias" in days:
            for day_id in day_ids: self.ids[day_id].active = True
        else:
            for day_id in day_ids:
                day_name = day_id.split('_')[1].capitalize()
                self.ids[day_id].active = day_name in days
        self.update_select_all_status()

    def save_medication_edit(self):
        """Saves the changes to the currently edited medication."""
        if not self.editing_med_id:
            return

        # --- Gather data from fields ---
        generic_name = self.ids.generic_name_input.text
        # Validate if the medication exists in the generic list
        if generic_name not in self.generic_med_list:
            App.get_running_app().show_error_popup(f"'{generic_name}' não é uma medicação válida.")
            return

        presentation = self.ids.presentation_input.text
        dosage = self.ids.dosage_input.text
        quantity = self.ids.quantity_input.text
        hour = self.ids.hour_spinner.text
        minute = self.ids.minute_spinner.text
        observation = self.ids.observation_input.text
        
        days_of_week = []
        day_ids = ['day_seg', 'day_ter', 'day_qua', 'day_qui', 'day_sex', 'day_sab', 'day_dom']
        for day_key in day_ids:
            if self.ids[day_key].active:
                days_of_week.append(day_key.split('_')[1].capitalize())
        if len(days_of_week) == 7:
            days_of_week = ["Todos os dias"]

        time_selected = f"{hour}:{minute}"

        # --- Update the data in the JSON file ---
        medications_path = self._get_main_dir_path('patient_medications.json')
        all_meds = {}
        with open(medications_path, 'r+', encoding='utf-8') as f:
            all_meds = json.load(f)
            patient_meds = all_meds.get(self.current_patient_user, [])
            
            for i, med in enumerate(patient_meds):
                if med['id'] == self.editing_med_id:
                    patient_meds[i].update({
                        "generic_name": generic_name,
                        "presentation": presentation,
                        "dosage": dosage,
                        "quantity": quantity,
                        "days_of_week": days_of_week,
                        "times_of_day": [time_selected],
                        "observation": observation
                    })
                    break
            
            all_meds[self.current_patient_user] = patient_meds
            f.seek(0)
            json.dump(all_meds, f, indent=4)
            f.truncate()

        App.get_running_app().show_success_popup(f"Medicação atualizada.")
        self.cancel_edit() # Clear fields and exit edit mode
        self.load_medications() # Refresh the list

    def cancel_edit(self):
        """Cancels the editing process and clears the fields."""
        self.editing_med_id = None
        self.clear_input_fields()

    def clear_input_fields(self):
        """Resets all input fields to their default state."""
        self.ids.generic_name_input.text = ''
        self.ids.presentation_input.text = 'Apresentação'
        self.ids.dosage_input.text = ''
        self.ids.quantity_input.text = ''
        self.ids.observation_input.text = ''
        self.ids.hour_spinner.text = 'Hora'
        self.ids.minute_spinner.text = 'Min'
        self.ids.day_all.active = False
        self.toggle_all_days(False)
        # Hide search results
        self.ids.med_search_results_scroll.height = 0
        self.ids.med_search_results.clear_widgets()

    def toggle_all_days(self, active_state):
        """
        Sets the state of all individual day checkboxes based on the 'All' checkbox.
        """
        if self._updating_checkboxes:
            return

        self._updating_checkboxes = True
        day_ids = ['day_seg', 'day_ter', 'day_qua', 'day_qui', 'day_sex', 'day_sab', 'day_dom']
        for day_id in day_ids:
            if day_id in self.ids:
                self.ids[day_id].active = active_state
        self._updating_checkboxes = False

    def update_select_all_status(self):
        """
        Checks if all individual day checkboxes are active and updates the 'All' checkbox.
        """
        if self._updating_checkboxes:
            return

        day_ids = ['day_seg', 'day_ter', 'day_qua', 'day_qui', 'day_sex', 'day_sab', 'day_dom']
        all_checked = all(self.ids[day_id].active for day_id in day_ids if day_id in self.ids)

        self._updating_checkboxes = True
        if 'day_all' in self.ids:
            self.ids.day_all.active = all_checked
        self._updating_checkboxes = False

    def filter_generic_medications(self, search_text):
        """Filters the generic medication list based on user input."""
        if self._is_selecting_med: # Ignore text changes made by the app itself
            return

        results_grid = self.ids.med_search_results
        results_scroll = self.ids.med_search_results_scroll
        results_grid.clear_widgets()

        if not search_text:
            results_scroll.height = 0
            return

        # Case-insensitive search
        search_text_lower = search_text.lower()
        matches = [med for med in self.generic_med_list if med.lower().startswith(search_text_lower)]

        if not matches:
            results_scroll.height = 0
            return

        for med_name in matches: # Show all results
            btn = Button(
                text=med_name,
                size_hint=(0.5, None), # Button takes 50% of the container width
                height=dp(40),
                background_color=(0.85, 0.85, 0.85, 1), # Fundo cinza padrão
                color=(0, 0, 0, 1), # Texto preto
                halign='left', # Alinha o texto à esquerda
                padding=[dp(12), 0] # Adiciona padding horizontal
            )
            # Garante que o texto quebre a linha se for muito longo
            btn.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            btn.bind(on_press=partial(self.select_generic_medication, med_name))

            # Create a container to center the button
            container = RelativeLayout(
                size_hint_y=None,
                height=dp(40)
            )
            # Center the button inside the container
            btn.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
            container.add_widget(btn)

            results_grid.add_widget(container)

        results_scroll.height = len(matches) * dp(40) # The height calculation remains the same

    def select_generic_medication(self, med_name, *args):
        """Called when a medication is selected from the search results."""
        print(f"DEBUG: Botão '{med_name}' clicado. A função select_generic_medication foi chamada.")
        self._is_selecting_med = True  # Set flag to prevent filter from running

        # Set the text. The handler will see the flag and do nothing.
        self.ids.generic_name_input.text = med_name

        # Use Clock.schedule_once to reset the flag on the next frame.
        # This ensures the text update event is fully processed before the flag is reset.
        # We also hide the results and restore focus here to ensure a clean state.
        Clock.schedule_once(self.reset_selection_flag)

    def reset_selection_flag(self, *args):
        """
        Resets the selection flag, hides search results, and restores focus to the input.
        This is called on the next frame to avoid event conflicts.
        """
        self.ids.med_search_results_scroll.height = 0 # Hide results
        self.ids.med_search_results.clear_widgets() # Clear the old buttons
        self._is_selecting_med = False
        self.ids.generic_name_input.focus = True # Explicitly restore focus

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]

    def prevent_newlines(self, text_input):
        """Removes newline characters from a TextInput's text."""
        if '\n' in text_input.text:
            text_input.text = text_input.text.replace('\n', '')

class MedicationItem(BoxLayout):
    """
    A custom widget representing a single item in the medication list.
    Its visual representation is defined in the .kv file.
    """
    pass