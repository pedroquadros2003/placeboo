from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty, DictProperty
from kivy.uix.label import Label
import json
import os
from datetime import datetime

# Loads the associated kv file
Builder.load_file("patient_profile/patient_events_view.kv", encoding='utf-8')

class PatientEventsView(RelativeLayout):
    """Read-only view for the patient to see their events."""
    events = ListProperty([])
    logged_in_patient_info = DictProperty({})

    def on_kv_post(self, base_widget):
        """Called after the kv file is loaded. Binds properties and loads initial data."""
        self.bind(logged_in_patient_info=self.load_events)
        # Load patient info, which will then trigger loading events via the binding.
        self.load_logged_in_patient_info()

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def load_logged_in_patient_info(self):
        """Loads the logged-in patient's data from session.json and account.json."""
        session_path = self._get_main_dir_path('session.json')
        accounts_path = self._get_main_dir_path('account.json')
        patient_email = ""

        if os.path.exists(session_path):
            try:
                with open(session_path, 'r') as f:
                    session_data = json.load(f)
                if session_data.get('logged_in') and session_data.get('profile_type') == 'patient':
                    patient_email = session_data.get('email')
            except (json.JSONDecodeError, FileNotFoundError):
                print("Error loading session.json.")

        if patient_email and os.path.exists(accounts_path):
            with open(accounts_path, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
            # This property change will trigger load_events
            self.logged_in_patient_info = next((acc for acc in accounts if acc.get('email') == patient_email), {})
        
        if not self.logged_in_patient_info:
            print("No patient logged in or session data is invalid.")

    def load_events(self, *args):
        """Loads the event list for the logged-in patient from the JSON file."""
        self.events = []
        patient_email = self.logged_in_patient_info.get('email')
        if not patient_email or not os.path.exists(self._get_main_dir_path('patient_events.json')):
            self.populate_events_list()
            return

        try:
            with open(self._get_main_dir_path('patient_events.json'), 'r', encoding='utf-8') as f:
                all_events = json.load(f)
            
            patient_events = all_events.get(patient_email, [])
            self.events = sorted(patient_events, key=lambda x: (x['date'], x['time'])) # Sort chronologically
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
                Label(text='Nenhum exame ou consulta agendado.', color=(0,0,0,1))
            )
            return

        for event in self.events:
            date_str = event.get('date', '')
            try:
                formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
            except (ValueError, TypeError):
                formatted_date = date_str
            
            item_text = f"[b]{event.get('name', 'N/A')}[/b]\n"
            item_text += f"{formatted_date} às {event.get('time', '--:--')}\n"
            if event.get('description'):
                item_text += f"{event.get('description')}"

            event_label = Label(
                text=item_text,
                markup=True,
                color=(0,0,0,1),
                size_hint_y=None,
                halign='left',
                valign='top'
            )
            event_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)),
                             texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
            events_list_widget.add_widget(event_label)