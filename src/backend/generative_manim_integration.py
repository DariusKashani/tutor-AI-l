"""
Integration with generative-manim for improved Manim code generation.
This module provides functions to use generative-manim's approach for generating Manim code.
"""

import os
import sys
import logging
import json
import subprocess
from pathlib import Path
import shutil

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler(LOG_DIR / "generative_manim_integration.log")
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Update Python Path to Include Project Root
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

# Path to generative-manim directory
GENERATIVE_MANIM_DIR = project_root / "generative-manim"

# Import OpenAI client
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except ImportError:
    logger.error("OpenAI package not found. Please install it with 'pip install openai'.")
    openai_client = None

# Load Manim documentation from generative-manim
def load_manim_docs():
    """Load Manim documentation from generative-manim."""
    try:
        docs_path = GENERATIVE_MANIM_DIR / "api" / "prompts" / "manimDocs.py"
        if docs_path.exists():
            with open(docs_path, 'r') as f:
                content = f.read()
                # Extract the docs string from the Python file
                docs_match = content.split('manimDocs = """', 1)
                if len(docs_match) > 1:
                    docs = docs_match[1].split('"""', 1)[0]
                    logger.info(f"Loaded Manim docs ({len(docs)} characters)")
                    return docs
        logger.warning("Could not load Manim docs from generative-manim")
        return ""
    except Exception as e:
        logger.error(f"Error loading Manim docs: {e}")
        return ""

MANIM_DOCS = load_manim_docs()

def generate_manim_code_with_generative_manim(scene_description: str, scene_index: int = 0) -> str:
    """
    Generate Manim code using the generative-manim approach.
    
    Args:
        scene_description: The scene description text.
        scene_index: Index of the scene (for naming).
        
    Returns:
        Generated Manim code as a string.
    """
    logger.info(f"Generating Manim code for scene {scene_index} using generative-manim approach")
    
    # Prepare the prompt for code generation
    prompt = f"""
Create a Manim animation for the following scene:

{scene_description}

The animation should be educational and visually appealing. 
Make sure to use appropriate colors, timing, and animations to illustrate the concepts clearly.
"""

    # System prompt based on generative-manim's approach
    system_prompt = f"""
You are an expert at creating animations using the Manim library for math education.
Your task is to generate Python code for a Manim animation based on the given description.

CRITICAL REQUIREMENTS:
1. Start with 'from manim import *'
2. The class must be named 'GenScene' and inherit from Scene
3. The construct method must be defined and use self.play() for all animations
4. All objects must be created before use and remain within visible bounds
5. Do not include any explanations, only return the Python code
6. Use Text() instead of Tex() or MathTex() to avoid LaTeX dependencies
7. Use Create() instead of ShowCreation() which is outdated
8. Use config.frame_width instead of FRAME_WIDTH
9. Do not use Checkmark() which is not defined - use custom shapes instead

COMMON ERRORS TO AVOID:
1. RightAngle requires two Line objects, not a Polygon. Example: 
   ```
   line1 = Line([0, 0, 0], [1, 0, 0])
   line2 = Line([0, 0, 0], [0, 1, 0])
   right_angle = RightAngle(line1, line2)
   ```

2. When creating arrows between parts of a Text object, use specific indices:
   ```
   text = Text("a² + b² = c²")
   # Use text[0] for 'a', text[2] for 'b', text[4] for 'c'
   ```

3. When creating a checkmark, use:
   ```
   checkmark = VMobject()
   checkmark.set_points_as_corners([[0, 0, 0], [0.5, -0.5, 0], [1.5, 1, 0]])
   checkmark.set_color(GREEN)
   ```

4. Always position objects explicitly to avoid overlaps:
   ```
   formula.to_edge(DOWN)
   title.to_edge(UP)
   ```

5. For Sector objects, use 'radius' not 'outer_radius':
   ```
   # CORRECT:
   pizza = Sector(radius=2, angle=PI/4, color=ORANGE)
   
   # INCORRECT:
   pizza = Sector(outer_radius=2, angle=PI/4, color=ORANGE)
   ```

6. For Angle objects, use Line objects:
   ```
   # CORRECT:
   angle = Angle(Line(point1, point2), Line(point1, point3))
   
   # INCORRECT:
   angle = Angle(point1, point2, point3)
   ```

{MANIM_DOCS}
"""

    try:
        # Generate code using OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2500
        )
        
        # Extract and clean the code
        raw_code = response.choices[0].message.content
        logger.info(f"Received response ({len(raw_code)} characters)")
        
        # Clean the code (remove markdown formatting if present)
        cleaned_code = raw_code
        if "```python" in raw_code:
            code_parts = raw_code.split("```python", 1)[1].split("```", 1)[0]
            cleaned_code = code_parts.strip()
        elif "```" in raw_code:
            code_parts = raw_code.split("```", 1)[1].split("```", 1)[0]
            cleaned_code = code_parts.strip()
        
        # Ensure the class is named UserAnimationScene for compatibility
        cleaned_code = cleaned_code.replace("class GenScene(Scene):", "class UserAnimationScene(Scene):")
        
        # Post-process the code to fix common issues
        cleaned_code = post_process_code(cleaned_code)
        
        logger.info(f"Generated Manim code successfully ({len(cleaned_code)} characters)")
        return cleaned_code
    except Exception as e:
        logger.error(f"Error generating Manim code: {e}")
        return create_fallback_code(scene_description)

def post_process_code(code: str) -> str:
    """
    Post-process the generated code to fix common issues.
    
    Args:
        code: The generated Manim code.
        
    Returns:
        Fixed Manim code.
    """
    # Fix RightAngle usage with polygons
    if "RightAngle" in code and "Polygon" in code:
        import re
        right_angle_pattern = r"right_angle\s*=\s*RightAngle\s*\(\s*(\w+)\s*,"
        polygon_match = re.search(right_angle_pattern, code)
        if polygon_match:
            polygon_name = polygon_match.group(1)
            if f"{polygon_name} = Polygon" in code:
                # Add lines for the right angle
                lines_code = f"""
        # Create lines for the right angle
        line1 = Line({polygon_name}.get_vertices()[0], {polygon_name}.get_vertices()[1])
        line2 = Line({polygon_name}.get_vertices()[0], {polygon_name}.get_vertices()[2])
        right_angle = RightAngle(line1, line2)
"""
                # Replace the problematic RightAngle line
                code = re.sub(right_angle_pattern + r"[^)]+\)", "# Original right angle code replaced\n" + lines_code, code)
    
    # Fix Sector usage (should use radius instead of outer_radius)
    if "Sector" in code:
        import re
        sector_pattern = r"Sector\s*\(\s*outer_radius\s*=\s*([^,]+)"
        sector_match = re.search(sector_pattern, code)
        if sector_match:
            radius_value = sector_match.group(1)
            code = re.sub(sector_pattern, f"Sector(radius={radius_value}", code)
    
    # Fix Angle usage
    if "Angle" in code:
        import re
        angle_pattern = r"angle_highlight\s*=\s*Angle\s*\(\s*([^,]+),\s*([^,]+),\s*([^,\)]+)"
        angle_match = re.search(angle_pattern, code)
        if angle_match:
            point1 = angle_match.group(1)
            point2 = angle_match.group(2)
            point3 = angle_match.group(3)
            # Replace with correct Angle constructor
            code = re.sub(angle_pattern + r"[^)]*\)", 
                          f"angle_highlight = Angle(Line({point1}, {point2}), Line({point1}, {point3}))", 
                          code)
    
    # Ensure we're using Text instead of Tex
    code = code.replace("Tex(", "Text(")
    code = code.replace("MathTex(", "Text(")
    
    return code

def create_fallback_code(scene_description: str) -> str:
    """Generate fallback Manim code when API generation fails."""
    logger.info("Using fallback code generation")
    
    # Extract a topic from the scene description
    topic = scene_description.split('.')[0][:30] + "..."
    
    # Create a simple animation that doesn't use LaTeX
    return f"""from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create a title
        title = Text("Scene Generation Fallback", color=RED)
        self.play(Write(title))
        self.wait(1)
        
        # Move title to top
        self.play(title.animate.to_edge(UP))
        
        # Show topic
        topic_text = Text("{topic}", color=BLUE, font_size=24)
        self.play(Write(topic_text))
        self.wait(1)
        
        # Create some basic shapes
        circle = Circle(color=BLUE)
        square = Square(color=RED)
        triangle = Polygon([-1, -1, 0], [1, -1, 0], [0, 1, 0], color=GREEN)
        
        # Position shapes
        shapes_group = Group(circle, square, triangle).arrange(RIGHT, buff=0.5)
        self.play(Create(shapes_group), run_time=2)
        self.wait(1)
        
        # Animate shapes
        self.play(
            circle.animate.scale(0.7),
            square.animate.rotate(PI/4),
            triangle.animate.shift(UP*0.5)
        )
        self.wait(2)
"""

# For testing directly from this module
if __name__ == "__main__":
    test_description = (
        "Explain the concept of a right triangle. Show a triangle with sides of length 3, 4, and 5. "
        "Highlight the right angle and demonstrate the Pythagorean theorem by showing that 3² + 4² = 5²."
    )
    
    code = generate_manim_code_with_generative_manim(test_description)
    print(code) 