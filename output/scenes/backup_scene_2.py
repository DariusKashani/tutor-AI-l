from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create the ladder, wall, and ground
        wall = Line(ORIGIN, UP * 4, color=BLUE)
        ground = Line(ORIGIN, RIGHT * 5, color=GREEN)
        ladder = Line(ORIGIN, RIGHT * 3 + UP * 4, color=RED)
        right_angle = RightAngle(ground, wall)

        # Create the triangle and labels
        triangle = VGroup(wall, ground, ladder, right_angle)
        labels = VGroup(
            Text("20 ft", color=BLUE).next_to(wall, LEFT),
            Text("25 ft", color=RED).move_to(ladder.get_center() + LEFT * 0.5),
            Text("x ft", color=GREEN).next_to(ground, DOWN)
        )

        # Display the triangle and labels
        self.play(Create(triangle), Write(labels))
        self.wait(3)

        # Overlay the Pythagorean theorem
        theorem = Text("a² + b² = c²").to_edge(UP)
        self.play(Write(theorem))
        self.wait(2)

        # Substitute the values
        values = Text("20² + x² = 25²").move_to(theorem.get_center())
        self.play(Transform(theorem, values))
        self.wait(2)

        # Show the calculated ground distance
        ground_distance = Text("x = 15 ft").next_to(ground, DOWN)
        self.play(Transform(labels[2], ground_distance))
        self.wait(6)

        # Animate a safety warning about the correct angle for ladder placement
        safety_warning = Text("Ensure correct angle for safety!", color=YELLOW).to_edge(DOWN)
        self.play(Write(safety_warning))
        self.wait(4)

        # Show a montage of triangles in various contexts
        montage_texts = [
            Text("Architecture").to_corner(UL),
            Text("Navigation").to_corner(UR),
            Text("Physics").to_corner(DR)
        ]
        montage = VGroup(*montage_texts)
        self.play(LaggedStart(*[Write(text) for text in montage_texts], lag_ratio=0.5))
        self.wait(4)