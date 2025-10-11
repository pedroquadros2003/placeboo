from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from navigation_screen_manager import NavigationScreenManager



class MyScreenManager(NavigationScreenManager):
    pass


class PlaceboApp (App):  ## Aplicações em Kivy terminam em App
    manager = ObjectProperty(None)
    
    def build(self):
        self.manager = MyScreenManager()
        return self.manager

PlaceboApp().run()