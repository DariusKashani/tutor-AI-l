from manim import *
# Added import
from manim import Polygon

class UserAnimationScene(Scene):
    def construct(self):
        # First triangle setup
        triangle1 = Polygon([0, 0, 0], [5, 0, 0], [5, 12, 0], color=BLUE)
        triangle1.shift(LEFT * 3)
        side_a1 = Text("5", color=WHITE).next_to(triangle1, DOWN, buff=0.1)
        side_b1 = Text("12", color=WHITE).next_to(triangle1, RIGHT, buff=0.1)
        side_c1 = Text("13", color=WHITE).next_to(triangle1, UP, buff=0.1)

        # First Pythagorean theorem demonstration
        equation1 = Text("5² + 12² = 13²", color=YELLOW)
        equation1.shift(UP * 3)
        calc1 = Text("25 + 144 = 169", color=GREEN)
        calc1.next_to(equation1, DOWN)

        # Second triangle setup
        triangle2 = Polygon([0, 0, 0], [7, 0, 0], [7, 24, 0], color=RED)
        triangle2.shift(RIGHT * 3)
        side_a2 = Text("7", color=WHITE).next_to(triangle2, DOWN, buff=0.1)
        side_b2 = Text("24", color=WHITE).next_to(triangle2, RIGHT, buff=0.1)
        side_c2 = Text("25", color=WHITE).next_to(triangle2, UP, buff=0.1)

        # Second Pythagorean theorem demonstration
        equation2 = Text("7² + 24² = 25²", color=YELLOW)
        equation2.next_to(triangle2, UP, buff=0.5)
        calc2 = Text("49 + 576 = 625", color=GREEN)
        calc2.next_to(equation2, DOWN)

        # Checkmark creation
        checkmark = VMobject()
        checkmark.set_points_as_corners([[0, 0, 0], [0.5, -0.5, 0], [1.5, 1, 0]])
        checkmark.set_color(GREEN)
        checkmark.scale(0.5)
        checkmark1 = checkmark.copy().next_to(triangle1, LEFT)
        checkmark2 = checkmark.copy().next_to(triangle2, RIGHT)

        # Animations
        self.play(Create(triangle1), Write(side_a1), Write(side_b1), Write(side_c1))
        self.play(Write(equation1))
        self.wait(5)
        self.play(Write(calc1))
        self.wait(5)
        self.play(Transform(triangle1, triangle2), Transform(side_a1, side_a2), Transform(side_b1, side_b2), Transform(side_c1, side_c2))
        self.play(Write(equation2))
        self.wait(5)
        self.play(Write(calc2))
        self.wait(5)
        self.play(Create(checkmark1), Create(checkmark2))
        self.wait(10)