from manim import *
# Added import
from manim import Polygon

class UserAnimationScene(Scene):
    def construct(self):
        # Einstein at a chalkboard
        einstein = Text("Einstein at a chalkboard", color=WHITE)
        einstein.to_edge(UP)
        self.play(Create(einstein))
        self.wait(5)  # Wait until 3:40

        # Writing E=mc^2
        formula = Text("E=mc²", color=BLUE)
        formula.next_to(einstein, DOWN)
        self.play(Write(formula))
        self.wait(10)  # Wait until 3:50

        # Drawing a right-angle triangle
        triangle = Polygon([-1, -1, 0], [1, -1, 0], [-1, 1, 0], color=GREEN)
        triangle.next_to(formula, DOWN)
        self.play(Create(triangle))
        line1 = Line([-1, -1, 0], [1, -1, 0])
        line2 = Line([-1, -1, 0], [-1, 1, 0])
        right_angle = RightAngle(line1, line2)
        self.play(Create(right_angle))

        # Beam of light
        light_path = VMobject(color=YELLOW)
        light_path.set_points_as_corners([[-1, -1, 0], [1, -1, 0], [-1, 1, 0]])
        beam = Arrow([-1, -1, 0], [1, -1, 0], buff=0, color=YELLOW)
        self.play(MoveAlongPath(beam, light_path), run_time=10)
        self.wait(10)  # Wait until 4:00

        # Space-time diagram
        space_time_diagram = Text("Space-time diagram", color=RED)
        space_time_diagram.to_edge(DOWN)
        self.play(Transform(triangle, space_time_diagram))
        self.wait(20)  # Wait until 4:20

        # Quantum particles
        quantum_particles = Text("Quantum particles", color=PURPLE)
        quantum_particles.move_to(space_time_diagram.get_center())
        self.play(Transform(space_time_diagram, quantum_particles))
        self.wait(20)  # Wait until 4:40

        # Return to geometric plane and triangle
        self.play(Transform(quantum_particles, triangle))
        self.wait(10)  # Hold final scene