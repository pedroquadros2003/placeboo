

from kivy.properties import StringProperty

from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder

Builder.load_file("auxiliary_classes/box_layout_with_action_bar.kv")

class BoxLayoutWithActionBar(BoxLayout):
    title = StringProperty("")