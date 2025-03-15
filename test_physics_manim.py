from manim import *
from manim_physics.rigid_mechanics.pendulum import Pendulum
from manim_physics.rigid_mechanics.rigid_mechanics import SpaceScene

class PendulumExample(SpaceScene):
    def construct(self):
        # Create a title
        title = Text("Pendulum Example").to_edge(UP)
        self.add(title)
        
        # Create a pendulum with the correct parameters
        pendulum = Pendulum(
            length=3.5,                 # Length of the pendulum
            initial_theta=0.3,          # Initial angle of deviation
            rod_style={
                "stroke_width": 3,
                "stroke_color": WHITE
            },
            bob_style={
                "radius": 0.25,         # Size of the bob
                "color": ORANGE,        # Color of the bob
                "fill_opacity": 1,
            }
        )
        
        # Add the pendulum to the scene
        self.add(pendulum)
        
        # Make the pendulum a rigid body and start the simulation
        self.make_rigid_body(*pendulum.bobs)
        pendulum.start_swinging()
        
        # Add a trace to the pendulum's path
        trace = TracedPath(pendulum.bobs[0].get_center, stroke_color=BLUE)
        self.add(trace)
        
        # Run the simulation for 10 seconds
        self.wait(10)

if __name__ == "__main__":
    print("Running Pendulum Example scene...")
    print("This will simulate a pendulum swinging for 10 seconds.") 