from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
import json
import os
from datetime import datetime
from functools import partial

# Loads the associated kv file
Builder.load_file("medication_view.kv", encoding='utf-8')

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
    current_patient_email = StringProperty("")
    editing_med_id = StringProperty(None, allownone=True)

    def on_kv_post(self, base_widget):
        """Load data when the screen is displayed."""
        self.load_generic_medications()
        self._updating_checkboxes = False # Flag to prevent recursion
        self.load_medications()

    def load_generic_medications(self):
        """Loads the list of generic medications from a JSON file."""
        if os.path.exists('generic_medications.json'):
            try:
                with open('generic_medications.json', 'r', encoding='utf-8') as f:
                    self.generic_med_list = json.load(f)
                print("Loaded generic medications list.")
            except (json.JSONDecodeError, FileNotFoundError):
                print("Error loading generic_medications.json")
                self.generic_med_list = []
        else:
            print("generic_medications.json not found.")
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

            # Medication Name Label
            med_name_text = f"[b]{med.get('generic_name', 'N/A')}[/b] {med.get('dosage', '')}"
            name_label = Label(
                text=med_name_text,
                markup=True,
                color=(0,0,0,1),
                halign='left',
                valign='middle',
                size_hint=(0.65, None),
                height='30dp',
                pos_hint={'x': 0.05, 'top': 0.95}
            )
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            item_container.add_widget(name_label)

            # Remove Button
            remove_button = Button(
                text='Remover',
                size_hint=(0.25, None),
                height='30dp',
                pos_hint={'right': 0.95, 'top': 0.95}
            )
            remove_button.bind(on_press=partial(self.remove_medication, med.get('id')))
            item_container.add_widget(remove_button)

            # Edit Button
            edit_button = Button(
                text='Editar', size_hint=(0.25, None), height='30dp',
                pos_hint={'right': 0.95, 'top': 0.60}
            )
            edit_button.bind(on_press=partial(self.start_editing_medication, med))
            item_container.add_widget(edit_button)

            # Schedule details
            quantity = med.get('quantity', '')
            presentation = med.get('presentation', '')
            times = ', '.join(med.get('times_of_day', []))
            days = ', '.join(med.get('days_of_week', []))
            schedule_text = f"Tomar {quantity} {presentation.lower()}(s) às {times} ({days})"
            bottom_label = Label(
                text=schedule_text,
                color=(0.3, 0.3, 0.3, 1),
                halign='left',
                valign='middle',
                font_size='12sp',
                size_hint=(0.9, None),
                height='40dp',
                pos_hint={'center_x': 0.5, 'y': 0.05}
            )
            bottom_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            item_container.add_widget(bottom_label)

            med_list_widget.add_widget(item_container)

    def load_medications(self):
        """Loads medication list for the selected patient from the JSON file."""
        self.medications = []
        if not self.current_patient_email or not os.path.exists('patient_medications.json'):
            self.populate_medications_list()
            return

        try:
            with open('patient_medications.json', 'r', encoding='utf-8') as f:
                all_meds = json.load(f)
            
            patient_meds = all_meds.get(self.current_patient_email, [])
            self.medications = patient_meds
            print(f"Loaded {len(self.medications)} medications for {self.current_patient_email}")
            self.populate_medications_list() # Populate the list after loading
        except (json.JSONDecodeError, FileNotFoundError):
            print("Error loading patient_medications.json")
            self.medications = []
            self.populate_medications_list() # Show empty message on error

    def remove_medication(self, med_id, *args):
        """Removes a medication from the list and updates the JSON file."""
        med_to_remove = next((med for med in self.medications if med['id'] == med_id), None)
        if not med_to_remove:
            return

        self.medications.remove(med_to_remove)
        self.populate_medications_list()

        try:
            with open('patient_medications.json', 'r+', encoding='utf-8') as f:
                all_meds = json.load(f)
                all_meds[self.current_patient_email] = self.medications
                f.seek(0)
                json.dump(all_meds, f, indent=4)
                f.truncate()
            print(f"Removed medication {med_id} and updated file.")
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            print("Error updating patient_medications.json")

    def add_medication(self):
        """
        Adds a new medication based on the inputs and updates the list.
        """
        generic_name = self.ids.generic_name_spinner.text
        if not generic_name or generic_name == 'Selecione a Medicação':
            print("Validation Error: Please select a medication.")
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
        if os.path.exists('patient_medications.json'):
            try:
                with open('patient_medications.json', 'r', encoding='utf-8') as f:
                    all_meds = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        patient_meds = all_meds.get(self.current_patient_email, [])
        patient_meds.append(new_med)
        all_meds[self.current_patient_email] = patient_meds

        with open('patient_medications.json', 'w', encoding='utf-8') as f:
            json.dump(all_meds, f, indent=4)

        print(f"Added '{generic_name}' for patient {self.current_patient_email}")
        self.load_medications()

    def start_editing_medication(self, med_data, *args):
        """Populates the input fields with the data of the medication to be edited."""
        self.editing_med_id = med_data.get('id')

        self.ids.generic_name_spinner.text = med_data.get('generic_name', 'Selecione a Medicação')
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
        generic_name = self.ids.generic_name_spinner.text
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
        with open('patient_medications.json', 'r+', encoding='utf-8') as f:
            all_meds = json.load(f)
            patient_meds = all_meds.get(self.current_patient_email, [])
            
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
            
            all_meds[self.current_patient_email] = patient_meds
            f.seek(0)
            json.dump(all_meds, f, indent=4)
            f.truncate()

        print(f"Updated medication {self.editing_med_id}")
        self.cancel_edit() # Clear fields and exit edit mode
        self.load_medications() # Refresh the list

    def cancel_edit(self):
        """Cancels the editing process and clears the fields."""
        self.editing_med_id = None
        self.clear_input_fields()

    def clear_input_fields(self):
        """Resets all input fields to their default state."""
        self.ids.generic_name_spinner.text = 'Selecione a Medicação'
        self.ids.presentation_input.text = 'Apresentação'
        self.ids.dosage_input.text = ''
        self.ids.quantity_input.text = ''
        self.ids.observation_input.text = ''
        self.ids.hour_spinner.text = 'Hora'
        self.ids.minute_spinner.text = 'Min'
        self.ids.day_all.active = False
        self.toggle_all_days(False)

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

class MedicationItem(RelativeLayout):
    """
    A custom widget representing a single item in the medication list.
    Its visual representation is defined in the .kv file.
    """
    pass