from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty, DictProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
import json
import os
from datetime import datetime
from kivy.metrics import dp

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
        patient_user = ""

        if os.path.exists(session_path):
            try:
                with open(session_path, 'r') as f:
                    session_data = json.load(f)
                if session_data.get('logged_in') and session_data.get('profile_type') == 'patient':
                    patient_user = session_data.get('user')
            except (json.JSONDecodeError, FileNotFoundError):
                print("Error loading session.json.")

        if patient_user and os.path.exists(accounts_path):
            with open(accounts_path, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
            # This property change will trigger load_events
            self.logged_in_patient_info = next((acc for acc in accounts if acc.get('user') == patient_user), {})
        
        if not self.logged_in_patient_info:
            print("No patient logged in or session data is invalid.")

    def load_events(self, *args):
        """Loads the event list for the logged-in patient from the JSON file."""
        self.events = []
        patient_user = self.logged_in_patient_info.get('user')
        if not patient_user or not os.path.exists(self._get_main_dir_path('patient_events.json')):
            self.populate_events_list()
            return

        try:
            with open(self._get_main_dir_path('patient_events.json'), 'r', encoding='utf-8') as f:
                all_events = json.load(f)
            
            patient_events = all_events.get(patient_user, [])
            
            # Separate past and future events
            now = datetime.now()
            future_events = []
            past_events = []
            for event in patient_events:
                try:
                    event_datetime = datetime.strptime(f"{event.get('date')} {event.get('time')}", '%Y-%m-%d %H:%M')
                    (future_events if event_datetime > now else past_events).append(event)
                except (ValueError, TypeError):
                    past_events.append(event) # Treat events with bad dates as past
            
            self.events = sorted(future_events, key=lambda x: (x['date'], x['time'])) + sorted(past_events, key=lambda x: (x['date'], x['time']), reverse=True)
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
                Label(text='Nenhum exame ou consulta cadastrado.', color=(0,0,0,1), halign='center')
            )
            return

        for event in self.events:
            item_container = EventItem()
            item_container.orientation = 'vertical'

            # --- Nome do Evento e Data ---
            date_str = event.get('date', '')
            time_str = event.get('time', '00:00')
            try:
                formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
                event_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                formatted_date = date_str
                event_datetime = None
            
            item_text = f"[b]{event.get('name', 'N/A')}[/b]\n"
            item_text += f"{formatted_date} às {time_str}"

            event_label = Label(
                text=item_text, markup=True, color=(0,0,0,1),
                halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(10))
            )
            event_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)),
                             texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
            item_container.add_widget(event_label) # Correctly add to the container

            # --- Status do Evento ---
            now = datetime.now()
            status_text = ""
            if event_datetime:
                if event_datetime > now:
                    delta = event_datetime - now
                    status_color = (0.1, 0.5, 0.1, 1) # Verde
                    if delta.days == 0:
                        hours, remainder = divmod(delta.seconds, 3600)
                        minutes, _ = divmod(remainder, 60)
                        status_text = f"Faltam: {hours}h {minutes}m"
                    else:
                        status_text = f"Faltam: {delta.days} dia(s)"
                else:
                    status_text = "Evento já ocorreu."
                    status_color = (0.1, 0.1, 0.5, 1) # Azul

                status_label = Label(
                    text=status_text, color=status_color, font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                status_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                status_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(status_label) # Correctly add to the container

            # --- Descrição (se existir) ---
            description = event.get('description')
            if description:
                desc_label = Label(
                    text=f"[b]Descrição:[/b] {description}", markup=True, color=(0.5, 0.5, 0.5, 1),
                    halign='left', valign='top', font_size='11sp',
                    size_hint_y=None, padding=(dp(10), dp(5))
                )
                desc_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                desc_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(desc_label) # Correctly add to the container

            events_list_widget.add_widget(item_container)

class EventItem(BoxLayout):
    """Custom widget for an event item, allowing dynamic height."""
    pass