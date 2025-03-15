from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Title for the animation
        title = Text("Transforming Shapes", font_size=48)
        self.play(Write(title))
        self.wait(1)

        # Transition from title to the animation
        self.play(FadeOut(title))

        # Create a blue circle
        circle = Circle(color=BLUE)
        circle.set_fill(BLUE, opacity=0.5)
        self.play(Create(circle))
        self.wait(1)

        # Transform Circle into a red square
        square = Square(color=RED)
        square.set_fill(RED, opacity=0.5)
        self.play(Transform(circle, square))
        self.wait(2)