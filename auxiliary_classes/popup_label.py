from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.animation import Animation
from kivy.core.window import Window

from kivy.properties import ListProperty

class PopupLabel(Label):
    """
    Um Label que aparece na parte inferior da tela por um curto período e depois desaparece.
    Usado para fornecer feedback ao usuário (ex: erros, confirmações).
    """
    bg_color = ListProperty([0.8, 0.2, 0.2, 1]) # Default to red for errors

    def show(self, text, duration=2.5, bg_color=None):
        """
        Exibe o popup com o texto fornecido.
        :param text: O texto a ser exibido.
        :param duration: Quanto tempo o popup fica visível antes de desaparecer.
        :param bg_color: Cor de fundo do popup (RGBA).
        """
        self.text = text
        Window.add_widget(self) # Adiciona o widget diretamente à janela principal
        
        anim = Animation(opacity=1, d=0.3) + Animation(d=duration) + Animation(opacity=0, d=0.5)
        anim.bind(on_complete=self._remove_widget)
        anim.start(self)
        if bg_color:
            self.bg_color = bg_color

    def _remove_widget(self, *args):
        Window.remove_widget(self)

# Carrega o arquivo KV associado
Builder.load_file("auxiliary_classes/popup_label.kv")