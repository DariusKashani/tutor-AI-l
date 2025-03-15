from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Title screen
        title = Text("Simple Triangle", font_size=64, color=BLUE)
        title.move_to(ORIGIN)
        self.play(Write(title))
        self.wait(3)  # Wait until 0:05

        # Move title to the top
        self.play(title.animate.to_edge(UP))
        self.wait(2)  # Wait until 0:07

        # Draw triangle
        triangle = Polygon([-3, -2, 0], [3, -2, 0], [0, 2, 0], color=ORANGE)
        self.play(Create(triangle))
        self.wait(3)  # Wait until 0:10

        # Label sides
        labels = VGroup(
            Text("a", color=WHITE).move_to(triangle.get_center() + [-2, 0.5, 0]),
            Text("b", color=WHITE).move_to(triangle.get_center() + [2, 0.5, 0]),
            Text("c", color=WHITE).move_to(triangle.get_center() + [0, -1.5, 0])
        )
        self.play(Write(labels))

        # Highlight corners
        corners = VGroup(
            Dot(triangle.get_vertices()[0], color=YELLOW),
            Dot(triangle.get_vertices()[1], color=YELLOW),
            Dot(triangle.get_vertices()[2], color=YELLOW)
        )
        self.play(FadeIn(corners))
        self.wait(5)  # Wait until 0:15

        # Annotate angles
        angles = VGroup(
            Text("α", color=RED).move_to(triangle.get_vertices()[0] + [-0.5, 0.5, 0]),
            Text("β", color=RED).move_to(triangle.get_vertices()[1] + [0.5, 0.5, 0]),
            Text("γ", color=RED).move_to(triangle.get_vertices()[2] + [0, 1, 0])
        )
        self.play(Write(angles))
        self.wait(5)  # Wait until 0:20

        # Sum of angles statement
        angle_sum = Text("The sum of the angles of a triangle always equals 180 degrees", color=GREEN)
        angle_sum.to_edge(DOWN)
        self.play(Write(angle_sum))
        self.wait(5)  # Wait until 0:25

        # Animate angles adding up
        angle_line = Line([-3, -3, 0], [3, -3, 0], color=RED)
        self.play(Transform(angles, angle_line))
        self.wait(5)  # Wait until 0:30

        # Transition to a more complex triangle example
        complex_triangle = Polygon([-2, -1, 0], [2, -1, 0], [1, 2, 0], color=PURPLE)
        self.play(ReplacementTransform(triangle, complex_triangle))
        self.play(ReplacementTransform(labels, VGroup(
            Text("d", color=WHITE).move_to(complex_triangle.get_center() + [-1, 0.5, 0]),
            Text("e", color=WHITE).move_to(complex_triangle.get_center() + [1, 0.5, 0]),
            Text("f", color=WHITE).move_to(complex_triangle.get_center() + [0, -1.5, 0])
        )))
        self.wait(2)  # Hold final scene