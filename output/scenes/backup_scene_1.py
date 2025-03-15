from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create a pyramid with four triangular faces
        pyramid = Pyramid(base_side_length=2, height=3, color=BLUE)
        pyramid.set_fill(BLUE, opacity=0.5)
        self.play(Create(pyramid), run_time=3)
        self.wait(0.5)

        # Zoom in on one face of the pyramid
        face = pyramid.copy().set_fill(YELLOW, opacity=0.8)
        self.play(Transform(pyramid, face), run_time=2)
        self.wait(0.5)

        # Label the base and height of the triangle
        base_label = Text("b", color=RED).next_to(pyramid, DOWN)
        height_label = Text("h", color=GREEN).next_to(pyramid, UP)
        self.play(Write(base_label), Write(height_label), run_time=2)
        self.wait(0.5)

        # Display the formula for the area of a triangle
        area_formula = Text("Area = 1/2 * b * h", color=WHITE).to_edge(DOWN)
        self.play(Write(area_formula), run_time=2)
        self.wait(0.5)

        # Animate a calculation showing the area of the triangular face
        area_calculation = Text("Area = 1/2 * 2 * 3 = 3", color=WHITE).next_to(area_formula, DOWN)
        self.play(Write(area_calculation), run_time=2)
        self.wait(0.5)

        # Zoom out to show the whole pyramid again
        self.play(Transform(pyramid, Pyramid(base_side_length=2, height=3, color=BLUE).set_fill(BLUE, opacity=0.5)), run_time=2)
        self.wait(0.5)

        # Highlight the importance of triangles in architecture
        architecture_text = Text("Triangles in Architecture", color=PURPLE).to_edge(UP)
        self.play(Write(architecture_text), run_time=2)
        self.wait(1)