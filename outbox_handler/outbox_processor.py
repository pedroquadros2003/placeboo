import json
import os
from typing import Dict, Any
from datetime import datetime
import uuid

class OutboxProcessor:
    """
    Gera mensagens de 'outbox' para registrar ações do usuário e
    também processa mensagens de 'outbox' (vindas do servidor, futuramente).
    """

    def __init__(self, user_data_path: str):
        """
        Inicializa o processador de mensagens.

        Args:
            user_data_path: O caminho absoluto para a pasta 'user_data'.
        """
        if not os.path.isdir(user_data_path):
            raise FileNotFoundError(f"O diretório de dados do usuário não foi encontrado: {user_data_path}")
        self.user_data_path = user_data_path

    def _read_json_file(self, filename: str) -> Dict | list:
        """Lê um arquivo JSON de forma segura."""
        filepath = os.path.join(self.user_data_path, filename)
        if not os.path.exists(filepath): # Se o arquivo não existe, retorna um valor padrão
            return {} if filename != 'my_account.json' else [] # Retorna lista vazia para 'my_account.json', dicionário para outros
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {} if filename != 'my_account.json' else []

    def _write_json_file(self, filename: str, data: Dict | list):
        """Escreve dados em um arquivo JSON de forma segura."""
        filepath = os.path.join(self.user_data_path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def process_message(self, message_data: str | Dict[str, Any]):
        """
        Processa uma única mensagem, decodifica e executa a ação correspondente.
        """
        try:
            if isinstance(message_data, str):
                message = json.loads(message_data)
            else:
                message = message_data

            if not all(k in message for k in ['object', 'action', 'payload']):
                print("Erro de processamento: Mensagem com formato inválido.")
                return

            obj = message.get('object')
            action = message.get('action')
            payload = message.get('payload', {})

            # Constrói o nome do método manipulador (ex: _handle_diagnostic_add)
            handler_method_name = f"_handle_{obj}_{action}"
            handler_method = getattr(self, handler_method_name, self._handle_unknown)
            
            print(f"Processando: {obj}/{action}")
            handler_method(payload)

        except Exception as e:
            print(f"Erro ao processar a mensagem: {e}")

    def _handle_unknown(self, payload: Dict[str, Any]):
        """Manipula ações desconhecidas."""
        print(f"Ação não implementada no processador.")

    # --- Manipuladores de Ações ---

    def _handle_diagnostic_add(self, payload: Dict[str, Any]):
        """Adiciona um novo diagnóstico ao arquivo do paciente."""
        patient_user = payload.get('patient_user')
        if not patient_user:
            print("Erro: 'patient_user' não encontrado no payload do diagnóstico.")
            return

        all_diagnostics = self._read_json_file('my_patient_diagnostics.json')
        patient_diagnostics = all_diagnostics.get(patient_user, [])
        
        # Remove chaves que não pertencem ao modelo de dados do diagnóstico
        new_diagnostic_data = {k: v for k, v in payload.items() if k != 'patient_user'}
        
        patient_diagnostics.append(new_diagnostic_data)
        all_diagnostics[patient_user] = patient_diagnostics
        
        self._write_json_file('patient_diagnostics.json', all_diagnostics)
        print(f"Diagnóstico adicionado para {patient_user}.")

    def _get_origin_user_id(self) -> str | None:
        """Reads the current logged-in user from my_session.json."""
        session_filepath = os.path.join(self.user_data_path, 'session.json')
        if os.path.exists(session_filepath):
            try:
                with open(session_filepath, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    return session_data.get('user')
            except json.JSONDecodeError:
                pass
        return None

    def add_to_outbox(self, obj: str, action: str, payload: Dict[str, Any], origin_user_override: str = None) -> str | None:
        """
        Gera uma mensagem e a anexa ao arquivo outbox_messages.json.
        Isso é executado em paralelo com as gravações de arquivo locais existentes.
        Retorna o message_id da mensagem criada.
        """
        origin_user_id = self._get_origin_user_id() or origin_user_override
        
        if not origin_user_id:
            print(f"Aviso: Não foi possível determinar o origin_user_id para a mensagem {obj}/{action}. Mensagem não registrada no outbox.")
            return None

        message_id = f"msg_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        message = {
            "message_id": message_id,
            # O timestamp será adicionado pelo backend ao processar a mensagem
            "origin_user_id": origin_user_id,
            "object": obj,
            "action": action,
            "payload": payload
        }
        
        # O arquivo outbox_messages.json deve estar sempre na mesma pasta que este script.
        outbox_filepath = os.path.join(self.user_data_path, 'outbox_handler', 'outbox_messages.json')
        all_messages = []
        if os.path.exists(outbox_filepath):
            try:
                with open(outbox_filepath, 'r', encoding='utf-8') as f:
                    all_messages = json.load(f)
            except json.JSONDecodeError:
                pass
        
        all_messages.append(message)

        with open(outbox_filepath, 'w', encoding='utf-8') as f:
            json.dump(all_messages, f, indent=4)
        print(f"[Outbox] Mensagem {message.get('object')}/{message.get('action')} adicionada ao outbox_messages.json.")
        return message_id

    def _handle_diagnostic_edit(self, payload: Dict[str, Any]):
        """Edita um diagnóstico existente no arquivo do paciente."""
        patient_user = payload.get('patient_user')
        diagnostic_id = payload.get('diagnostic_id')

        if not all([patient_user, diagnostic_id]):
            print("Erro: 'patient_user' e 'diagnostic_id' são necessários para editar.")
            return

        all_diagnostics = self._read_json_file('patient_diagnostics.json')
        patient_diagnostics = all_diagnostics.get(patient_user, [])
        
        diagnostic_found = False
        for i, diag in enumerate(patient_diagnostics):
            if diag.get('id') == diagnostic_id:
                # Atualiza apenas as chaves presentes no payload
                for key, value in payload.items():
                    if key in diag:
                        patient_diagnostics[i][key] = value
                diagnostic_found = True
                break
        
        if diagnostic_found:
            all_diagnostics[patient_user] = patient_diagnostics
            self._write_json_file('patient_diagnostics.json', all_diagnostics)
            print(f"Diagnóstico {diagnostic_id} atualizado para {patient_user}.")
        else:
            print(f"Diagnóstico {diagnostic_id} não encontrado para {patient_user}.")

    def _handle_event_add(self, payload: Dict[str, Any]):
        """Adiciona um novo evento (consulta/exame) ao arquivo do paciente."""
        patient_user = payload.get('patient_user')
        if not patient_user:
            print("Erro: 'patient_user' não encontrado no payload do evento.")
            return

        all_events = self._read_json_file('patient_events.json')
        patient_events = all_events.get(patient_user, [])
        
        new_event_data = {k: v for k, v in payload.items() if k != 'patient_user'}
        
        patient_events.append(new_event_data)
        all_events[patient_user] = patient_events
        
        self._write_json_file('patient_events.json', all_events)
        print(f"Evento adicionado para {patient_user}.")

    def _handle_account_success_login(self, payload: Dict[str, Any]):
        """
        Processa uma mensagem de login bem-sucedido, salvando os dados da sessão.
        """
        user_data = payload.get('user_data')
        if not user_data or not all(k in user_data for k in ['user', 'profile_type']):
            print("Erro: Payload de 'success_login' inválido.")
            return

        session_data = {
            'logged_in': True,
            'user': user_data['user'],
            'profile_type': user_data['profile_type']
        }
        self._write_json_file('my_session.json', session_data)
        print(f"Sessão criada para o usuário: {user_data['user']}.")


# Exemplo de uso (pode ser removido ou comentado depois)
if __name__ == '__main__':
    # O caminho para a pasta user_data precisa ser absoluto ou relativo ao local de execução
    # Para este exemplo, vamos subir dois níveis a partir de 'outbox_handler'
    base_dir = os.path.dirname(os.path.dirname(__file__))
    USER_DATA_DIR = os.path.join(base_dir, 'user_data')

    processor = OutboxProcessor(USER_DATA_DIR)

    # Mensagem de exemplo para adicionar um diagnóstico
    add_diag_msg = {
      "object": "diagnostic",
      "action": "add_diagnostic",
      "payload": {
        "patient_user": "jane.doe_patient_profile",
        "diagnostic_id": "diag_test_123",
        "cid_code": "J45",
        "name": "Asma",
        "description": "Asma induzida por exercício.",
        "date_added": "2024-05-22T10:00:00Z"
      }
    }

    processor.process_message(add_diag_msg)