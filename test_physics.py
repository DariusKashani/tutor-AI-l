from manim import *
from manim_physics import *

class PendulumScene(Scene):
    def construct(self):
        # Create a pendulum
        pendulum = Pendulum(
            angle=PI/4,  # Initial angle
            length=3,    # Length of the pendulum
            top_point=ORIGIN,  # Pivot point
            weight_diameter=0.5  # Size of the bob
        )
        
        # Set up the scene
        title = Text("Testing Manim-Physics", font_size=36)
        title.to_edge(UP)
        
        # Add elements to the scene
        self.play(Write(title))
        self.play(Create(pendulum))
        
        # Add gravity to the pendulum
        self.play(pendulum.start_swinging())
        
        # Let it swing for a few seconds
        self.wait(5)
        
        # Stop the animation
        self.play(pendulum.stop_swinging())
        
        # Fade out
        self.play(FadeOut(pendulum), FadeOut(title))
        
        # Final message
        success = Text("Manim-Physics Works!", font_size=48, color=GREEN)
        self.play(Write(success))
        self.wait(2)

if __name__ == "__main__":
    print("Rendering PendulumScene...") 