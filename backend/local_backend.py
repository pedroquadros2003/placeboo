import json
import os
import shutil
from datetime import datetime
import uuid
import random
from backend.database_manager import PersistenceService

class LocalBackend:
    """
    Simula um backend de servidor local.
    - Lê mensagens da 'outbox'.
    - Valida ações (como login).
    - Gera mensagens de resposta (como success_login, establish_link).
    - Redireciona mensagens para a 'inbox' para serem processadas pelo cliente.
    """

    def __init__(self, base_path: str):
        """
        Inicializa o backend local.

        Args:
            base_path: O caminho raiz do projeto (onde 'account.json' está).
        """
        self.base_path = base_path
        self.inbox_handler_path = os.path.join(self.base_path, 'inbox_handler')
        self.inbox_path = os.path.join(self.inbox_handler_path, 'inbox_messages.json')
        self.outbox_handler_path = os.path.join(self.base_path, 'outbox_handler')
        self.outbox_path = os.path.join(self.outbox_handler_path, 'outbox_messages.json')
        self.db = PersistenceService(base_path)

    def _generate_server_message(self, obj, action, payload, origin_user_id="server"):
        """Cria uma nova mensagem com origem do servidor."""
        timestamp = datetime.now().isoformat(timespec='seconds') + 'Z'
        message_id = f"msg_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        return {
            "message_id": message_id,
            "timestamp": timestamp,
            "origin_user_id": origin_user_id,
            "object": obj,
            "action": action,
            "payload": payload
        }

    def process_outbox(self):
        """
        Processa todas as mensagens no outbox, gera respostas e as move para o inbox.
        """
        outbox_messages = self.db._read_db(self.outbox_path)
        if not outbox_messages:
            return

        inbox_messages = self.db._read_db(self.inbox_path)
        new_inbox_messages = []

        # Ações que são apenas de saída (cliente -> servidor) e não devem ser retransmitidas para o inbox.
        # O backend as processa e gera uma resposta, se necessário.
        OUT_ONLY_ACTIONS = {
            ("account", "delete_account"),
            ("account", "create_account"),
            ("account", "change_password"),
            ("account", "try_login"),
            ("linking_accounts", "invite_patient"),
            ("linking_accounts", "respond_to_invitation"),
            ("account", "delete_account"),
            ("account", "change_password"),
            # Ações de escrita que são retransmitidas para outros clientes
            # mas não precisam voltar para o remetente original.
            ("diagnostic", "add_diagnostic"), ("diagnostic", "edit_diagnostic"), ("diagnostic", "delete_diagnostic"),
            ("event", "add_event"), ("event", "edit_event"), ("event", "delete_event"),
            ("medication", "add_med"), ("medication", "edit_med"), ("medication", "delete_med"),
            ("evolution", "fill_metric"), ("evolution", "update_tracked_metrics"),
        }

        for msg in outbox_messages:
            obj = msg.get("object")
            action = msg.get("action")
            payload = msg.get("payload")
            origin_user = msg.get("origin_user_id")

            print(f"[Backend] Processando: {obj}/{action} de {origin_user}")

            # 1. Redireciona a mensagem original para o inbox, a menos que seja uma ação "out-only".
            if (obj, action) not in OUT_ONLY_ACTIONS:
                new_inbox_messages.append(msg)

            # 2. Gera respostas específicas do servidor
            if obj == "account" and action == "try_login":
                self._handle_login(msg, new_inbox_messages)

            elif obj == "account" and action == "create_account":
                self._handle_create_account(msg, new_inbox_messages)

            elif obj == "account" and action == "delete_account":
                self.db.delete_account(origin_user) # Ação de deleção no DB

            elif obj == "account" and action == "change_password":
                success = self.db.change_password(origin_user, payload.get("current_password"), payload.get("new_password"))
                # Poderíamos enviar uma mensagem de sucesso/falha de volta se quiséssemos

            elif obj == "diagnostic":
                self._handle_patient_data(msg, "patient_diagnostics.json")
            
            elif obj == "event":
                self._handle_patient_data(msg, "patient_events.json")

            elif obj == "medication":
                self._handle_patient_data(msg, "patient_medications.json")

            elif obj == "evolution" and action == "fill_metric":
                self.db.fill_evolution_metric(payload.get("patient_id"), payload.get("date"), payload.get("metrics"))
            elif obj == "evolution" and action == "update_tracked_metrics":
                self.db.update_tracked_metrics(payload.get("patient_id"), payload.get("tracked_metrics"))
            
            elif obj == "linking_accounts" and action == "invite_patient":
                # O origin_user é o médico que está convidando
                status = self.db.add_invitation(origin_user, payload.get("patient_user_to_invite"))
                # Poderíamos enviar uma mensagem de status de volta para a UI do médico

            elif obj == "linking_accounts" and action == "respond_to_invitation": # Paciente responde
                self.db.respond_to_invitation(origin_user, payload.get("doctor_id"), payload.get("response"))
                if payload.get("response") == "accept": # Notifica o médico se aceito
                    self._handle_accepted_invitation(payload, origin_user, new_inbox_messages)
            
            elif obj == "linking_accounts" and action == "unlink_accounts":
                self.db.unlink_account(origin_user, payload.get("target_user_id"))

            elif obj == "linking_accounts" and action == "invite_patient":
                 self._handle_new_invitation(payload, origin_user, new_inbox_messages)

        if new_inbox_messages:
            inbox_messages.extend(new_inbox_messages)
            self.db._write_db(self.inbox_path, inbox_messages)
            print(f"[Backend] {len(new_inbox_messages)} novas mensagens adicionadas ao inbox.")

        # Limpa o outbox após o processamento
        self.db._write_db(self.outbox_path, [])
        print("[Backend] Outbox limpo.")

    def _handle_patient_data(self, message, filename):
        """Handler genérico para CRUD de dados de paciente (diagnósticos, eventos, etc.)."""
        action = message.get("action")
        payload = message.get("payload")
        patient_user = payload.get("patient_user")

        if action in ["add_diagnostic", "add_event", "add_med"]:
            item_data = {k: v for k, v in payload.items() if k != 'patient_user'}
            self.db.add_item_to_patient_list(filename, patient_user, item_data)
        elif action in ["edit_diagnostic", "edit_event", "edit_med"]:
            self.db.edit_item_in_patient_list(filename, patient_user, payload.get("id"), payload)
        elif action in ["delete_diagnostic", "delete_event", "delete_med"]:
            self.db.delete_item_from_patient_list(filename, patient_user, payload.get("diagnostic_id") or payload.get("event_id") or payload.get("med_id"))

    def _handle_login(self, original_message, message_list):
        """Valida credenciais e gera uma mensagem de success_login ou fail_login."""
        payload = original_message.get("payload", {})
        original_msg_id = original_message.get("message_id")
        login_user = payload.get("user")
        login_password = payload.get("password")
        accounts = self.db.get_accounts()

        account = next((acc for acc in accounts if acc.get('user') == login_user and acc.get('password') == login_password), None)

        if account:
            # Login bem-sucedido
            response_payload = {
                "user_data": {
                    "id": account.get("id"),
                    "name": account.get("name"),
                    "user": account.get("user"),
                    "profile_type": account.get("profile_type")
                },
                "request_message_id": original_msg_id
            }
            server_msg = self._generate_server_message("account", "success_login", response_payload, origin_user_id=login_user)
            message_list.append(server_msg)
        else:
            # Falha no login
            response_payload = {"reason": "Usuário ou senha inválidos.", "request_message_id": original_msg_id}
            server_msg = self._generate_server_message("account", "fail_login", response_payload, origin_user_id=login_user)
            message_list.append(server_msg)

    def _handle_create_account(self, original_message, message_list):
        """Cria uma nova conta, salva e envia uma mensagem de success_login."""
        payload = original_message.get("payload", {})
        original_msg_id = original_message.get("message_id")
        accounts = self.db.get_accounts()
        user = payload.get("user")

        # --- Validação ---
        if not all(payload.get(k) for k in ["name", "user", "password", "profile_type"]):
            # Não envia resposta para o cliente, apenas loga o erro no backend.
            print("[Backend] Erro: Payload de create_account inválido.")
            return

        if any(acc['user'] == user for acc in accounts):
            response_payload = {"reason": f"Usuário '{user}' já existe.", "request_message_id": original_msg_id}
            server_msg = self._generate_server_message("account", "fail_login", response_payload, origin_user_id=user)
            message_list.append(server_msg)
            return

        # --- Criação da Conta ---
        profile_type = payload.get("profile_type")
        user_id = self._generate_unique_id(profile_type)

        base_user_data = {
            "profile_type": profile_type,
            "name": payload.get("name"),
            "user": user,
            "password": payload.get("password"),
            "id": user_id
        }

        # --- Lida com o caso "Médico também é paciente" ---
        if profile_type == 'doctor' and payload.get("is_also_patient"):
            patient_id = self._generate_unique_id('patient')
            doctor_as_patient_account = {
                "profile_type": "patient",
                "name": base_user_data['name'],
                "user": f"{user}_patient_profile",
                "password": "internal_use_only",
                "id": patient_id,
                "patient_info": payload.get("patient_info")
            }
            doctor_as_patient_account["patient_info"]["patient_code"] = patient_id
            doctor_as_patient_account["patient_info"]["responsible_doctors"] = [user_id]
            accounts.append(doctor_as_patient_account)

            base_user_data['linked_patients'] = [patient_id]
            base_user_data['self_patient_id'] = patient_id
            print(f"[Backend] Perfil de paciente ({patient_id}) criado para o médico {user_id}.")

        elif profile_type == 'patient':
            base_user_data["patient_info"] = payload.get("patient_info")
            base_user_data["patient_info"]["patient_code"] = user_id

        accounts.append(base_user_data)
        self.db.save_accounts(accounts)
        print(f"[Backend] Conta '{user}' criada com sucesso.")

        # --- Envia mensagem de success_login para o cliente ---
        login_response_payload = {
            "user_data": {
                "id": base_user_data.get("id"),
                "name": base_user_data.get("name"),
                "user": base_user_data.get("user"),
                "profile_type": base_user_data.get("profile_type")
            },
            "request_message_id": original_msg_id
        }
        server_msg = self._generate_server_message("account", "success_login", login_response_payload, origin_user_id=user)
        message_list.append(server_msg)

    def _generate_unique_id(self, id_type):
        """Gera um ID numérico único e o salva no arquivo de IDs correspondente."""
        filename = f"{id_type}_ids.json"
        existing_ids = self.db._read_db(filename)

        while True:
            new_id = str(random.randint(10000000, 99999999))
            if new_id not in existing_ids:
                existing_ids.append(new_id)
                self.db._write_db(filename, existing_ids)
                return new_id

    def _handle_accepted_invitation(self, payload, patient_user, message_list):
        """Gera uma mensagem 'establish_link' para o médico quando um paciente aceita um convite."""
        doctor_id = payload.get("doctor_id")
        accounts = self.db.get_accounts()
        patient_account = next((acc for acc in accounts if acc.get('user') == patient_user), None)
        
        if doctor_id and patient_account:
            response_payload = {
                "type": "link_established",
                "patient_info": {"id": patient_account.get("id"), "name": patient_account.get("name")}
            }
            # A mensagem é para o médico, então o origin_user_id é o ID do médico
            server_msg = self._generate_server_message("linking_accounts", "establish_link", response_payload, origin_user_id=doctor_id)
            message_list.append(server_msg)

    def _handle_new_invitation(self, payload, doctor_user, message_list):
        """Gera uma mensagem 'establish_link' para o paciente que foi convidado."""
        patient_user_to_invite = payload.get("patient_user_to_invite")
        accounts = self.db.get_accounts()
        doctor_account = next((acc for acc in accounts if acc.get('user') == doctor_user), None)

        if patient_user_to_invite and doctor_account:
            response_payload = {
                "type": "new_invitation",
                "doctor_info": {"id": doctor_account.get("id"), "name": doctor_account.get("name")}
            }
            # A mensagem é para o paciente, então o origin_user_id é o usuário do paciente
            server_msg = self._generate_server_message("linking_accounts", "establish_link", response_payload, origin_user_id=patient_user_to_invite)
            message_list.append(server_msg)
