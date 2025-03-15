from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create a map background
        map_background = Rectangle(width=config.frame_width, height=config.frame_height, color=BLUE_B)
        map_background.set_fill(BLUE_D, opacity=1)
        self.play(Create(map_background))

        # Define points for the triangle
        p1, p2, p3 = [-4, 1, 0], [3, 2, 0], [-1, -2, 0]

        # Create the triangle
        triangle = Polygon(p1, p2, p3, color=WHITE)
        triangle.set_fill(YELLOW, opacity=0.5)
        self.play(Create(triangle), run_time=3)

        # Label sides and angles
        labels = VGroup(
            Text("A").move_to(p1),
            Text("B").move_to(p2),
            Text("C").move_to(p3)
        )
        self.play(Write(labels), run_time=2)

        # Display text about triangles in navigation
        text = Text("Triangles can help us calculate distances and areas in navigation and geography.", font_size=24)
        text.to_edge(DOWN)
        self.play(Write(text), run_time=2)
        self.wait(2)

        # Animate a plane flying along the triangle
        plane = Triangle().scale(0.2).set_fill(RED, opacity=1)
        plane.move_to(p1)
        path = VMobject()
        path.set_points_as_corners([p1, p2, p3, p1])
        self.play(MoveAlongPath(plane, path), run_time=3)

        # Final wait
        self.wait(2)