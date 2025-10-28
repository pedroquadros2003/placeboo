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
        self.processed_inbox_ids_path = os.path.join(self.base_path, 'inbox_handler', 'processed_inbox_ids.json')
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
        
        # "Lembre-se" do ID da requisição pendente no início do ciclo
        current_pending_request_id = app.pending_request_id
        print(f"\n[DEBUG Inbox] --- Starting cycle --- Session User: {session_user}, Pending Request ID: {current_pending_request_id}")

        inbox_messages = self._read_json(self.inbox_path) # Lê apenas o inbox
        remaining_messages = []
        processed_ids_this_cycle = set()
        processed_ids_history = set(self._read_json(self.processed_inbox_ids_path))

        for msg in inbox_messages:
            msg_target_user = msg.get("origin_user_id")
            msg_id = msg.get("message_id")
            payload = msg.get("payload", {})
            print(f"[DEBUG Inbox] Evaluating message: {msg.get('action')} for user {msg_target_user}")

            # Condição para processar:
            # 1. A mensagem é para o usuário logado.
            # 2. OU é uma resposta a uma requisição de login/criação de conta pendente.
            is_for_session_user = (session_user and msg_target_user == session_user) # Usuário já logado
            is_login_response = (not session_user and current_pending_request_id and
                                 payload.get("request_message_id") == current_pending_request_id) # Resposta a uma requisição pendente
            should_process = is_for_session_user or is_login_response
            print(f"[DEBUG Inbox] -> is_for_session_user: {is_for_session_user}, is_login_response: {is_login_response} ==> Should Process: {should_process}")
            
            if should_process and msg_id not in processed_ids_history:
                print(f"[Inbox] Processando nova mensagem: {msg.get('object')}/{msg.get('action')}")
                
                # 1. Decodificar a mensagem
                decoded_message = self.decoder.decode(msg)
                
                # 2. Roteá-la se a decodificação for bem-sucedida
                if decoded_message:
                    self._route_message(decoded_message)
                
                processed_ids_this_cycle.add(msg_id)
            else:
                # Se a mensagem não for para o usuário atual, ela permanece na caixa de entrada
                remaining_messages.append(msg)
        
        # Atualiza o histórico de IDs processados e limpa o inbox
        if processed_ids_this_cycle:
            updated_history = processed_ids_history.union(processed_ids_this_cycle)
            self._write_json(self.processed_inbox_ids_path, list(updated_history))
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
        if action.endswith('_cback') and action != 'try_login_cback':
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
            
            # Casos especiais de 'comeback'
            if action == "delete_account_cback":
                self._force_logout()
            elif action == "create_account_cback":
                app.show_success_popup("Conta criada com sucesso! Faça o login.")
                app.manager.reset_to('login')
            else:
                app.show_success_popup(f"{translated_message}!")
        else:
            reason = payload.get("reason", "A operação falhou.")
            app.show_error_popup(f"Erro: {reason}")

    def _force_logout(self):
        """Força o logout do cliente, limpando a sessão."""
        print("[Inbox] Forçando logout após ação bem-sucedida (ex: delete_account).")
        session_path = os.path.join(self.base_path, 'session.json')
        if os.path.exists(session_path):
            try:
                os.remove(session_path)
                print("[Inbox] Arquivo de sessão deletado.")
            except OSError as e:
                print(f"[Inbox] Erro ao deletar arquivo de sessão: {e}")
        
        App.get_running_app().manager.reset_to('initial_access')

    def _handle_account_try_login_cback(self, payload: Dict[str, Any]):
        """Processa a resposta de uma tentativa de login ou criação de conta."""
        app = App.get_running_app()
        
        if payload.get("executed"):
            # Sucesso: cria a sessão e redireciona
            user_data = payload.get('user_data')
            if not user_data: return

            session_path = os.path.join(self.base_path, 'session.json')
            session_data = {'logged_in': True, 'user': user_data['user'], 'profile_type': user_data['profile_type']}
            self._write_json(session_path, session_data)

            print(f"[Inbox] Login/Criação bem-sucedido para {user_data['user']}. Redirecionando...")
            manager = app.manager
            if user_data['profile_type'] == 'doctor': manager.reset_to('doctor_home')
            else: manager.reset_to('patient_home')
        else:
            # Falha: exibe o popup de erro
            reason = payload.get("reason", "A operação falhou.")
            print(f"[Inbox] Falha no login/criação: {reason}")
            app.show_error_popup(reason)

        # Limpa o ID da requisição pendente em ambos os casos (sucesso ou falha)
        # Esta é a única fonte da verdade para limpar o ID após login/criação.
        if app.pending_request_id == payload.get("request_message_id"):
            print(f"[DEBUG Inbox] Clearing pending_request_id after login/create response: {app.pending_request_id}")
            app.pending_request_id = None
    def _handle_outbox_delete_from_outbox(self, payload: Dict[str, Any]):
        """Remove uma mensagem específica do outbox do cliente."""
        msg_id_to_delete = payload.get("message_id_to_delete")
        if not msg_id_to_delete: return

        outbox_path = os.path.join(self.base_path, 'outbox_handler', 'outbox_messages.json')
        outbox_messages = self._read_json(outbox_path)

        remaining_outbox = [msg for msg in outbox_messages if msg.get("message_id") != msg_id_to_delete]

        if len(remaining_outbox) < len(outbox_messages):
            self._write_json(outbox_path, remaining_outbox)
            print(f"[Inbox] Mensagem {msg_id_to_delete} removida do outbox.")

    def _handle_inbox_delete_from_inbox(self, payload: Dict[str, Any]):
        """Remove um ID de mensagem do histórico de mensagens processadas do inbox."""
        msg_id_to_forget = payload.get("message_id_to_delete")
        if not msg_id_to_forget: return

        processed_ids_history = set(self._read_json(self.processed_inbox_ids_path))

        if msg_id_to_forget in processed_ids_history:
            processed_ids_history.remove(msg_id_to_forget)
            self._write_json(self.processed_inbox_ids_path, list(processed_ids_history))
            print(f"[Inbox] ID de mensagem {msg_id_to_forget} removido do histórico de processamento.")