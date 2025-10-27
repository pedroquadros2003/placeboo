from kivy.uix.relativelayout import RelativeLayout
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.app import App
import os
import json

# Loads the associated kv file
Builder.load_file("auxiliary_classes/change_password_view.kv", encoding='utf-8')

class ChangePasswordView(RelativeLayout):
    """
    View genérica para permitir que um usuário mude sua senha.
    """
    current_user_name = StringProperty('')

    def _get_main_dir_path(self, filename):
        """Constrói o caminho completo para um arquivo no diretório principal do projeto (PlaceboSRC)."""
        # Assumes this file is in 'auxiliary_classes' subfolder.
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    def change_password(self):
        """
        Processa a mudança de senha do usuário.
        Verifica a senha atual, valida a nova senha e atualiza o account.json.
        """
        current_password = self.ids.current_password_input.text
        new_password = self.ids.new_password_input.text
        confirm_new_password = self.ids.confirm_new_password_input.text

        if not self.current_user_name:
            App.get_running_app().show_error_popup("Erro interno: Usuário não definido.")
            return

        if not current_password or not new_password or not confirm_new_password:
            App.get_running_app().show_error_popup("Todos os campos são obrigatórios.")
            return

        if new_password != confirm_new_password:
            App.get_running_app().show_error_popup("A nova senha e a confirmação não coincidem.")
            return
        
        if len(new_password) < 6: # Basic password strength check
            App.get_running_app().show_error_popup("A nova senha deve ter no mínimo 6 caracteres.")
            return

        accounts_path = self._get_main_dir_path('account.json')
        if not os.path.exists(accounts_path):
            App.get_running_app().show_error_popup("Erro: Arquivo de contas não encontrado.")
            return

        # --- Lógica de Mensagens (executada primeiro) ---
        # Cria a mensagem para o OutboxProcessor para que a ação seja registrada.
        payload = {
            "current_password": current_password,
            "new_password": new_password
        }
        App.get_running_app().outbox_processor.add_to_outbox("account", "change_password", payload)

        # A lógica de alteração foi movida para o backend.
        # O cliente apenas envia a mensagem e aguarda uma resposta (se aplicável).
        # O feedback (sucesso/erro) agora virá do backend.
        self.clear_fields()
        App.get_running_app().manager.pop() # Go back to previous screen

    def cancel(self):
        """Cancela a operação e retorna à tela anterior."""
        self.clear_fields()
        App.get_running_app().manager.pop()

    def clear_fields(self):
        """Limpa todos os campos de entrada de senha."""
        self.ids.current_password_input.text = ''
        self.ids.new_password_input.text = ''
        self.ids.confirm_new_password_input.text = ''

# Define a screen que hospeda a view
from kivy.uix.screenmanager import Screen
class ChangePasswordScreen(Screen):
    """Tela para hospedar a ChangePasswordView."""
    current_user_name = StringProperty('') # Propriedade para passar o nome de usuário
    def on_enter(self, *args):
        # Limpa os campos ao entrar na tela para garantir um estado limpo
        self.ids.change_password_view_content.clear_fields()