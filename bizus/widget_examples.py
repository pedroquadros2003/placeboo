from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.gridlayout import GridLayout
from kivy.lang import Builder

Builder.load_file("widget_examples.kv")

class WidgetsExample(GridLayout):
    my_text =  StringProperty("0")
    slider_number = StringProperty("")
    counter_active = BooleanProperty(False)
    input_text = StringProperty("foo")
    ## properties são variáveis reativas, 
    ## só elas podem ser invocadas no .kv
    ## sempre declaradas aqui


    def on_button_click(self):
        
        if self.counter_active:
            self.my_text =  str(int(self.my_text)+1)

    def on_switch_active(self, widget):

        print(widget.active)


    def on_toggle_button_state(self, widget):
        
        if (widget.state == "down"):
            widget.text = "ON"
            self.counter_active = True
        elif ( widget.state == "normal"):
            widget.text = "OFF" ##outra forma de alterar texto
            self.counter_active = False


    def on_slider_value(self, widget):

        self.slider_number = str(int(widget.value))
        print(f"Slider : {widget.value}")

    def on_text_validate(self, widget):

        self.input_text = widget.text