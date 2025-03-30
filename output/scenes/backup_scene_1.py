from manim import *
# Added import
from manim import Polygon

class UserAnimationScene(Scene):
    def construct(self):
        # Create an isosceles triangle
        triangle = Polygon([-1, -1, 0], [1, -1, 0], [0, 1, 0], color=BLUE)
        self.play(Create(triangle))
        self.wait(2)  # Wait until 0:34

        # Label the sides
        label_b1 = Text("b", color=WHITE).next_to(triangle.get_vertices()[0], LEFT, buff=0.1)
        label_b2 = Text("b", color=WHITE).next_to(triangle.get_vertices()[1], RIGHT, buff=0.1)
        label_a = Text("a", color=WHITE).move_to(triangle.get_bottom() + DOWN * 0.3)
        self.play(Write(label_b1), Write(label_b2), Write(label_a))
        self.wait(3)  # Wait until 0:37

        # Split the triangle and show right-angled triangles
        mid_point = [(triangle.get_vertices()[0][0] + triangle.get_vertices()[1][0]) / 2, -1, 0]
        line = Line(triangle.get_top(), mid_point, color=GREEN)
        self.play(Create(line))
        self.wait(3)  # Wait until 0:40

        # Show height "h" and half base "a/2"
        height = Line(mid_point, triangle.get_top(), color=RED)
        half_base = Line(mid_point, triangle.get_vertices()[1], color=PURPLE)
        label_h = Text("h", color=RED).next_to(height, LEFT, buff=0.1)
        label_a2 = Text("a/2", color=PURPLE).next_to(half_base, DOWN, buff=0.1)
        self.play(Create(height), Create(half_base), Write(label_h), Write(label_a2))

        # Show the formula
        formula = Text("h = √(b² - (a/2)²)", color=YELLOW).to_edge(DOWN)
        self.play(Write(formula))
        self.wait(5)  # Wait until 0:45

        # Animate a checkmark
        checkmark = VMobject()
        checkmark.set_points_as_corners([[0, 0, 0], [0.5, -0.5, 0], [1.5, 1, 0]])
        checkmark.set_color(GREEN).next_to(formula, RIGHT)
        self.play(Create(checkmark))
        self.wait(2)