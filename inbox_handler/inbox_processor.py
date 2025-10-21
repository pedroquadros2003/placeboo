import json
import os
from typing import Dict, Any

class InboxProcessor:
    """
    Processa mensagens da 'inbox' e aplica as alterações necessárias
    nos arquivos JSON dentro de um diretório de dados do usuário.
    """

    def __init__(self, user_data_path: str):
        """
        Inicializa o processador.

        Args:
            user_data_path: O caminho absoluto para a pasta 'user_data'.
        """
        if not os.path.isdir(user_data_path):
            raise FileNotFoundError(f"O diretório de dados do usuário não foi encontrado: {user_data_path}")
        self.user_data_path = user_data_path

    def _read_json_file(self, filename: str) -> Dict | list:
        """Lê um arquivo JSON de forma segura."""
        filepath = os.path.join(self.user_data_path, filename)
        if not os.path.exists(filepath):
            return {} if filename != 'account.json' else []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {} if filename != 'account.json' else []

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

        all_diagnostics = self._read_json_file('patient_diagnostics.json')
        patient_diagnostics = all_diagnostics.get(patient_user, [])
        
        # Remove chaves que não pertencem ao modelo de dados do diagnóstico
        new_diagnostic_data = {k: v for k, v in payload.items() if k != 'patient_user'}
        
        patient_diagnostics.append(new_diagnostic_data)
        all_diagnostics[patient_user] = patient_diagnostics
        
        self._write_json_file('patient_diagnostics.json', all_diagnostics)
        print(f"Diagnóstico adicionado para {patient_user}.")

    # Adicione outros métodos de manipulação aqui, como:
    # def _handle_diagnostic_edit(self, payload): ...
    # def _handle_event_add(self, payload): ...
    # def _handle_account_success_login(self, payload): ...


# Exemplo de uso (pode ser removido ou comentado depois)
if __name__ == '__main__':
    # O caminho para a pasta user_data precisa ser absoluto ou relativo ao local de execução
    # Para este exemplo, vamos subir dois níveis a partir de 'inbox_handler'
    base_dir = os.path.dirname(os.path.dirname(__file__))
    USER_DATA_DIR = os.path.join(base_dir, 'user_data')

    processor = InboxProcessor(USER_DATA_DIR)

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