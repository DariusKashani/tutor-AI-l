from manim import *

class SimpleScene(Scene):
    def construct(self):
        text = Text("Test Scene")
        self.play(Write(text))
        self.wait(1)
