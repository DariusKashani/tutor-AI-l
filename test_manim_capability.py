#!/usr/bin/env python3
"""
Test script to check Manim video generation capability.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.resolve()
sys.path.append(str(project_root))

# Import project modules
from src.backend.video_generator import verify_manim_installation
from config import get_project_dirs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('manim_test')

def create_test_scene():
    """Create a test scene file."""
    output_dirs = get_project_dirs(create_dirs=True)
    scene_file = Path(output_dirs["scenes"]) / "test_scene.py"
    
    scene_code = """
from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create shapes
        circle = Circle(color=BLUE)
        square = Square(color=RED)
        triangle = Polygon([-1, -1, 0], [1, -1, 0], [0, 1, 0], color=GREEN)
        
        # Position shapes
        shapes = VGroup(circle, square, triangle).arrange(RIGHT, buff=0.5)
        
        # Create animations
        self.play(Create(shapes), run_time=2)
        self.wait(1)
        
        # Animate shapes
        self.play(
            circle.animate.scale(0.5),
            square.animate.rotate(PI/4),
            triangle.animate.shift(UP*0.5)
        )
        self.wait(1)
        
        # Add text
        text = Text("Manim Test Successful", color=YELLOW).to_edge(UP)
        self.play(Write(text))
        self.wait(2)
"""
    
    scene_file.parent.mkdir(parents=True, exist_ok=True)
    scene_file.write_text(scene_code)
    logger.info(f"Created test scene at {scene_file}")
    return scene_file

def main():
    """Run the Manim capability test."""
    print("\n=== Manim Capability Test ===\n")
    
    # Step 1: Check Manim Installation
    if not verify_manim_installation():
        print("\n❌ Manim installation check failed. Please check the logs for details.")
        return False
    
    print("\n✅ Manim installation verified")
    
    try:
        # Step 2: Create test scene
        scene_file = create_test_scene()
        print(f"\n✅ Created test scene at: {scene_file}")
        
        # Step 3: Render the scene
        from backend.generate_scenes import render_manim_scenes
        output_dirs = get_project_dirs(create_dirs=True)
        video_files = render_manim_scenes([str(scene_file)], output_dirs["videos"])
        
        if video_files:
            print(f"\n✅ Successfully rendered test video to: {video_files[0]}")
            return True
        else:
            print("\n❌ Failed to render test video. Check the logs for details.")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        logger.exception("Test failed with error")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 