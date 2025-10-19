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
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

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

        # --- Atualizar account.json ---
        accounts_path = self._get_main_dir_path('account.json')
        if os.path.exists(accounts_path):
            with open(accounts_path, 'r+', encoding='utf-8') as f:
                try:
                    accounts = json.load(f)
                    
                    patient_account = next((acc for acc in accounts if acc.get('user') == patient_user), None)
                    patient_id = patient_account.get('id') if patient_account else None

                    # Remover a conta do paciente
                    accounts = [acc for acc in accounts if acc.get('user') != patient_user]

                    # Desvincular este paciente de qualquer lista de 'linked_patients' de médicos
                    if patient_id:
                        for i, acc in enumerate(accounts):
                            if acc.get('profile_type') == 'doctor' and patient_id in acc.get('linked_patients', []):
                                accounts[i]['linked_patients'].remove(patient_id)

                    f.seek(0)
                    json.dump(accounts, f, indent=4)
                    f.truncate()

                    # --- Atualizar patient_ids.json ---
                    patient_ids_path = self._get_main_dir_path('patient_ids.json')
                    if patient_id and os.path.exists(patient_ids_path):
                        with open(patient_ids_path, 'r+', encoding='utf-8') as id_f:
                            patient_ids = json.load(id_f)
                            if patient_id in patient_ids:
                                patient_ids.remove(patient_id)
                            id_f.seek(0)
                            json.dump(patient_ids, id_f, indent=4)
                            id_f.truncate()

                except (json.JSONDecodeError, FileNotFoundError):
                    pass

        # --- Remover dados de outros arquivos JSON ---
        files_to_clean = {
            'patient_medications.json': patient_user,
            'patient_events.json': patient_user,
            'patient_evolution.json': patient_id
        }

        for filename, key in files_to_clean.items():
            if not key: continue
            file_path = self._get_main_dir_path(filename)
            if os.path.exists(file_path):
                with open(file_path, 'r+', encoding='utf-8') as f:
                    data = json.load(f)
                    if key in data:
                        del data[key]
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()

        print(f"Conta e todos os dados associados para {patient_user} foram deletados.")
        self.logout() # Faz o logout para limpar a sessão e retornar à tela inicial