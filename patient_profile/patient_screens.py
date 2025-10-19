from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import StringProperty
from datetime import datetime
import json
import os

from patient_profile.patient_medication_view import PatientMedicationsView
from patient_profile.patient_evolution_view import PatientEvolutionView
from patient_profile.patient_events_view import PatientEventsView
from patient_profile.patient_settings_view import PatientAppSettingsView
from patient_profile.add_doctor_view import AddDoctorView

class PatientHomeScreen(Screen):
    """
    Tela principal para o perfil do Paciente.
    Corresponde aos requisitos [R022], [R023], [R024].
    """
    title = StringProperty("Hoje: ")

    def on_enter(self, *args):
        """
        Chamado quando a tela está prestes a ser exibida.
        Carrega a data atual.
        """
        self.load_and_set_date()
        # Por padrão, exibe a tela de medicações [R024], mas apenas se nenhum conteúdo estiver selecionado.
        if not self.ids.content_manager.current:
            self.ids.content_manager.current = 'patient_medications'

    def load_and_set_date(self):
        """
        Carrega a data de app_data.json e atualiza o título.
        Se o arquivo não existir ou for inválido, usa a data atual do sistema.
        """
        # Use the system's current date directly
        date_str = datetime.now().strftime('%d/%m/%Y')
        self.title = f"Hoje: {date_str}"

    def change_content(self, screen_name):
        """Muda a view central."""
        # Define a ordem das telas para controlar a direção da animação
        screen_order = ['patient_evolution', 'patient_medications', 'patient_events']
        current_screen_name = self.ids.content_manager.current

        if current_screen_name == screen_name:
            return # Não faz nada se já estiver na tela

        try:
            current_index = screen_order.index(current_screen_name)
            target_index = screen_order.index(screen_name)

            # Define a direção da transição com base na posição dos botões
            self.ids.content_manager.transition.direction = 'left' if target_index > current_index else 'right'
        except ValueError:
            # Fallback para o caso de uma tela não estar na lista
            self.ids.content_manager.transition.direction = 'left'

        self.ids.content_manager.current = screen_name
        # Garante que a função on_enter da view seja chamada ao trocar de aba
        # É importante chamar isso DEPOIS de mudar o 'current'
        screen = self.ids.content_manager.get_screen(screen_name)
        # A view (ex: PatientEvolutionView) agora é a própria tela
        if hasattr(screen, 'on_enter'):
            screen.on_enter()

class PatientMenuScreen(Screen):
    """Tela de menu para o paciente."""
    def go_to_screen(self, screen_name):
        # Tratamento especial para configurações do aplicativo e adicionar médico, que são telas separadas
        if screen_name in ['patient_app_settings', 'add_doctor']:
            if self.manager.has_screen(screen_name):
                self.manager.push(screen_name)
            else:
                print(f"Erro: Tela '{screen_name}' não encontrada.")
            return

        # Para outras opções, troca o conteúdo na PatientHomeScreen
        if self.manager.get_screen('patient_home').ids.content_manager.has_screen(screen_name):
            self.manager.get_screen('patient_home').ids.content_manager.current = screen_name
            self.manager.pop() # Volta para a tela inicial para mostrar o novo conteúdo
        else:
            print(f"Erro: A tela de conteúdo '{screen_name}' não foi encontrada.")

class PatientMedicationsScreen(Screen, PatientMedicationsView): pass
class PatientEvolutionScreen(Screen, PatientEvolutionView): pass
class PatientEventsScreen(Screen, PatientEventsView): pass

# Telas para o conteúdo do menu
class PatientAppSettingsScreen(Screen):
    """Tela para hospedar a view de configurações do app do paciente."""
    pass

class AddDoctorScreen(Screen):
    """Tela para hospedar a view de adicionar médico."""
    pass

Builder.load_file("patient_profile/patient_screens.kv", encoding='utf-8')

# É importante carregar os novos arquivos KV depois de definir as classes
Builder.load_file("patient_profile/patient_settings_view.kv", encoding='utf-8')
Builder.load_file("patient_profile/add_doctor_view.kv", encoding='utf-8')