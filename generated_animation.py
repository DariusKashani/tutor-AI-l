# Import necessary modules from Manim
from manim import *

# Define a scene class named "UserAnimationScene" inheriting from Scene
class UserAnimationScene(Scene):
    def construct(self):
        # Create a red square
        square = Square(color=RED)

        # Define the animation: move the square from left to right
        self.play(ApplyMethod(square.shift, RIGHT*5))

        # Keep the animation on screen
        self.wait()