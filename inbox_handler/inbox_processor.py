import json
import os
from typing import Dict, Any
from kivy.app import App
from kivy.clock import mainthread
from inbox_handler.message_decoder import MessageDecoder
from backend.database_manager import PersistenceService

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
        "try_logout": "Logout realizado com sucesso",
        "add_med": "Medicação adicionada",
        "delete_med": "Medicação removida",
        "edit_med": "Medicação editada"
    }

    def __init__(self, base_path: str, db_manager: PersistenceService):
        '''
        Inicializa o processador de inbox.

        Args:
            base_path: O caminho raiz do projeto.
            db_manager: Instância do PersistenceService para manipulação de arquivos.
        '''
        
        self.base_path = base_path
        self.inbox_path = os.path.join(self.base_path, 'inbox_handler', 'inbox_messages.json')
        self.db = db_manager
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

                    # Se a ação foi um login bem-sucedido, a sessão foi criada.
                    # Reavaliamos o session_user para processar mensagens subsequentes no mesmo ciclo.
                    if msg.get("action") == "try_login_cback" and payload.get("executed"):
                        session_user = app.outbox_processor._get_origin_user_id()
                
                processed_ids_this_cycle.add(msg_id)
            else:
                # Se a mensagem não foi processada, verificamos se ela deve ser mantida.
                # Mantemos apenas as respostas de login/criação de conta pendentes.
                # Todas as outras mensagens que não são para o usuário atual são descartadas.
                is_pending_login_response = (current_pending_request_id and
                                             payload.get("request_message_id") == current_pending_request_id)

                if is_pending_login_response:
                    remaining_messages.append(msg)
        
        # Atualiza o histórico de IDs processados e o arquivo do inbox.
        # Esta reescrita é crucial para remover as mensagens processadas e evitar loops infinitos.
        if processed_ids_this_cycle:
            updated_history = processed_ids_history.union(processed_ids_this_cycle)
            self._write_json(self.processed_inbox_ids_path, list(updated_history))
        self._write_json(self.inbox_path, remaining_messages)

    def _route_message(self, message: Dict[str, Any]):
        """Direciona a mensagem para o handler apropriado."""
        obj = message.get('object') # Já validado pelo decoder
        action = message.get('action') # Já validado pelo decoder
        payload = message.get('payload', {}) # Já validado pelo decoder
        
        # Se for uma mensagem de 'comeback', usa o handler genérico.
        if action.endswith('_cback') and action != 'try_login_cback':
            print(f"[InboxProcessor] Mensagem de comeback. Roteando para o método: _handle_comeback")
            if action == 'try_logout_cback': # Caso especial de logout
                self._handle_try_logout_cback(payload)
            self._handle_comeback(action, payload)
        else:
            # Para todas as outras mensagens, busca um handler específico.
            handler_method_name = f"_handle_{obj}_{action}"
            handler_method = getattr(self, handler_method_name, self._handle_unknown)
            print(f"[InboxProcessor] Mensagem entendida. Roteando para o método: {handler_method_name}")
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
            # Caso especial para alteração de senha: fecha a tela em caso de sucesso.
            elif action == "change_password_cback":
                change_password_screen = app.manager.get_screen('change_password')
                app.show_success_popup(f"{translated_message}!")
                change_password_screen.ids.change_password_view_content.clear_fields()
                app.manager.pop()
            # Caso especial para desvinculação: recarrega a tela de gerenciamento correspondente.
            elif action == "unlink_accounts_cback":
                app.show_success_popup(f"{translated_message}!")
                # Acessa o ScreenManager interno da DoctorHomeScreen pelo seu ID.
                doctor_home_screen = app.manager.get_screen('doctor_home')
                content_manager = doctor_home_screen.ids.content_manager
                
                if content_manager.current == 'doctor_patient_management':
                    # Acessa a view pelo ID que definimos no arquivo .kv
                    patient_management_screen = content_manager.get_screen('doctor_patient_management')
                    patient_management_screen.ids.patient_management_view_content.load_linked_patients()
                    print("[DEBUG] Chamando load_linked_patients() para o médico.")

                # Se o paciente está na tela de gerenciamento, atualiza a lista dele.
                elif app.manager.current == 'patient_manage_doctors':
                    patient_manage_screen = app.manager.get_screen('patient_manage_doctors')
                    patient_manage_screen.ids.manage_doctors_view_content.load_data()
                    print("[DEBUG] Chamando load_data() para o paciente.")
          
            else:
                app.show_success_popup(f"{translated_message}!")
        else:
            reason = payload.get("reason", "A operação falhou.")
            app.show_error_popup(f"Erro: {reason}")

    def _force_logout(self):
        """Força o logout do cliente, limpando a sessão."""
        print("[Inbox] Forçando logout após ação bem-sucedida (ex: delete_account).")
        # Centraliza a deleção do arquivo de sessão no database_manager
        self.db.delete_file('session.json')
        App.get_running_app().manager.reset_to('initial_access')

    def _handle_account_try_login_cback(self, payload: Dict[str, Any]):
        """Processa a resposta de uma tentativa de login ou criação de conta."""
        app = App.get_running_app()
        
        if payload.get("executed"):
            # Sucesso: cria a sessão e redireciona
            user_data = payload.get('user_data')
            if not user_data: return

            session_data = {'logged_in': True, 'user': user_data['user'], 'profile_type': user_data['profile_type']}
            self.db.save_session(session_data)

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

    @mainthread
    def _handle_try_logout_cback(self, payload: Dict[str, Any]):
        """
        Processa a confirmação de logout, limpando a sessão e resetando a UI.
        """
        if payload.get("executed"):
            print("[Inbox] Recebido try_logout_cback. Executando logout no cliente.")
            self._force_logout()
        else:
            # Em teoria, um logout não deveria falhar, mas tratamos o caso.
            reason = payload.get("reason", "Falha ao tentar fazer logout.")
            App.get_running_app().show_error_popup(f"Erro: {reason}")

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

    @mainthread
    def _handle_linking_accounts_unlink_accounts(self, payload: Dict[str, Any]):
        """
        Processa a mensagem de broadcast para desvinculação.
        Para o cliente que originou a ação, esta mensagem é apenas para confirmação e não dispara UI.
        Para o outro cliente (o alvo da desvinculação), este método pode ser expandido para
        recarregar sua respectiva view (ex: a lista de médicos do paciente).
        """
        print("[Inbox] Mensagem de broadcast 'unlink_accounts' recebida e processada.")
        # Conforme solicitado, este método não fará nenhuma atualização de UI.
        # A atualização da tela do usuário que iniciou a ação é de responsabilidade
        # exclusiva do método _handle_comeback, que processa a mensagem _cback.
        pass
