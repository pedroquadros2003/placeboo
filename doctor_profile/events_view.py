from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
import json
from kivy.clock import Clock
from inbox_handler.inbox_processor import InboxProcessor
import os
from datetime import datetime
from functools import partial
from kivy.uix.button import Button
import uuid
from kivy.metrics import dp
from auxiliary_classes.date_checker import get_days_for_month, MONTH_NAME_TO_NUM

# Loads the associated kv file
Builder.load_file("doctor_profile/events_view.kv", encoding='utf-8')

class EventsView(RelativeLayout):
    """
    Events (Exams/Consultations) CRUD screen for the doctor.
    Corresponds to requirements [R016] and [R017].
    """
    events = ListProperty([])
    hour_list = ListProperty([f"{h:02d}" for h in range(24)])
    minute_list = ListProperty([f"{m:02d}" for m in range(60)])
    year_list = ListProperty([])
    # This is dynamically set by DoctorHomeScreen
    current_patient_user = StringProperty("")
    editing_event_id = StringProperty(None, allownone=True)

    def on_kv_post(self, base_widget):
        """Load data when the screen is displayed."""
        current_year = datetime.now().year
        self.year_list = [str(y) for y in range(current_year + 5, current_year - 5, -1)]
        self.load_events()

    def load_events(self):
        events_path = self._get_main_dir_path('patient_events.json')
        """Loads event list for the selected patient from the JSON file."""
        self.events = []
        if not self.current_patient_user or not os.path.exists(events_path):
            self.populate_events_list()
            return

        try:
            with open(events_path, 'r', encoding='utf-8') as f:
                all_events = json.load(f)
            
            patient_events = all_events.get(self.current_patient_user, [])
            
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
            print(f"Loaded {len(self.events)} events for {self.current_patient_user}")
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
            item_container = EventItem() # Agora herda de BoxLayout
            item_container.orientation = 'vertical'

            # --- Determine color based on event time ---
            is_past_event = False
            try:
                event_datetime_for_color = datetime.strptime(f"{event.get('date')} {event.get('time')}", '%Y-%m-%d %H:%M')
                if event_datetime_for_color < datetime.now():
                    is_past_event = True
            except (ValueError, TypeError):
                is_past_event = True # Treat invalid dates as past

            # Top part with name and buttons
            top_layout = RelativeLayout(size_hint_y=None, height=dp(65))

            # Event Name and Date
            date_str = event.get('date', '')
            time_str = event.get('time', '00:00')
            try:
                formatted_date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
                event_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
            except (ValueError, TypeError):
                formatted_date = date_str # Fallback to original string if format is wrong
                event_datetime = None
            
            name_text = f"[b]{event.get('name', 'N/A')}[/b]\n{formatted_date} às {time_str}"
            name_label = Label(
                text=name_text, markup=True, color=(0,0,0,1),
                halign='left', valign='middle',
                size_hint=(0.60, 1),
                pos_hint={'x': 0.05, 'center_y': 0.5}
            )
            name_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            top_layout.add_widget(name_label)

            # Create a vertical BoxLayout for the buttons
            button_layout = BoxLayout(
                orientation='vertical',
                size_hint=(0.25, None),
                height=dp(65), # Height for two buttons + spacing
                spacing=dp(5),
                pos_hint={'right': 0.95, 'top': 0.95}
            )
            remove_button = Button(text='Remover')
            remove_button.bind(on_press=partial(self.remove_event, event.get('id')))
            button_layout.add_widget(remove_button)
            edit_button = Button(text='Ver/Editar')
            edit_button.bind(on_press=partial(self.start_editing_event, event))
            button_layout.add_widget(edit_button)
            top_layout.add_widget(button_layout)

            item_container.add_widget(top_layout)

            # --- Time until event ---
            now = datetime.now()
            status_text = ""
            status_color = (0, 0, 0, 1) # Default black
            if event_datetime:
                if event_datetime > now:
                    delta = event_datetime - now
                    status_color = (0.1, 0.5, 0.1, 1) # Green for upcoming
                    if delta.days == 0: # Event is today
                        hours, remainder = divmod(delta.seconds, 3600)
                        minutes, _ = divmod(remainder, 60)
                        status_text = f"Faltam: {hours}h {minutes}m"
                    else: # Event is in the future
                        status_text = f"Faltam: {delta.days} dia(s)"
                else: # Event is in the past
                    status_text = "Evento já ocorreu."
                    status_color = (0.1, 0.1, 0.5, 1) # Blue for past
            
            if status_text:
                status_label = Label(
                    text=status_text, color=status_color, font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                status_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                status_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(status_label)

            # Description Label (only if description exists)
            description = event.get('description', '')
            if description:
                desc_label = Label(
                    text=f"[b]Descrição:[/b] {description}", markup=True,
                    color=(0.5, 0.5, 0.5, 1), font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                desc_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                desc_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(desc_label)

            events_list_widget.add_widget(item_container)

    def fill_today_date(self):
        """Fills the date selectors with today's date."""
        date_obj = datetime.now()
        self.ids.day_input.text = str(date_obj.day)
        self.ids.event_year_spinner.text = str(date_obj.year)
        self.ids.event_month_spinner.text = list(MONTH_NAME_TO_NUM.keys())[date_obj.month - 1]

    def add_event(self):
        """Adds a new event based on the inputs and updates the list."""
        name = self.ids.event_name_input.text
        day = self.ids.day_input.text
        month_name = self.ids.event_month_spinner.text
        year = self.ids.event_year_spinner.text
        hour = self.ids.event_hour_spinner.text
        minute = self.ids.event_minute_spinner.text
        description = self.ids.event_description_input.text

        if not name or day == 'Dia' or month_name == 'Mês' or year == 'Ano' or hour == 'Hora' or minute == 'Min':
            App.get_running_app().show_error_popup("Nome, data e hora são obrigatórios.")
            return

        # --- Date Validation ---
        try:
            num_days_in_month = get_days_for_month(year, month_name)
            day_int = int(day)
            if not (1 <= day_int <= num_days_in_month):
                raise ValueError("Dia inválido para o mês selecionado.")

            month_num = MONTH_NAME_TO_NUM[month_name]
            date_obj = datetime(int(year), month_num, day_int)
            date = date_obj.strftime('%Y-%m-%d')
        except (ValueError, KeyError):
            App.get_running_app().show_error_popup("A data selecionada é inválida.")
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
        events_path = self._get_main_dir_path('patient_events.json')
        if os.path.exists(events_path):
            try:
                with open(events_path, 'r', encoding='utf-8') as f:
                    all_events = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        patient_events = all_events.get(self.current_patient_user, [])
        patient_events.append(new_event)
        all_events[self.current_patient_user] = patient_events

        with open(events_path, 'w', encoding='utf-8') as f:
            json.dump(all_events, f, indent=4)

        App.get_running_app().show_success_popup(f"Evento '{name}' adicionado.")
        # Adiciona mensagem ao inbox_messages.json
        payload = new_event.copy()
        payload['patient_user'] = self.current_patient_user # Adiciona patient_user ao payload para a mensagem
        App.get_running_app().inbox_processor.add_to_inbox_messages("event", "add_event", payload)
        self.load_events()

    def remove_event(self, event_id, *args):
        """Removes an event from the list and updates the JSON file."""
        event_to_remove = next((evt for evt in self.events if evt['id'] == event_id), None)
        if not event_to_remove:
            return

        self.events.remove(event_to_remove)
        self.populate_events_list()

        events_path = self._get_main_dir_path('patient_events.json')
        try:
            with open(events_path, 'r+', encoding='utf-8') as f:
                all_events = json.load(f)
                all_events[self.current_patient_user] = self.events
                f.seek(0)
                json.dump(all_events, f, indent=4)
                f.truncate()
            print(f"Removed event {event_id} and updated file.")
        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            print("Error updating patient_events.json")

        # Adiciona mensagem ao inbox_messages.json
        payload = {"event_id": event_id, "patient_user": self.current_patient_user}
        App.get_running_app().inbox_processor.add_to_inbox_messages("event", "delete_event", payload)
        

    def start_editing_event(self, event_data, *args):
        """Populates the input fields with the data of the event to be edited."""
        self.editing_event_id = event_data.get('id')

        self.ids.event_name_input.text = event_data.get('name', '')
        
        date_str = event_data.get('date', '')
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            self.ids.event_year_spinner.text = str(date_obj.year)
            self.ids.event_month_spinner.text = list(MONTH_NAME_TO_NUM.keys())[date_obj.month - 1]
            self.ids.day_input.text = str(date_obj.day)

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
        day = self.ids.day_input.text
        month_name = self.ids.event_month_spinner.text
        year = self.ids.event_year_spinner.text
        hour = self.ids.event_hour_spinner.text
        minute = self.ids.event_minute_spinner.text
        description = self.ids.event_description_input.text

        # --- Date Validation ---
        try:
            num_days_in_month = get_days_for_month(year, month_name)
            day_int = int(day)
            if not (1 <= day_int <= num_days_in_month):
                raise ValueError("Dia inválido para o mês selecionado.")

            month_num = MONTH_NAME_TO_NUM[month_name]
            date_obj = datetime(int(year), month_num, day_int)
            date = date_obj.strftime('%Y-%m-%d')
        except (ValueError, KeyError):
            App.get_running_app().show_error_popup("A data selecionada é inválida.")
            return
        time = f"{hour}:{minute}"

        # --- Update the data in the JSON file ---
        events_path = self._get_main_dir_path('patient_events.json')
        with open(events_path, 'r+', encoding='utf-8') as f:
            all_events = json.load(f)
            patient_events = all_events.get(self.current_patient_user, [])
            
            for i, event in enumerate(patient_events):
                if event['id'] == self.editing_event_id:
                    patient_events[i].update({
                        "name": name,
                        "id": self.editing_event_id,
                        "date": date,
                        "time": time,
                        "description": description
                    })
                    # Prepara o payload para a inbox ANTES de sair do loop
                    payload_for_message = patient_events[i].copy()
                    payload_for_message['patient_user'] = self.current_patient_user
                    break
            
            # Adiciona mensagem ao inbox_messages.json
            if 'payload_for_message' in locals():
                payload = payload_for_message
                App.get_running_app().inbox_processor.add_to_inbox_messages("event", "edit_event", payload)

            all_events[self.current_patient_user] = patient_events
            f.seek(0)
            json.dump(all_events, f, indent=4)
            f.truncate()

        App.get_running_app().show_success_popup(f"Evento atualizado.")
        self.cancel_edit()
        self.load_events()

    def cancel_edit(self):
        """Cancels the editing process and clears the fields."""
        self.editing_event_id = None
        self.clear_input_fields()

    def clear_input_fields(self):
        """Resets all input fields to their default state."""
        self.ids.event_name_input.text = ''
        self.ids.event_year_spinner.text = 'Ano'
        self.ids.event_month_spinner.text = 'Mês'
        self.ids.day_input.text = ''
        self.ids.event_description_input.text = ''
        self.ids.event_hour_spinner.text = 'Hora'
        self.ids.event_minute_spinner.text = 'Min'

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]

    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

class EventItem(BoxLayout):
    """
    A custom widget representing a single item in the event list.
    """
    pass
