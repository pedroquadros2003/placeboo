from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.app import App
import os
from outbox_handler.outbox_processor import OutboxProcessor
from datetime import datetime
import uuid
import json

# Loads the associated kv file
Builder.load_file("doctor_profile/doctor_settings_view.kv", encoding='utf-8')

class DoctorSettingsView(RelativeLayout):
    """
    Screen for doctor-specific settings, such as logging out.
    """
    def _get_main_dir_path(self, filename):
        """Constructs the full path to a file in the main project directory."""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def logout(self):
        """
        Sends a logout request to the backend.
        """
        print("Enviando solicitação de logout...")
        App.get_running_app().outbox_processor.add_to_outbox("account", "try_logout", {})
        App.get_running_app().show_success_popup("Solicitação de logout enviada.")

    def change_password(self):
        """Navigates to the change password screen."""
        session_path = self._get_main_dir_path('session.json')
        if os.path.exists(session_path):
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            user_name = session_data.get('user')
            if user_name:
                change_password_screen = App.get_running_app().manager.get_screen('change_password')
                change_password_screen.ids.change_password_view_content.current_user_name = user_name
                App.get_running_app().manager.push('change_password')
            else:
                print("Erro: Usuário não encontrado na sessão.")
                # TODO: Show popup

    def delete_account(self):
        """
        Deletes all data associated with the current doctor's account.
        This is a destructive and irreversible action.
        """
        session_path = self._get_main_dir_path('session.json')
        # Get current doctor's user and ID from session
        if not os.path.exists(session_path): return
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        doctor_user = session_data.get('user')
        if not doctor_user: return

        # Adiciona mensagem ao outbox_messages.json ANTES de deletar os dados
        payload = {"user": doctor_user}
        App.get_running_app().outbox_processor.add_to_outbox("account", "delete_account", payload)

        # A lógica de deleção foi movida para o backend.
        # O cliente apenas envia a mensagem e faz o logout.
        # O feedback e a ação de logout agora virão do backend.
        App.get_running_app().show_success_popup("Solicitação para deletar conta enviada...")