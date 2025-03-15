from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create the wall, ladder, and ground
        wall = Line(ORIGIN, 3 * UP, color=BLUE)
        ground = Line(ORIGIN, 5 * RIGHT, color=GREEN)
        ladder = Line(ORIGIN, 5 * RIGHT + 3 * UP, color=RED)

        # Labels for the wall and ladder
        wall_label = Text("10 feet", color=BLUE).next_to(wall, LEFT)
        ladder_label = Text("26 feet", color=RED).next_to(ladder.get_center(), RIGHT, buff=0.1)
        ground_label = Text("x feet", color=GREEN).next_to(ground, DOWN)

        # Right angle indication
        right_angle = RightAngle(ground, wall, length=0.5, color=WHITE)

        # Create and position the formula text
        formula = Text("a² + b² = c²").to_edge(UP)
        substituted_formula = Text("10² + x² = 26²").next_to(formula, DOWN)

        # Safety warning text
        safety_warning = Text("Ensure correct ladder angle for safety!", color=YELLOW).to_edge(DOWN)

        # Montage text
        montage_text = Text("Applications: Construction, Navigation, Computer Graphics", color=PURPLE).to_edge(DOWN)

        # Animations
        self.play(Create(wall), Create(ground), Create(ladder))
        self.play(Write(wall_label), Write(ground_label), Write(ladder_label))
        self.play(Create(right_angle))
        self.wait(10)  # Wait until 2:15

        self.play(Write(formula))
        self.wait(5)  # Wait until 2:20

        self.play(Transform(ground_label, Text("24 feet", color=GREEN).next_to(ground, DOWN)))
        self.play(ReplacementTransform(formula, substituted_formula))
        self.wait(30)  # Wait until 2:50

        self.play(Write(safety_warning))
        self.wait(10)  # Wait until 3:00

        self.play(ReplacementTransform(safety_warning, montage_text))
        self.wait(10)  # Hold final scene