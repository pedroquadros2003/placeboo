from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.animation import Animation
from kivy.core.window import Window

# Carrega o arquivo KV associado
Builder.load_file("auxiliary_classes/popup_label.kv")

class PopupLabel(Label):
    """
    Um Label que aparece na parte inferior da tela por um curto período e depois desaparece.
    Usado para fornecer feedback ao usuário (ex: erros, confirmações).
    """
    def show(self, text, duration=2.5):
        """
        Exibe o popup com o texto fornecido.
        :param text: O texto a ser exibido.
        :param duration: Quanto tempo o popup fica visível antes de desaparecer.
        """
        self.text = text
        Window.add_widget(self) # Adiciona o widget diretamente à janela principal
        
        anim = Animation(opacity=1, d=0.3) + Animation(d=duration) + Animation(opacity=0, d=0.5)
        anim.bind(on_complete=self._remove_widget)
        anim.start(self)

    def _remove_widget(self, *args):
        Window.remove_widget(self)