import json
import os
from typing import Dict, List, Any

class PersistenceService:
    """
    Serviço que gerencia todas as operações de leitura e escrita nos arquivos JSON
    que funcionam como o banco de dados local do aplicativo.
    """

    def __init__(self, base_path: str):
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            base_path: O caminho raiz do projeto onde os arquivos JSON estão localizados.
        """
        self.db_path = base_path

    def _get_filepath(self, filename: str) -> str:
        """Constrói o caminho do arquivo, tratando os arquivos do backend como um caso especial."""
        backend_files = [
            'doctor_ids.json',
            'patient_ids.json',
            'placebo_transactions.json',
            'processed_transaction_ids.json'
        ]
        
        base_name = os.path.basename(filename)

        if base_name in backend_files:
            return os.path.join(self.db_path, 'backend', base_name)
        else:
            # Usa o caminho completo se fornecido, ou assume o diretório principal.
            return filename if os.path.isabs(filename) else os.path.join(self.db_path, base_name)

    def _read_db(self, filename: str) -> List | Dict:
        """Lê um arquivo JSON de forma segura, retornando uma lista ou dicionário."""
        filepath = self._get_filepath(filename)
        # Define quais arquivos devem ser dicionários por padrão.
        # Todos os outros serão tratados como listas.
        dict_files = [
            'patient_evolution.json',
            'patient_diagnostics.json',
            'patient_medications.json',
            'patient_events.json'
        ]

        if not os.path.exists(filepath):
            return {} if os.path.basename(filename) in dict_files else []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {} if os.path.basename(filename) in dict_files else []

    def _write_db(self, filename: str, data: List | Dict):
        """Escreve dados em um arquivo JSON."""
        filepath = self._get_filepath(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Retorna todas as contas de usuário."""
        return self._read_db('account.json')

    def save_accounts(self, accounts: List[Dict[str, Any]]):
        """Salva a lista de contas de usuário."""
        self._write_db('account.json', accounts)

    def get_patient_data(self, filename: str) -> Dict[str, Any]:
        """Retorna dados específicos de pacientes (diagnósticos, eventos, etc.)."""
        return self._read_db(filename)

    def save_patient_data(self, filename: str, data: Dict[str, Any]):
        """Salva dados específicos de pacientes."""
        self._write_db(filename, data)

    # --- Métodos Específicos por Objeto ---

    def add_item_to_patient_list(self, filename: str, patient_user: str, item_data: Dict):
        """Adiciona um item (diagnóstico, evento, medicação) à lista de um paciente."""
        all_data = self.get_patient_data(filename)
        patient_list = all_data.get(patient_user, [])
        patient_list.append(item_data)
        all_data[patient_user] = patient_list
        self.save_patient_data(filename, all_data)
        print(f"[DB] Item adicionado para {patient_user} em {filename}.")

    def edit_item_in_patient_list(self, filename: str, patient_user: str, item_id: str, updated_data: Dict):
        """Edita um item na lista de um paciente."""
        all_data = self.get_patient_data(filename)
        patient_list = all_data.get(patient_user, [])
        
        item_found = False
        for i, item in enumerate(patient_list):
            if item.get('id') == item_id:
                # Mantém campos originais que não estão no payload de atualização (ex: date_added)
                original_item = patient_list[i].copy()
                original_item.update(updated_data)
                patient_list[i] = original_item
                item_found = True
                break
        
        if item_found:
            all_data[patient_user] = patient_list
            self.save_patient_data(filename, all_data)
            print(f"[DB] Item {item_id} editado para {patient_user} em {filename}.")
        else:
            print(f"[DB] Aviso: Item {item_id} não encontrado para edição em {filename}.")

    def delete_item_from_patient_list(self, filename: str, patient_user: str, item_id: str):
        """Deleta um item da lista de um paciente."""
        all_data = self.get_patient_data(filename)
        patient_list = all_data.get(patient_user, [])
        
        original_len = len(patient_list)
        patient_list = [item for item in patient_list if item.get('id') != item_id]

        if len(patient_list) < original_len:
            all_data[patient_user] = patient_list
            self.save_patient_data(filename, all_data)
            print(f"[DB] Item {item_id} deletado para {patient_user} em {filename}.")
        else:
            print(f"[DB] Aviso: Item {item_id} não encontrado para deleção em {filename}.")

    def fill_evolution_metric(self, patient_id: str, date: str, metrics: Dict):
        """Salva ou atualiza as métricas de evolução para um paciente em uma data."""
        all_evolutions = self.get_patient_data('patient_evolution.json')
        patient_evolution = all_evolutions.get(patient_id, {})
        
        if date not in patient_evolution:
            patient_evolution[date] = {}
        
        patient_evolution[date].update(metrics)
        all_evolutions[patient_id] = patient_evolution
        self.save_patient_data('patient_evolution.json', all_evolutions)
        print(f"[DB] Métricas de evolução salvas para {patient_id} em {date}.")

    def update_tracked_metrics(self, patient_id: str, tracked_metrics: List[str]):
        """Atualiza a lista de métricas rastreadas para um paciente."""
        accounts = self.get_accounts()
        old_tracked_metrics = []

        for i, acc in enumerate(accounts):
            if acc.get('id') == patient_id:
                old_tracked_metrics = acc.get('patient_info', {}).get('tracked_metrics', [])
                if 'patient_info' not in acc:
                    accounts[i]['patient_info'] = {}
                accounts[i]['patient_info']['tracked_metrics'] = tracked_metrics
                self.save_accounts(accounts)
                print(f"[DB] Métricas rastreadas atualizadas para o paciente {patient_id}.")
                break
        
        # Remove dados de métricas não selecionadas do histórico de evolução
        metrics_to_remove = set(old_tracked_metrics) - set(tracked_metrics)
        if metrics_to_remove:
            all_evolutions = self.get_patient_data('patient_evolution.json')
            patient_evolution = all_evolutions.get(patient_id, {})
            if patient_evolution:
                for date_record in patient_evolution.values():
                    for metric_key in metrics_to_remove:
                        if metric_key in date_record:
                            del date_record[metric_key]
                all_evolutions[patient_id] = patient_evolution
                self.save_patient_data('patient_evolution.json', all_evolutions)
                print(f"[DB] Dados de métricas antigas removidos para {patient_id}.")

    def change_password(self, user: str, current_pass: str, new_pass: str) -> bool:
        """Altera a senha de um usuário se a senha atual estiver correta."""
        accounts = self.get_accounts()
        for i, acc in enumerate(accounts):
            if acc.get('user') == user:
                if acc.get('password') == current_pass:
                    accounts[i]['password'] = new_pass
                    self.save_accounts(accounts)
                    print(f"[DB] Senha alterada para o usuário {user}.")
                    return True
                else:
                    return False # Senha atual incorreta
        return False # Usuário não encontrado

    def delete_account(self, user_to_delete: str) -> bool:
        """Deleta uma conta de usuário e todas as suas referências."""
        accounts = self.get_accounts()
        account_to_delete = next((acc for acc in accounts if acc.get('user') == user_to_delete), None)
        
        if not account_to_delete:
            print(f"[DB] Conta {user_to_delete} não encontrada para deleção.")
            return False

        user_id_to_delete = account_to_delete.get('id')
        profile_type = account_to_delete.get('profile_type')

        # 1. Remove a conta principal
        accounts = [acc for acc in accounts if acc.get('user') != user_to_delete]

        # 2. Remove referências cruzadas
        if profile_type == 'doctor':
            # Remove o ID do médico da lista de responsáveis de cada paciente
            for i, acc in enumerate(accounts):
                if acc.get('profile_type') == 'patient' and user_id_to_delete in acc.get('patient_info', {}).get('responsible_doctors', []):
                    accounts[i]['patient_info']['responsible_doctors'].remove(user_id_to_delete)
            # Remove o ID do arquivo de IDs de médicos
            doctor_ids = self._read_db('doctor_ids.json')
            if user_id_to_delete in doctor_ids:
                doctor_ids.remove(user_id_to_delete)
                self._write_db('doctor_ids.json', doctor_ids)

        elif profile_type == 'patient':
            # Remove o ID do paciente da lista de vinculados de cada médico
            for i, acc in enumerate(accounts):
                if acc.get('profile_type') == 'doctor' and user_id_to_delete in acc.get('linked_patients', []):
                    accounts[i]['linked_patients'].remove(user_id_to_delete)
            # Remove o ID do arquivo de IDs de pacientes
            patient_ids = self._read_db('patient_ids.json')
            if user_id_to_delete in patient_ids:
                patient_ids.remove(user_id_to_delete)
                self._write_db('patient_ids.json', patient_ids)
            
            # 3. Limpa os dados do paciente de outros arquivos
            files_to_clean = {
                'patient_medications.json': user_to_delete,
                'patient_events.json': user_to_delete,
                'patient_evolution.json': user_id_to_delete
            }
            for filename, key in files_to_clean.items():
                data = self.get_patient_data(filename)
                if key in data:
                    del data[key]
                    self.save_patient_data(filename, data)

        self.save_accounts(accounts)
        print(f"[DB] Conta {user_to_delete} e todos os dados associados foram deletados.")
        return True

    def add_invitation(self, doctor_user: str, patient_user_to_invite: str) -> str:
        """Adiciona um convite de um médico para um paciente."""
        accounts = self.get_accounts()
        doctor_account = next((acc for acc in accounts if acc.get('user') == doctor_user), None)
        patient_account = next((acc for acc in accounts if acc.get('user') == patient_user_to_invite), None)

        if not doctor_account or not patient_account: return "Médico ou paciente não encontrado."
        if patient_account.get('profile_type') != 'patient': return "Usuário alvo não é um paciente."

        doctor_id = doctor_account.get('id')
        patient_id = patient_account.get('id')

        if doctor_id in patient_account.get('patient_info', {}).get('responsible_doctors', []): return "Paciente já vinculado."
        if doctor_id in patient_account.get('invitations', []): return "Convite já enviado."

        for i, acc in enumerate(accounts):
            if acc.get('id') == patient_id:
                if 'invitations' not in accounts[i]: accounts[i]['invitations'] = []
                accounts[i]['invitations'].append(doctor_id)
                self.save_accounts(accounts)
                return "Convite enviado com sucesso."
        return "Erro ao processar convite."

    def respond_to_invitation(self, patient_user: str, doctor_id: str, response: str):
        """Processa a resposta de um paciente a um convite."""
        accounts = self.get_accounts()
        patient_account = next((acc for acc in accounts if acc.get('user') == patient_user), None)
        if not patient_account: return

        patient_id = patient_account.get('id')

        for i, acc in enumerate(accounts):
            if acc.get('id') == patient_id:
                if 'invitations' in acc and doctor_id in acc['invitations']:
                    accounts[i]['invitations'].remove(doctor_id)
                    if response == 'accept':
                        if 'responsible_doctors' not in accounts[i]['patient_info']: accounts[i]['patient_info']['responsible_doctors'] = []
                        accounts[i]['patient_info']['responsible_doctors'].append(doctor_id)
                        # Adiciona o paciente à lista do médico
                        for j, doc_acc in enumerate(accounts):
                            if doc_acc.get('id') == doctor_id:
                                if 'linked_patients' not in doc_acc: accounts[j]['linked_patients'] = []
                                accounts[j]['linked_patients'].append(patient_id)
                                break
        self.save_accounts(accounts)
        print(f"[DB] Resposta ao convite de {doctor_id} por {patient_user} processada.")

    def unlink_account(self, user_unlinking: str, target_user_id: str):
        """Desvincula um paciente de um médico (ou vice-versa)."""
        accounts = self.get_accounts()
        user_account = next((acc for acc in accounts if acc.get('user') == user_unlinking), None)
        if not user_account: return

        user_id = user_account.get('id')
        
        # Itera e remove as referências cruzadas
        for i, acc in enumerate(accounts):
            # Remove o médico da lista do paciente
            if acc.get('id') == target_user_id and acc.get('profile_type') == 'patient':
                if user_id in acc.get('patient_info', {}).get('responsible_doctors', []):
                    accounts[i]['patient_info']['responsible_doctors'].remove(user_id)
            # Remove o paciente da lista do médico
            if acc.get('id') == user_id and acc.get('profile_type') == 'doctor':
                if target_user_id in acc.get('linked_patients', []):
                    accounts[i]['linked_patients'].remove(target_user_id)
        self.save_accounts(accounts)
        print(f"[DB] Desvinculação entre {user_id} e {target_user_id} processada.")