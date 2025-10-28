from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.app import App
import os
import json

# O arquivo KV é carregado em patient_screens.py
# Builder.load_file("patient_profile/patient_settings_view.kv", encoding='utf-8')

class PatientAppSettingsView(RelativeLayout):
    """
    View para as configurações do aplicativo do paciente, como logout e deleção de conta.
    """
    def _get_main_dir_path(self, filename):
        """Constrói o caminho completo para um arquivo no diretório principal do projeto."""
        return os.path.join(App.get_running_app().get_user_data_path(), filename)

    def logout(self):
        """
        Faz o logout do usuário deletando o arquivo de sessão e retornando para a tela inicial.
        """
        print("Fazendo logout...")
        session_path = self._get_main_dir_path('session.json')
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
                print("Arquivo de sessão deletado.")
            except OSError as e:
                print(f"Erro ao deletar arquivo de sessão: {e}")
        
        App.get_running_app().manager.reset_to('initial_access')

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
        Deleta todos os dados associados à conta do paciente atual.
        Esta é uma ação destrutiva e irreversível.
        """
        # Obter usuário e ID do paciente da sessão
        session_path = self._get_main_dir_path('session.json')
        if not os.path.exists(session_path): return
        with open(session_path, 'r') as f:
            session_data = json.load(f)
        patient_user = session_data.get('user')
        if not patient_user: return

        # Adiciona mensagem ao outbox_messages.json ANTES de deletar os dados locais.
        # O payload pode ser expandido para incluir confirmação de senha se a UI for atualizada.
        payload = {"user": patient_user}
        App.get_running_app().outbox_processor.add_to_outbox("account", "delete_account", payload)

        # A lógica de deleção foi movida para o backend.
        # O cliente apenas envia a mensagem e aguarda a resposta do backend.
        App.get_running_app().show_success_popup("Solicitação para deletar conta enviada...")