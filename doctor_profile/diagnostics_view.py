from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.app import App
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.metrics import dp
import json
import os
from datetime import datetime, timezone
from outbox_handler.outbox_processor import OutboxProcessor
from functools import partial
import uuid

# Loads the associated kv file
Builder.load_file("doctor_profile/diagnostics_view.kv", encoding='utf-8')

class DiagnosticsView(RelativeLayout):
    """
    Diagnostics CRUD screen for the doctor.
    Corresponds to requirement [R018].
    """
    diagnostics = ListProperty([])
    cid10_list = ListProperty([])
    current_patient_user = StringProperty("")
    editing_diagnostic_id = StringProperty(None, allownone=True)

    def on_kv_post(self, base_widget):
        """Load data when the screen is displayed."""
        self.load_cid10_data()
        self._is_selecting_cid = False # Flag to control search feedback loop

    def on_current_patient_user(self, instance, value):
        """Updates the view when the patient changes."""
        if value:
            self.load_diagnostics()
        else:
            # Clear content if no patient is selected
            self.ids.diagnostics_list.clear_widgets()

    def load_cid10_data(self):
        """Loads the CID-10 codes and names from a JSON file."""
        cid10_path = self._get_main_dir_path('cid10.json')
        """Loads the CID-10 codes and names from a JSON file."""
        if os.path.exists(cid10_path):
            try:
                with open(cid10_path, 'r', encoding='utf-8') as f:
                    self.cid10_list = json.load(f)
                print("Loaded CID-10 list.")
            except (json.JSONDecodeError, FileNotFoundError):
                App.get_running_app().show_error_popup("Erro ao carregar dados de diagnóstico.")

    def load_diagnostics(self):
        """Loads diagnostics for the current patient."""
        diagnostics_path = self._get_main_dir_path('patient_diagnostics.json')
        self.diagnostics = []
        if not self.current_patient_user or not os.path.exists(diagnostics_path):
            self.populate_diagnostics_list()
            return

        try:
            with open(diagnostics_path, 'r', encoding='utf-8') as f:
                all_diagnostics = json.load(f)
            
            patient_diagnostics = all_diagnostics.get(self.current_patient_user, [])
            # Sort by 'date_added' if it exists, otherwise no specific order
            self.diagnostics = sorted(patient_diagnostics, key=lambda x: x.get('date_added', ''), reverse=True)
            print(f"Loaded {len(self.diagnostics)} diagnostics for {self.current_patient_user}")
            self.populate_diagnostics_list()
        except (json.JSONDecodeError, FileNotFoundError):
            App.get_running_app().show_error_popup("Erro ao carregar diagnósticos do paciente.")
            self.diagnostics = []
            self.populate_diagnostics_list()

    def populate_diagnostics_list(self):
        """Clears and repopulates the diagnostic list widget."""
        diagnostics_list_widget = self.ids.diagnostics_list
        diagnostics_list_widget.clear_widgets()

        if not self.diagnostics:
            diagnostics_list_widget.add_widget(
                Label(text='Nenhum diagnóstico cadastrado.', color=(0,0,0,1))
            )
            return

        for diagnostic in self.diagnostics:
            item_container = DiagnosticItem() # Agora herda de BoxLayout
            item_container.orientation = 'vertical' # Para empilhar os widgets

            # Top part with name and buttons
            top_layout = RelativeLayout(size_hint_y=None, height=dp(65))

            # Name and CID-10 Label
            name_text = f"[b]{diagnostic.get('name', 'N/A')}[/b]"
            if diagnostic.get('cid_code'):
                name_text += f"\n(CID-10: {diagnostic.get('cid_code')})"
            name_label = Label(
                text=name_text, markup=True, color=(0,0,0,1),
                halign='left', valign='middle',
                size_hint=(0.60, 1), # Ocupa a altura do pai
                pos_hint={'x': 0.05, 'center_y': 0.5} # Centraliza verticalmente
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
            remove_button.bind(on_press=partial(self.remove_diagnostic, diagnostic.get('id')))
            button_layout.add_widget(remove_button)

            edit_button = Button(text='Ver/Editar')
            edit_button.bind(on_press=partial(self.start_editing_diagnostic, diagnostic))
            button_layout.add_widget(edit_button)

            top_layout.add_widget(button_layout)
            item_container.add_widget(top_layout)

            # Description Label (only if description exists)
            description = diagnostic.get('description', '')
            if description:
                desc_label = Label(
                    text=f"[b]Descrição:[/b] {description}", markup=True,
                    color=(0.5, 0.5, 0.5, 1), font_size='11sp',
                    halign='left', valign='top', size_hint_y=None, padding=(dp(10), dp(5))
                )
                desc_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
                desc_label.bind(texture_size=lambda s, ts: s.setter('height')(s, ts[1]))
                item_container.add_widget(desc_label)

            diagnostics_list_widget.add_widget(item_container)

    def add_diagnostic(self):
        """Adds a new diagnostic and saves it."""
        cid_code = self.ids.diagnostic_cid_input.text
        name = self.ids.diagnostic_name_input.text
        description = self.ids.diagnostic_description_input.text

        if not name:
            App.get_running_app().show_error_popup("O nome da condição é obrigatório.")
            return

        new_diagnostic = {
            "id": f"diag{int(datetime.now().timestamp())}",
            "cid_code": cid_code,
            "name": name,
            "description": description,
            "date_added": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        self.clear_input_fields()
        self.load_diagnostics()
        
        # Adiciona mensagem ao outbox_messages.json
        payload = new_diagnostic.copy()
        payload['patient_user'] = self.current_patient_user # Adiciona patient_user ao payload para o payload da mensagem
        App.get_running_app().outbox_processor.add_to_outbox("diagnostic", "add_diagnostic", payload)

    def remove_diagnostic(self, diagnostic_id, *args):
        """Removes a diagnostic."""
        # A remoção local é otimista. A fonte da verdade será o backend.
        self.diagnostics = [d for d in self.diagnostics if d['id'] != diagnostic_id]
        # self._save_to_file(None, is_new=False) # Lógica de escrita removida
        self.populate_diagnostics_list()
        
        # Adiciona mensagem ao outbox_messages.json
        payload = {"diagnostic_id": diagnostic_id, "patient_user": self.current_patient_user}
        App.get_running_app().outbox_processor.add_to_outbox("diagnostic", "delete_diagnostic", payload)

    def start_editing_diagnostic(self, diagnostic_data, *args):
        """Populates input fields to start editing."""
        self.editing_diagnostic_id = diagnostic_data.get('id')
        self.ids.diagnostic_cid_input.text = diagnostic_data.get('cid_code', '')
        self.ids.diagnostic_name_input.text = diagnostic_data.get('name', '')
        self.ids.diagnostic_description_input.text = diagnostic_data.get('description', '')

    def save_diagnostic_edit(self):
        """Saves changes to an existing diagnostic."""
        if not self.editing_diagnostic_id:
            return

        for i, diag in enumerate(self.diagnostics):
            if diag['id'] == self.editing_diagnostic_id:
                self.diagnostics[i] = {
                    "id": self.editing_diagnostic_id,
                    "cid_code": self.ids.diagnostic_cid_input.text,
                    "name": self.ids.diagnostic_name_input.text,
                    "description": self.ids.diagnostic_description_input.text,
                    "date_added": diag.get('date_added') # Preserve original date
                }
                break
        
        # Adiciona mensagem ao outbox_messages.json
        payload = self.diagnostics[i].copy() # Usa o diagnóstico atualizado
        payload['patient_user'] = self.current_patient_user
        App.get_running_app().outbox_processor.add_to_outbox("diagnostic", "edit_diagnostic", payload)
        App.get_running_app().show_success_popup("Solicitação de edição de diagnóstico enviada.")
        
        self.cancel_edit()
        
    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def cancel_edit(self):
        """Cancels editing and clears fields."""
        self.editing_diagnostic_id = None
        self.clear_input_fields()

    def clear_input_fields(self):
        """Resets all input fields."""
        self.ids.diagnostic_cid_input.text = ''
        self.ids.diagnostic_name_input.text = ''
        self.ids.diagnostic_description_input.text = ''

    def filter_cid_codes(self, search_text):
        """Filters the CID-10 list based on user input on code or name."""
        if self._is_selecting_cid:
            return

        results_grid = self.ids.cid_search_results
        results_scroll = self.ids.cid_search_results_scroll
        results_grid.clear_widgets()

        if not search_text:
            results_scroll.height = 0
            return

        search_text_lower = search_text.lower()
        matches = [
            item for item in self.cid10_list 
            if search_text_lower in item['code'].lower() or search_text_lower in item['name'].lower()
        ]

        if not matches:
            results_scroll.height = 0
            return

        for item in matches:
            display_text = f"{item['code']} - {item['name']}"
            btn = Button(
                text=display_text,
                size_hint=(0.75, None),
                height=dp(40),
                background_color=(0.85, 0.85, 0.85, 1), # Fundo escuro
                color=(1, 1, 1, 1), # Texto branco
                halign='left',
                padding=[dp(12), 0],
                font_size='12sp'
            )
            # Bind the button's width to its text_size to enable text wrapping
            btn.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
            btn.bind(on_press=partial(self.select_cid_code, item))
 
            container = RelativeLayout(size_hint_y=None, height=dp(40))
            btn.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
            container.add_widget(btn)
            results_grid.add_widget(container)

        results_scroll.height = len(matches) * dp(40)

    def select_cid_code(self, cid_item, *args):
        """Called when a CID code is selected from the search results."""
        self._is_selecting_cid = True

        self.ids.diagnostic_cid_input.text = cid_item['code']
        self.ids.diagnostic_name_input.text = cid_item['name']

        Clock.schedule_once(self.reset_selection_flag)

    def reset_selection_flag(self, *args):
        """Resets the selection flag and hides search results."""
        self.ids.cid_search_results_scroll.height = 0
        self.ids.cid_search_results.clear_widgets()
        self._is_selecting_cid = False
        self.ids.diagnostic_cid_input.focus = True

    def enforce_text_limit(self, text_input, max_length):
        """Enforces a maximum character limit on a TextInput."""
        if len(text_input.text) > max_length:
            text_input.text = text_input.text[:max_length]


class DiagnosticItem(BoxLayout):
    """
    A custom widget representing a single item in the diagnostic list.
    """
    pass