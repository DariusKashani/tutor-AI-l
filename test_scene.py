from manim import *
class TestScene(Scene):
    def construct(self):
        self.play(Write(Text('Hello, Manim!')))
        self.wait(1)
