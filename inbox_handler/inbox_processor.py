import json
import os
from typing import Dict, Any
from kivy.app import App
from kivy.clock import mainthread
from inbox_handler.message_decoder import MessageDecoder

class InboxProcessor:
    """
    Processa mensagens da 'inbox' (vindas do backend) e atualiza o estado do cliente.
    """

    # Dicionário de tradução para mensagens de sucesso de 'comeback'
    ACTION_TRANSLATIONS = {
        "add_diagnostic": "Diagnóstico adicionado",
        "delete_diagnostic": "Diagnóstico removido",
        "edit_diagnostic": "Diagnóstico editado",
        "update_tracked_metrics": "Métricas rastreadas atualizadas",
        "fill_metric": "Dados de evolução salvos",
        "add_event": "Evento adicionado",
        "delete_event": "Evento removido",
        "edit_event": "Evento editado",
        "delete_account": "Conta deletada",
        "change_password": "Senha alterada",
        "invite_patient": "Convite enviado",
        "respond_to_invitation": "Resposta ao convite processada",
        "unlink_accounts": "Conta desvinculada",
        "add_med": "Medicação adicionada",
        "delete_med": "Medicação removida",
        "edit_med": "Medicação editada"
    }

    def __init__(self, base_path: str):
        '''
        Inicializa o processador de inbox.

        Args:
            base_path: O caminho raiz do projeto.
        '''
        
        self.base_path = base_path
        self.inbox_path = os.path.join(self.base_path, 'inbox_handler', 'inbox_messages.json')
        self.decoder = MessageDecoder()

    def _read_json(self, file_path, default_value=None):
        if default_value is None: default_value = []
        if not os.path.exists(file_path): return default_value
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError): return default_value

    def _write_json(self, file_path, data):
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

    def process_inbox(self):
        """Lê o inbox, processa novas mensagens e as remove do arquivo."""
        # Identifica se há uma tentativa de login em andamento para filtrar mensagens
        app = App.get_running_app()
        session_user = app.outbox_processor._get_origin_user_id()
        
        inbox_messages = self._read_json(self.inbox_path) # Lê apenas o inbox
        remaining_messages = []

        for msg in inbox_messages:
            msg_target_user = msg.get("origin_user_id")
            payload = msg.get("payload", {})

            # Condição para processar:
            # 1. A mensagem é para o usuário logado.
            # 2. OU é uma resposta a uma requisição de login/criação de conta pendente.
            is_for_session_user = (session_user and msg_target_user == session_user) # Usuário já logado
            is_login_response = (not session_user and app.pending_request_id and 
                                 payload.get("request_message_id") == app.pending_request_id) # Resposta a uma requisição pendente
            should_process = is_for_session_user or is_login_response
            
            if should_process:
                print(f"[Inbox] Processando nova mensagem: {msg.get('object')}/{msg.get('action')}")
                
                # 1. Decodificar a mensagem
                decoded_message = self.decoder.decode(msg)
                
                # 2. Roteá-la se a decodificação for bem-sucedida
                if decoded_message:
                    self._route_message(decoded_message)
            else:
                # Se a mensagem não for para o usuário atual, ela permanece na caixa de entrada
                remaining_messages.append(msg)
        
        self._write_json(self.inbox_path, remaining_messages)

    def _route_message(self, message: Dict[str, Any]):
        """Direciona a mensagem para o handler apropriado."""
        obj = message.get('object') # Já validado pelo decoder
        action = message.get('action') # Já validado pelo decoder
        payload = message.get('payload', {}) # Já validado pelo decoder

        handler_method_name = f"_handle_{obj}_{action}"
        handler_method = getattr(self, handler_method_name, self._handle_unknown)
        
        print(f"[InboxProcessor] Mensagem entendida. Roteando para o método: {handler_method_name}")

        # Se for uma mensagem de 'comeback', usa o handler genérico.
        if action.endswith('_cback'):
            self._handle_comeback(action, payload)
        else:
            # Executa o método handler correspondente à mensagem.
            handler_method(payload)

    def _handle_unknown(self, payload: Dict[str, Any]):
        print(f"[Inbox] Ação desconhecida ou não implementada no cliente.")

    def _handle_comeback(self, action: str, payload: Dict[str, Any]):
        """Handler genérico para todas as mensagens de 'comeback'."""
        app = App.get_running_app()
        request_id = payload.get("request_message_id")

        if payload.get("executed"):
            # Transforma 'add_diagnostic_cback' em 'Diagnóstico adicionado'
            action_base_name = action.replace('_cback', '')
            translated_message = self.ACTION_TRANSLATIONS.get(action_base_name, f"{action_base_name.replace('_', ' ').capitalize()} (sucesso)")
            app.show_success_popup(f"{translated_message}!")
        else:
            reason = payload.get("reason", "A operação falhou.")
            app.show_error_popup(f"Erro: {reason}")
        
        # Se a resposta for para a requisição pendente atual, limpa o ID.
        if app.pending_request_id == request_id:
            app.pending_request_id = None

    def _handle_account_success_login(self, payload: Dict[str, Any]):
        """Cria a sessão local e redireciona o usuário após o backend confirmar o login."""
        user_data = payload.get('user_data')
        if not user_data: return

        session_path = os.path.join(self.base_path, 'session.json')
        session_data = {'logged_in': True, 'user': user_data['user'], 'profile_type': user_data['profile_type']}
        self._write_json(session_path, session_data)

        print(f"[Inbox] Login bem-sucedido para {user_data['user']}. Redirecionando...")
        manager = App.get_running_app().manager
        if user_data['profile_type'] == 'doctor': manager.reset_to('doctor_home')
        else: manager.reset_to('patient_home')
        App.get_running_app().pending_request_id = None # Limpa o ID da requisição pendente

    def _handle_account_fail_login(self, payload: Dict[str, Any]):
        """Exibe um popup de erro quando o backend informa falha no login."""
        reason = payload.get("reason", "Falha no login.")
        print(f"[Inbox] Falha no login: {reason}")
        App.get_running_app().show_error_popup(reason)
        App.get_running_app().pending_request_id = None # Limpa o ID da requisição pendente