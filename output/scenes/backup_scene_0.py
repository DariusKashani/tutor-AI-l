from manim import *
# Added import
from manim import Polygon

class UserAnimationScene(Scene):
    def construct(self):
        # Title text
        title = Text("Simple Triangles", font_size=64, color=ORANGE)
        title.to_edge(UP)
        self.play(Write(title), run_time=2)

        # Create an equilateral triangle
        triangle = Polygon([-1, -1, 0], [1, -1, 0], [0, np.sqrt(3) - 1, 0], color=WHITE)
        triangle.shift(DOWN)
        self.play(Create(triangle), run_time=2)

        # Label sides of the triangle
        labels = VGroup(
            Text("a", color=WHITE).move_to(triangle.get_center() + LEFT * 0.5 + DOWN * 0.3),
            Text("a", color=WHITE).move_to(triangle.get_center() + RIGHT * 0.5 + DOWN * 0.3),
            Text("a", color=WHITE).move_to(triangle.get_center() + UP * 0.8)
        )
        self.play(Write(labels), run_time=2)

        # Show formula for equal sides
        formula = Text("a equals a equals a", color=BLUE)
        formula.next_to(triangle, DOWN)
        self.play(Write(formula), run_time=2)

        # Split the triangle
        line = Line(triangle.get_bottom(), triangle.get_top(), color=RED)
        self.play(Create(line), run_time=2)

        # Label height and base
        height_label = Text("h", color=PURPLE).next_to(line, LEFT)
        base_label = Text("a/2", color=PURPLE).move_to(triangle.get_bottom() + RIGHT * 0.5 + UP * 0.1)
        self.play(Write(height_label), Write(base_label), run_time=2)

        # Show the height formula
        height_formula = Text("h equals sqrt(a^2 - (a/2)^2)", color=GREEN)
        height_formula.next_to(formula, DOWN)
        self.play(Write(height_formula), run_time=2)

        # Draw a checkmark
        checkmark = VMobject()
        checkmark.set_points_as_corners([[0, 0, 0], [0.5, -0.5, 0], [1.5, 1, 0]])
        checkmark.set_color(GREEN)
        checkmark.next_to(height_formula, DOWN)
        self.play(Create(checkmark), run_time=2)