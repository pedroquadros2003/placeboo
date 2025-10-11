import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout

class LoginScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with open('usuarios.json', 'r', encoding='utf-8') as f:
            self.usuarios = json.load(f)

    def do_login(self):
        user = self.ids.username.text
        pwd = self.ids.password.text
        if user in self.usuarios and self.usuarios[user] == pwd:
            self.ids.result.text = 'Login bem-sucedido!'
        else:
            self.ids.result.text = 'Usuário ou senha incorretos.'

class LoginApp(App):
    def build(self):
        return LoginScreen()

if __name__ == '__main__':
    LoginApp().run()