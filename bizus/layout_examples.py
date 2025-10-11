from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty


Builder.load_file("layout_examples.kv")


class BoxLayoutExample(BoxLayout):
    '''
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        b1 = Button(text = "ABC")
        b2 = Button(text = "AB")
        b3 = Button(text = "C")
        self.add_widget(b1)
        self.add_widget(b2)
        self.add_widget(b3)
    '''
    pass


class StackLayoutExampleDP(StackLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        size = dp(40)

        b = Button(text='Z', size_hint=(None, None), size = (size, size))
        self.add_widget(b)

        for i in range(0, 1000):
            b = Button(text=str(i+1), size_hint=(None, None), size = (size, size))
            self.add_widget(b)

class StackLayoutExample(StackLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ## Inicialização é adicionada primeiro, depois 
        ## vem o arquivo kivy
        b = Button(text='Z', size_hint=(.2, .2))
        self.add_widget(b)

        for i in range(0, 25):
            b = Button(text=str(i+1), size_hint=(.2, .2))
            ## size_hint(None, None)  size = (dp(40), dp(40))
            self.add_widget(b)



class AnchorLayoutExample(AnchorLayout):
    pass


class MainWidget(Widget):
    pass 