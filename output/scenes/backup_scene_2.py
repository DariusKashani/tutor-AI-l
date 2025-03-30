from manim import *
# Added import
from manim import ThreeDScene
# Added import
from manim import ThreeDObject
# Added import
from manim import Polygon

# Physics compatibility imports
from manim import VGroup, Dot, Line, Circle, Arrow, VMobject, ThreeDObject, Polygon, ThreeDScene

# Define missing physics classes
if 'Pendulum' not in globals():
    class Pendulum(VGroup):
        def __init__(self, length=3, angle=PI/4, weight_diameter=0.5, **kwargs):
            super().__init__(**kwargs)
            self.length = length
            self.angle = angle
            self.weight_diameter = weight_diameter
            self.pivot = Dot(ORIGIN, color=WHITE)
            self.rod = Line(ORIGIN, length * RIGHT, color=GRAY)
            self.rod.rotate(angle, about_point=ORIGIN)
            self.bob = Circle(radius=weight_diameter/2, color=BLUE, fill_opacity=1)
            self.bob.move_to(self.rod.get_end())
            self.add(self.pivot, self.rod, self.bob)
            
        def get_angle(self):
            return self.angle

if 'GravityForce' not in globals():
    class GravityForce(Arrow):
        def __init__(self, obj, length=1, **kwargs):
            super().__init__(obj.get_center(), obj.get_center() + DOWN * length, **kwargs)
            self.add_updater(lambda m: m.put_start_and_end_on(obj.get_center(), obj.get_center() + DOWN * length))

if 'Spring' not in globals():
    class Spring(VMobject):
        def __init__(self, start=ORIGIN, end=RIGHT*3, num_coils=5, radius=0.2, **kwargs):
            super().__init__(**kwargs)
            self.start = start
            self.end = end
            self.num_coils = num_coils
            self.radius = radius
            self.create_spring()
            
        def create_spring(self):
            points = []
            length = np.linalg.norm(self.end - self.start)
            direction = (self.end - self.start) / length
            normal = np.array([-direction[1], direction[0], 0])
            
            # Create coils
            segment_length = length / (2 * self.num_coils + 2)
            points.append(self.start)
            points.append(self.start + direction * segment_length)
            
            for i in range(self.num_coils):
                points.append(self.start + direction * ((2*i+1) * segment_length) + normal * self.radius)
                points.append(self.start + direction * ((2*i+2) * segment_length) - normal * self.radius)
            
            points.append(self.end - direction * segment_length)
            points.append(self.end)
            
            self.set_points_as_corners(points)


class UserAnimationScene(ThreeDScene):
    def construct(self):
        # Create a pyramid with an equilateral triangle base
        pyramid = Pyramid(base_side_length=2, height=2.5, color=BLUE)
        pyramid_text = Text("equal sides for stability", font_size=24).next_to(pyramid, DOWN)

        # Create a tent using isosceles triangle
        tent = Triangle().scale(2)
        tent.set_color(RED)
        tent_text = Text("two sides equal for balance", font_size=24).next_to(tent, DOWN)

        # Positioning pyramid and tent
        pyramid.to_edge(LEFT)
        tent.next_to(pyramid, RIGHT, buff=1)

        # Displaying pyramid and tent
        self.play(Create(pyramid), run_time=3)
        self.wait(0.5)
        self.play(Write(pyramid_text), run_time=2)
        self.wait(0.5)
        self.play(Create(tent), run_time=3)
        self.wait(0.5)
        self.play(Write(tent_text), run_time=2)
        self.wait(0.5)

        # Final text flash
        final_text = Text("Triangles in Real Life", color=YELLOW, font_size=36)
        final_text.to_edge(UP)
        self.play(Flash(final_text), run_time=2)
        self.wait(1)