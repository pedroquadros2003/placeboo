from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.label import Label
import json
import os
from datetime import datetime
from functools import partial
from kivy.uix.button import Button

# Loads the associated kv file
Builder.load_file("events_view.kv", encoding='utf-8')

class EventsView(RelativeLayout):
    """
    Events (Exams/Consultations) CRUD screen for the doctor.
    Corresponds to requirements [R016] and [R017].
    """
    events = ListProperty([])
    hour_list = ListProperty([f"{h:02d}" for h in range(24)])
    minute_list = ListProperty([f"{m:02d}" for m in range(60)])
    # This is dynamically set by DoctorHomeScreen
    current_patient_email = StringProperty("")
    editing_event_id = StringProperty(None, allownone=True)

    def on_kv_post(self, base_widget):
        """Load data when the screen is displayed."""
        self.load_events()

    def load_events(self):
        """Loads event list for the selected patient from the JSON file."""
        self.events = []
        if not self.current_patient_email or not os.path.exists('patient_events.json'):
            self.populate_events_list()
            return

        try:
            with open('patient_events.json', 'r', encoding='utf-8') as f:
                all_events = json.load(f)
            
            patient_events = all_events.get(self.current_patient_email, [])
            self.events = sorted(patient_events, key=lambda x: (x['date'], x['time'])) # Sort chronologically
            print(f"Loaded {len(self.events)} events for {self.current_patient_email}")
            self.populate_events_list()
        except (json.JSONDecodeError, FileNotFoundError):
            print("Error loading patient_events.json")
            self.events = []
            self.populate_events_list()

    def populate_events_list(self):
        """Clears and repopulates the event list widget."""
        events_list_widget = self.ids.events_list
        events_list_widget.clear_widgets()

        if not self.events:
            events_list_widget.add_widget(
                Label(text='Nenhum exame ou consulta cadastrado.', color=(0,0,0,1))
            )
            return

        for event in self.events:
            item_container = EventItem()

            # Event Name and Date (formatted)
            date_str = event.get('date', '')
            try:
                formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
            except (ValueError, TypeError):
                formatted_date = date_str # Fallback to original string if format is wrong
            name_text = f"[b]{event.get('name', 'N/A')}[/b] - {formatted_date} às {event.get('time')}"
            name_label = Label(
                text=name_text, markup=True, color=(0,0,0,1),
                halign='left', valign='middle', size_hint=(0.65, None),
                height='30dp', pos_hint={'x': 0.05, 'top': 0.95}
            )
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            item_container.add_widget(name_label)

            # Remove Button
            remove_button = Button(
                text='Remover', size_hint=(0.25, None), height='30dp',
                pos_hint={'right': 0.95, 'top': 0.95}
            )
            remove_button.bind(on_press=partial(self.remove_event, event.get('id')))
            item_container.add_widget(remove_button)

            # Edit Button
            edit_button = Button(
                text='Editar', size_hint=(0.25, None), height='30dp',
                pos_hint={'right': 0.95, 'top': 0.60}
            )
            edit_button.bind(on_press=partial(self.start_editing_event, event))
            item_container.add_widget(edit_button)

            # Description
            description_label = Label(
                text=event.get('description', ''), color=(0.3, 0.3, 0.3, 1),
                halign='left', valign='middle', font_size='12sp',
                size_hint=(0.9, None), height='40dp',
                pos_hint={'center_x': 0.5, 'y': 0.05}
            )
            description_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            item_container.add_widget(description_label)

            events_list_widget.add_widget(item_container)

    def add_event(self):
        """Adds a new event based on the inputs and updates the list."""
        name = self.ids.event_name_input.text
        date = self.ids.event_date_input.text
        hour = self.ids.event_hour_spinner.text
        minute = self.ids.event_minute_spinner.text
        description = self.ids.event_description_input.text

        if not name or not date or hour == 'Hora' or minute == 'Min':
            print("Validation Error: Name, Date, and Time are required.")
            return

        self.clear_input_fields()

        time = f"{hour}:{minute}"

        new_event = {
            "id": f"evt{int(datetime.now().timestamp())}",
            "name": name,
            "description": description,
            "date": date,
            "time": time
        }

        all_events = {}
        if os.path.exists('patient_events.json'):
            try:
                with open('patient_events.json', 'r', encoding='utf-8') as f:
                    all_events = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        patient_events = all_events.get(self.current_patient_email, [])
        patient_events.append(new_event)
        all_events[self.current_patient_email] = patient_events

        with open('patient_events.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, indent=4)

        print(f"Added event '{name}' for patient {self.current_patient_email}")
        self.load_events()

    def remove_event(self, event_id, *args):
        """Removes an event from the list and updates the JSON file."""
        event_to_remove = next((evt for evt in self.events if evt['id'] == event_id), None)
        if not event_to_remove:
            return

        self.events.remove(event_to_remove)
        self.populate_events_list()

        try:
            with open('patient_events.json', 'r+', encoding='utf-8') as f:
                all_events = json.load(f)
                all_events[self.current_patient_email] = self.events
                f.seek(0)
                json.dump(all_events, f, indent=4)
                f.truncate()
            print(f"Removed event {event_id} and updated file.")
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            print("Error updating patient_events.json")

    def start_editing_event(self, event_data, *args):
        """Populates the input fields with the data of the event to be edited."""
        self.editing_event_id = event_data.get('id')

        self.ids.event_name_input.text = event_data.get('name', '')
        self.ids.event_date_input.text = event_data.get('date', '')
        self.ids.event_description_input.text = event_data.get('description', '')

        time_str = event_data.get('time', '08:00')
        hour, minute = time_str.split(':')
        self.ids.event_hour_spinner.text = hour
        self.ids.event_minute_spinner.text = minute

    def save_event_edit(self):
        """Saves the changes to the currently edited event."""
        if not self.editing_event_id:
            return

        # --- Gather data from fields ---
        name = self.ids.event_name_input.text
        date = self.ids.event_date_input.text
        hour = self.ids.event_hour_spinner.text
        minute = self.ids.event_minute_spinner.text
        description = self.ids.event_description_input.text
        time = f"{hour}:{minute}"

        # --- Update the data in the JSON file ---
        with open('patient_events.json', 'r+', encoding='utf-8') as f:
            all_events = json.load(f)
            patient_events = all_events.get(self.current_patient_email, [])
            
            for i, event in enumerate(patient_events):
                if event['id'] == self.editing_event_id:
                    patient_events[i].update({
                        "name": name,
                        "date": date,
                        "time": time,
                        "description": description
                    })
                    break
            
            all_events[self.current_patient_email] = patient_events
            f.seek(0)
            json.dump(all_events, f, indent=4)
            f.truncate()

        print(f"Updated event {self.editing_event_id}")
        self.cancel_edit()
        self.load_events()

    def cancel_edit(self):
        """Cancels the editing process and clears the fields."""
        self.editing_event_id = None
        self.clear_input_fields()

    def clear_input_fields(self):
        """Resets all input fields to their default state."""
        self.ids.event_name_input.text = ''
        self.ids.event_date_input.text = ''
        self.ids.event_description_input.text = ''
        self.ids.event_hour_spinner.text = 'Hora'
        self.ids.event_minute_spinner.text = 'Min'

class EventItem(RelativeLayout):
    """
    A custom widget representing a single item in the event list.
    """
    pass
