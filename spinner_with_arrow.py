from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import StringProperty, ListProperty, BooleanProperty, AliasProperty
from kivy.lang import Builder

Builder.load_file('spinner_with_arrow.kv', encoding='utf-8')

class SpinnerWithArrow(RelativeLayout):
    """
    A compound widget that combines a Spinner with a dropdown arrow Image,
    mimicking a standard text input appearance.
    """
    values = ListProperty([])
    disabled = BooleanProperty(False)
    text = StringProperty('') # This will now be the single source of truth.