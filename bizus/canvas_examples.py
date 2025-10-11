from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.graphics.vertex_instructions import Line, Rectangle, Ellipse
from kivy.graphics.context_instructions import Color
from kivy.properties import Clock


Builder.load_file("canvas_examples.kv")

class CanvasExample1(Widget):
    pass


class CanvasExample2(Widget):
    pass

class CanvasExample3(Widget):
    pass


class CanvasExample4(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Line(points=(100, 100, 400, 500), width=2)
            Color(0, 1, 0)
            Line(circle=(400, 200, 80), width=2) 
            ## elipse aqui são os semieixos, diferente da elipse preenchida
            Line(rectangle=(700, 500, 150, 100), width=5)
            self.rect = Rectangle(pos=(700, 200), size=(150, 100))

    def on_button_a_click(self):

        x, y = self.rect.pos
        width, height = self.rect.size
        inc = 12

        # Calcula a coordenada do lado direito
        right_side = x + width

        if right_side + inc < self.width:
            self.rect.pos = (x + inc, y)
        else:
            self.rect.pos = (self.width - width, y)
    

class CanvasExample5(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ball_vx = 4
        self.ball_vy = 3

        with self.canvas:
            Color(0, 1, 0, 1) # Verde
            self.ball = Ellipse(pos=(400, 200), size=(80, 80))  ## eixos maior e menor

        Clock.schedule_interval(self.update, 1/60)
    
    def on_size(self, *args):

        self.ball.pos = (self.center_x - self.ball.size[0]/2, self.center_y - self.ball.size[1]/2)

    def update(self, dt):

        if self.ball.pos[0] + self.ball.size[0] + self.ball_vx > self.width:
            self.ball_vx = - abs(self.ball_vx)
        
        if self.ball.pos[0] + self.ball_vx < 0:
            self.ball_vx =  abs(self.ball_vx)

        if self.ball.pos[1] + self.ball.size[1] + self.ball_vy > self.height:
            self.ball_vy = - abs(self.ball_vy)
        
        if self.ball.pos[1] + self.ball_vy < 0:
            self.ball_vy =  abs(self.ball_vy)


        self.ball.pos = (self.ball.pos[0] + self.ball_vx, self.ball.pos[1] + self.ball_vy)



class CanvasExample6(Widget):
    pass