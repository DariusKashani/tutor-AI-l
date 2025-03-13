"""
Manim code generator for mathematical animations.
This module handles the creation of Manim animations based on scene descriptions.
"""

import re
import os
import importlib.util
from openai import OpenAI

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load Manim knowledge from the text file
def load_manim_knowledge():
    try:
        with open("manim_knowledge.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        print("Warning: manim_knowledge.txt not found. Using default knowledge base.")
        return """
        Manim is a Python library for creating animations. 
        Key components: mobjects (Circle, Square, Text), scenes (Scene), and animations (Create, Transform).
        """

# Load the knowledge base
MANIM_KNOWLEDGE = load_manim_knowledge()

# Common Manim elements and their creation code
COMMON_ELEMENTS = {
    "triangle": """
        # Create a right triangle
        triangle = Polygon(
            [-2, -1, 0],  # Bottom left
            [2, -1, 0],   # Bottom right
            [2, 2, 0],    # Top right - creates right angle
            color=WHITE,
            stroke_width=2
        )
    """,
    "coordinate_system": """
        # Create a coordinate system
        axes = Axes(
            x_range=[-5, 5, 1],
            y_range=[-3, 3, 1],
            axis_config={"include_tip": True}
        )
    """,
    "formula": """
        # Pythagorean theorem formula
        formula = MathTex(r"a^2 + b^2 = c^2", font_size=36)
    """
}

# Basic template for Manim animations - using named placeholder
BASE_TEMPLATE = """from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Track objects we'll reference later
        objects = {}
        
{animations}
        
        # Final pause
        self.wait(2)
"""

def extract_timing_instructions(scene_description):
    """Extract timing instructions from scene description."""
    # Look for patterns like "At 0:05, draw a triangle"
    timing_pattern = r'At\s+(\d+):(\d+),\s+(.*?)(?=\.\s+At|\.$|$)'
    instructions = re.findall(timing_pattern, scene_description, re.DOTALL)
    
    # If the "At X:XX" format isn't found, try looking for time codes in brackets
    if not instructions:
        timing_pattern = r'\[(\d+):(\d+)\](.*?)(?=\[\d+:\d+\]|\.$|$)'
        instructions = re.findall(timing_pattern, scene_description, re.DOTALL)
    
    # Sort by time
    return sorted(instructions, key=lambda x: (int(x[0]), int(x[1])))

def generate_animation_sequence(instructions):
    """Generate sequential animation code based on timing instructions."""
    code = []
    last_time = (0, 0)  # (minutes, seconds)
    
    for i, (mins, secs, action) in enumerate(instructions):
        current_time = (int(mins), int(secs))
        
        # Calculate wait time from previous instruction
        wait_time = (current_time[0] - last_time[0]) * 60 + (current_time[1] - last_time[1])
        
        # Add comment for this step
        code.append(f"        # At {mins}:{secs} - {action.strip()}")
        
        # Add wait if needed (only after first instruction)
        if i > 0 and wait_time > 0:
            code.append(f"        self.wait({wait_time})  # Wait for {wait_time} seconds")
        
        # Add placeholder for the animation code
        code.append(f"        # TODO: Action - {action.strip()}")
        code.append("")
        
        # Update last time
        last_time = current_time
    
    return "\n".join(code)

def identify_key_elements(scene_description):
    """Identify key elements needed for the animation."""
    elements = []
    
    # Check for common elements in the description
    if re.search(r'triangle|right.angle|pythagorean', scene_description, re.IGNORECASE):
        elements.append("triangle")
    
    if re.search(r'coordinate|plane|axis|axes|graph', scene_description, re.IGNORECASE):
        elements.append("coordinate_system")
        
    if re.search(r'formula|equation|a\s*\^2|a\s*squared|a²', scene_description, re.IGNORECASE):
        elements.append("formula")
        
    return elements

def create_base_code_with_timing(scene_description):
    """Create base Manim code with timing structure."""
    instructions = extract_timing_instructions(scene_description)
    
    if not instructions:
        print("WARNING: No timing instructions found in scene description")
        # Fall back to a basic template
        animation_code = "        # Basic animation\n        title = Text(\"Math Concept\", font_size=48)\n        self.play(Write(title))"
        return BASE_TEMPLATE.format(animations=animation_code)
    
    # Generate the animation sequence
    animation_sequence = generate_animation_sequence(instructions)
    
    # Use named placeholder
    return BASE_TEMPLATE.format(animations=animation_sequence)

def request_manim_code_from_gpt(scene_description, base_code):
    """Request complete Manim animation code from GPT."""
    system_content = f"""You are an expert at creating animations using the Manim library. 
Your task is to implement Manim animation code based on timing instructions from a scene description.

Here is the Manim knowledge base to help you create accurate, working code:

{MANIM_KNOWLEDGE}

Follow these critical requirements:
1. ALWAYS use self.play() for animations, never add objects directly to the scene
2. Keep all objects within the visible frame (-6 to 6 horizontally, -3.5 to 3.5 vertically)
3. Use appropriate font sizes for text (24-36 pt)
4. DO NOT add additional wait() calls beyond those already in the template
5. Implement animations SEQUENTIALLY at the exact times specified
6. Keep animations simple and robust - don't try complex techniques

You will be given a scene description and a code template with timing structure.
Implement the animation code for each step keeping the existing comments and wait() calls.
"""

    # Request the completed code from GPT
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"""Here is a scene description with timing instructions:

{scene_description}

I've created a template with the proper timing structure:

{base_code}

Implement the animation code for each step following the instructions in the comments.
DO NOT modify the existing structure or wait times - only add the animation code itself.
Create a COMPLETE, working animation that implements the scene sequentially.

The animation should stay simple and reliable - focus on basic shapes, text, and standard animations
that won't cause errors."""}
            ],
            max_tokens=3000,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error requesting code from GPT: {e}")
        # Return fallback code if the API call fails
        return create_fallback_code(scene_description)

def create_fallback_code(scene_description):
    """Create a fallback animation if the GPT request fails."""
    topic_match = re.search(r'pythagorean theorem|triangle|math concept', scene_description, re.IGNORECASE)
    topic = topic_match.group(0) if topic_match else "Math Concept"
    
    fallback_code = f"""from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Simple fallback animation for "{topic}"
        title = Text("{topic}", font_size=48)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))
        
        # Create a right triangle
        triangle = Polygon(
            [-2, -1, 0], 
            [2, -1, 0], 
            [2, 2, 0], 
            color=WHITE
        )
        self.play(Create(triangle))
        self.wait(1)
        
        # Label the sides
        a_label = Text("a", font_size=36).next_to(triangle, LEFT)
        b_label = Text("b", font_size=36).next_to(triangle, DOWN)
        c_label = Text("c", font_size=36).next_to(triangle, UP+RIGHT)
        self.play(Write(a_label), Write(b_label), Write(c_label))
        self.wait(1)
        
        # Show formula
        formula = MathTex(r"a^2 + b^2 = c^2", font_size=36).to_edge(DOWN)
        self.play(Write(formula))
        
        # Final pause
        self.wait(2)
"""
    return fallback_code

def inspect_code_for_issues(code):
    """Check for common issues in the generated Manim code."""
    issues = []
    
    # Check for wrong inheritance
    if not re.search(r'class\s+UserAnimationScene\s*\(\s*Scene\s*\)', code):
        issues.append("Class must be named 'UserAnimationScene' and inherit from 'Scene'")
    
    # Check for constructor
    if not re.search(r'def\s+construct\s*\(\s*self\s*\)', code):
        issues.append("Missing 'construct' method")
    
    # Check for missing imports
    if not code.startswith('from manim import'):
        issues.append("Missing Manim imports")
    
    # Check for unusually large coordinates (might be off-screen)
    large_coords = re.findall(r'\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)', code)
    for coords in large_coords:
        if any(abs(float(c)) > 10 for c in coords if c):
            issues.append("Found coordinates that may be off-screen")
            break
    
    # Check for too many wait() calls
    wait_count = len(re.findall(r'self\.wait\s*\(', code))
    if wait_count > 15:  # Arbitrary threshold
        issues.append(f"Excessive wait() calls ({wait_count})")
    
    return issues

def fix_common_code_issues(code):
    """Fix common issues in the generated code."""
    # Ensure proper imports
    if not code.startswith('from manim import *'):
        code = 'from manim import *\n\n' + code
    
    # Fix class definition if needed
    if not re.search(r'class\s+UserAnimationScene\s*\(\s*Scene\s*\)', code):
        code = re.sub(r'class\s+\w+\s*\([^)]*\)', 'class UserAnimationScene(Scene)', code)
    
    # Fix construct method if needed
    if not re.search(r'def\s+construct\s*\(\s*self\s*\)', code):
        code = re.sub(r'def\s+\w+\s*\(\s*self\s*\)', 'def construct(self)', code)
    
    # Limit coordinates to safe values
    code = re.sub(r'\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]', 
                 lambda m: f'[{min(max(float(m.group(1)), -7), 7)}, {min(max(float(m.group(2)), -4), 4)}, {m.group(3)}]', 
                 code)
    
    # Add final wait if missing
    if not re.search(r'self\.wait\s*\(\s*[1-9]\s*\)\s*$', code):
        # Find the end of the construct method
        method_end = re.search(r'def\s+construct\s*\(\s*self\s*\).*?(\n\s*\n|\Z)', code, re.DOTALL)
        if method_end:
            # Insert before the end of the method
            insert_pos = method_end.end()
            code = code[:insert_pos] + '\n        # Final pause\n        self.wait(2)\n' + code[insert_pos:]
        else:
            # Append at the end if we can't find the method end
            code = code.rstrip() + '\n        # Final pause\n        self.wait(2)\n'
    
    return code

def generate_manim_code(scene_description):
    """
    Generate Manim animation code based on a scene description.
    This is the main function that should be called from outside this module.
    
    Args:
        scene_description: Detailed description with timing instructions
        
    Returns:
        Python code for a Manim animation
    """
    print(f"Generating Manim code for scene: {scene_description[:100]}...")
    
    # Create base code with proper timing structure
    base_code = create_base_code_with_timing(scene_description)
    
    # Request completed code from GPT
    completed_code = request_manim_code_from_gpt(scene_description, base_code)
    
    # Check for issues
    issues = inspect_code_for_issues(completed_code)
    if issues:
        print(f"Found {len(issues)} potential issues in generated code:")
        for issue in issues:
            print(f"- {issue}")
        
        # Fix issues
        fixed_code = fix_common_code_issues(completed_code)
        
        # Verify fixes
        remaining_issues = inspect_code_for_issues(fixed_code)
        if remaining_issues:
            print(f"After fixes, {len(remaining_issues)} issues remain:")
            for issue in remaining_issues:
                print(f"- {issue}")
            
            # If critical issues remain, use fallback
            if any("UserAnimationScene" in issue or "construct" in issue or "import" in issue for issue in remaining_issues):
                print("Critical issues remain. Using fallback code.")
                return create_fallback_code(scene_description)
            
        return fixed_code
    
    # Final safety check - if code seems problematic, use fallback
    if "UserAnimationScene" not in completed_code or "def construct" not in completed_code:
        print("WARNING: Generated code appears invalid, using fallback")
        return create_fallback_code(scene_description)
    
    return completed_code

# Additional utility functions

def extract_scene_topic(scene_description):
    """Extract the main topic of a scene."""
    # Look for specific math topics
    topics = ["pythagorean theorem", "triangle", "geometry", "mathematics", 
              "algebra", "calculus", "equation", "formula"]
    
    for topic in topics:
        if topic in scene_description.lower():
            return topic
    
    # Default topic
    return "mathematical concept"

# For testing directly from this file
if __name__ == "__main__":
    test_description = """
    Let's start with a title screen that displays "Pythagorean Theorem" in large, blue text against a light background. At 0:03, animate the title moving to the top of the screen. At 0:05, draw a right-angled triangle in the center of the screen, with sides of lengths 3 and 4, and hypotenuse 5. Use bright colors: red for the vertical side (labeled 'a=3'), green for the horizontal side (labeled 'b=4'), and blue for the hypotenuse (labeled 'c=5'). At 0:10, highlight the right angle with a small square in the corner. At 0:15, draw three squares growing outward from each side of the triangle - a red square on side 'a', a green square on side 'b', and a blue square on side 'c'.
    """
    
    code = generate_manim_code(test_description)
    
    # Save to a file for testing
    with open("test_animation.py", "w") as f:
        f.write(code)
    
    print("Test animation code saved to test_animation.py")