from manim import *
# Added import
from manim import Polygon

class UserAnimationScene(Scene):
    def construct(self):
        # Title card
        title = Text("Pythagorean Theorem", font="Arial", color=BLACK).scale(1.5)
        title_background = FullScreenRectangle(color=LIGHT_BLUE)
        title_background.set_fill(LIGHT_BLUE, opacity=1)
        self.add(title_background, title)
        self.wait(3)  # Wait until 0:05

        # Subtitle
        subtitle = Text("Understanding Right Triangles", font="Arial", color=BLACK).scale(1.2)
        subtitle.move_to(DOWN)
        self.play(FadeIn(subtitle))
        self.wait(4)  # Wait until 0:12

        # Transition to geometric plane
        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(title_background))
        axes = Axes(x_range=[-1, 5], y_range=[-1, 5], x_length=5, y_length=5)
        self.play(Create(axes))
        self.wait(4)  # Wait until 0:16

        # Draw right-angled triangle
        triangle = Polygon([0, 0, 0], [3, 0, 0], [3, 4, 0], color=BLUE)
        self.play(Create(triangle))
        self.wait(4)  # Wait until 0:20

        # Label sides
        label_a = Text("a", color=BLACK).move_to([1.5, -0.3, 0])
        label_b = Text("b", color=BLACK).move_to([3.3, 2, 0])
        label_c = Text("c", color=BLACK).move_to([1.5, 2, 0])
        self.play(Write(label_a), Write(label_b), Write(label_c))

        # Draw squares on each side
        square_a = Square(side_length=3).move_to([1.5, -1.5, 0], aligned_edge=UP)
        square_b = Square(side_length=4).move_to([4, 2, 0], aligned_edge=LEFT)
        square_c = Square(side_length=5).move_to([1.5, 2, 0])
        square_a.set_style(stroke_color=RED, stroke_opacity=0.5, stroke_width=2, fill_opacity=0)
        square_b.set_style(stroke_color=GREEN, stroke_opacity=0.5, stroke_width=2, fill_opacity=0)
        square_c.set_style(stroke_color=BLUE, stroke_opacity=0.5, stroke_width=2, fill_opacity=0)
        self.play(Create(square_a, run_time=2), Create(square_b, run_time=2), Create(square_c, run_time=2))
        self.wait(10)  # Wait until 0:30

        # Fill in the squares
        square_a.set_fill(RED, opacity=0.5)
        square_b.set_fill(GREEN, opacity=0.5)
        square_c.set_fill(BLUE, opacity=0.5)
        self.play(square_a.animate.set_fill(RED, opacity=0.5),
                  square_b.animate.set_fill(GREEN, opacity=0.5),
                  square_c.animate.set_fill(BLUE, opacity=0.5))
        self.wait(10)  # Wait until 0:40

        # Reveal the general formula
        formula = Text("c² = a² + b²", font="Arial", color=BLACK).scale(1.5)
        formula.to_edge(UP)
        self.play(Write(formula))
        self.wait(10)  # Wait until 0:50

        # Animate the equation
        equation = Text("Area of c² = Area of a² + Area of b²", font="Arial", color=BLACK).scale(1.2)
        equation.next_to(formula, DOWN)
        self.play(Transform(formula, equation))
        self.wait(5)