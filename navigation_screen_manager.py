from kivy.uix.screenmanager import ScreenManager


class NavigationScreenManager(ScreenManager):  # Example base class, adjust as needed
	
    screen_stack = []

    def push(self, screen_name):
        ## empilhamos a screen atual e colocamos uma nova
        if not screen_name in self.screen_stack:
            self.screen_stack.append(self.current)
            self.current = screen_name
            self.transition.direction = "left"

    def pop(self):
        if len(self.screen_stack)>0:
            last_screen = self.screen_stack[-1]
            del self.screen_stack[-1]
            self.current = last_screen
            self.transition.direction = "right"