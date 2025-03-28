"""
Manim code generator for mathematical animations.
This module handles the creation of Manim animations based on scene descriptions.
"""

import os
import sys
import re
import json
import time
import random
import string
import shutil
import subprocess
import glob
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ---------------------------
# Update Python Path and Load Config
# ---------------------------
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

from config import MANIM_KNOWLEDGE_PATH, get_scene_path
import config  # For additional configuration functions

# Import the generative-manim integration
try:
    from src.backend.generative_manim_integration import generate_manim_code_with_generative_manim
    generative_manim_available = True
except ImportError:
    generative_manim_available = False

# ---------------------------
# OpenAI and Logging Setup
# ---------------------------
try:
    from openai import OpenAI
except ImportError:
    raise ImportError("OpenAI package not found.")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler(LOG_DIR / "manim_generator.log")
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# ---------------------------
# Global Manim Knowledge
# ---------------------------
def load_manim_knowledge() -> str:
    """Load Manim knowledge from the knowledge file."""
    try:
        logger.info(f"Loading Manim knowledge from: {MANIM_KNOWLEDGE_PATH}")
        if os.path.exists(MANIM_KNOWLEDGE_PATH):
            with open(MANIM_KNOWLEDGE_PATH, 'r') as f:
                knowledge = f.read()
            logger.info(f"Loaded {len(knowledge)} bytes of knowledge")
            return knowledge
        else:
            logger.warning(f"Manim knowledge file not found at {MANIM_KNOWLEDGE_PATH}")
            return ""
    except Exception as e:
        logger.error(f"Error loading Manim knowledge: {e}")
        return ""

MANIM_KNOWLEDGE = load_manim_knowledge()

# ---------------------------
# Base Template for Animations
# ---------------------------
BASE_TEMPLATE = """from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Track objects for reference
        objects = {{}}
        
{animations}
        
        # Final pause
        self.wait(2)
"""

# ---------------------------
# Utility Functions
# ---------------------------
def verify_manim_installation() -> tuple:
    """Verify that Manim is installed and working."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import manim"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error("Manim import failed: " + result.stderr)
            return False, result.stderr
        logger.info("Manim import successful")
        return True, "Manim is installed"
    except Exception as e:
        logger.error(f"Error verifying Manim installation: {e}")
        return False, str(e)

def extract_timing_instructions(scene_description: str) -> list:
    """Extract timing instructions from the scene description."""
    timing_pattern = r'At\s+(\d+):(\d+),\s+(.*?)(?=\.\s+At|\.$|$)'
    instructions = re.findall(timing_pattern, scene_description, re.DOTALL)
    if not instructions:
        timing_pattern = r'\[(\d+):(\d+)\](.*?)(?=\[\d+:\d+\]|\.$|$)'
        instructions = re.findall(timing_pattern, scene_description, re.DOTALL)
    return sorted(instructions, key=lambda x: (int(x[0]), int(x[1])))

def generate_animation_sequence(instructions: list) -> str:
    """Generate sequential animation code based on timing instructions."""
    code_lines = []
    last_time = (0, 0)
    for i, (mins, secs, action) in enumerate(instructions):
        current_time = (int(mins), int(secs))
        wait_time = (current_time[0] - last_time[0]) * 60 + (current_time[1] - last_time[1])
        code_lines.append(f"        # At {mins}:{secs} - {action.strip()}")
        if i > 0 and wait_time > 0:
            code_lines.append(f"        self.wait({wait_time})  # Wait for {wait_time} seconds")
        code_lines.append(f"        # TODO: Action - {action.strip()}\n")
        last_time = current_time
    return "\n".join(code_lines)

def create_base_code_with_timing(scene_description: str) -> str:
    """Create base Manim code with timing structure from the scene description."""
    instructions = extract_timing_instructions(scene_description)
    if not instructions:
        logger.warning("No timing instructions found; using basic animation template.")
        animation_code = ("        # Basic animation\n"
                          "        title = Text(\"Math Concept\", font_size=48)\n"
                          "        self.play(Write(title))")
        return BASE_TEMPLATE.replace("{animations}", animation_code)
    animation_sequence = generate_animation_sequence(instructions)
    return BASE_TEMPLATE.replace("{animations}", animation_sequence)

def request_manim_code_from_gpt(scene_description: str, base_code: str) -> str:
    """Request complete Manim animation code from OpenAI GPT."""
    system_prompt = (
        "You are an expert at creating animations using the Manim library for math education. "
        "Implement Manim animation code based on the given scene description and timing instructions.\n\n"
        "CRITICAL REQUIREMENTS:\n"
        "1. Start with 'from manim import *'\n"
        "2. The class must be named UserAnimationScene and inherit from Scene\n"
        "3. The construct method must be defined and use self.play() for all animations\n"
        "4. All objects must be created before use and remain within visible bounds (-6 to 6 horizontal, -3.5 to 3.5 vertical)\n"
        "5. Do not include any explanations, only return the Python code."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Create a Manim visualization for the following scene:\n\n{scene_description}\n\n"
                    f"Here is the base template with timing structure:\n\n{base_code}\n\n"
                    "Return only the complete Python code without markdown formatting."
                )}
            ],
            max_tokens=2500,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error requesting code from GPT: {e}")
        return ""

def create_fallback_code(scene_description: str) -> str:
    """Generate fallback Manim code when API generation fails."""
    logger.info("Using fallback code generation due to API error")
    topic = extract_scene_topic(scene_description)
    # Escape any single quotes in the topic to avoid syntax errors
    safe_topic = topic.replace("'", "\\'")
    return f"""from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        title = Text('Scene Generation Fallback', color=RED)
        self.play(Write(title))
        self.wait(1)
        explanation = Text('Unable to generate custom animation', color=WHITE, font_size=24)
        explanation.next_to(title, DOWN)
        self.play(FadeIn(explanation))
        self.wait(1)
        scene_topic = Text('{safe_topic}', color=BLUE, font_size=30)
        scene_topic.next_to(explanation, DOWN, buff=0.5)
        self.play(Create(scene_topic))
        self.wait(2)
        circle = Circle(color=BLUE)
        square = Square(color=RED)
        square.next_to(circle, RIGHT)
        self.play(Create(circle), run_time=1)
        self.play(Create(square), run_time=1)
        self.play(circle.animate.scale(0.5), square.animate.scale(0.5))
        self.wait(1)
        desc = Text('Scene description preview:', color=YELLOW, font_size=20)
        desc.to_edge(DOWN, buff=1.5)
        self.play(Write(desc))
        short_desc = Text('Description preview unavailable', color=GREEN, font_size=18)
        short_desc.next_to(desc, DOWN)
        self.play(Write(short_desc))
        self.wait(2)
"""

def inspect_code_for_issues(code: str) -> list:
    """Check the generated Manim code for common issues."""
    issues = []
    if not re.search(r'class\s+UserAnimationScene\s*\(\s*Scene\s*\)', code):
        issues.append("Class must be named 'UserAnimationScene' and inherit from 'Scene'")
    if not re.search(r'def\s+construct\s*\(\s*self\s*\)', code):
        issues.append("Missing 'construct' method")
    if not code.startswith('from manim import'):
        issues.append("Missing Manim import")
    large_coords = re.findall(r'\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)', code)
    for coords in large_coords:
        if any(abs(float(c)) > 10 for c in coords if c):
            issues.append("Found coordinates that may be off-screen")
            break
    wait_count = len(re.findall(r'self\.wait\s*\(', code))
    if wait_count > 15:
        issues.append(f"Excessive wait() calls ({wait_count})")
    return issues

def fix_common_code_issues(code: str) -> str:
    """Fix common issues in the generated code."""
    if not code.startswith('from manim import *'):
        code = 'from manim import *\n\n' + code
    if not re.search(r'class\s+UserAnimationScene\s*\(\s*Scene\s*\)', code):
        code = re.sub(r'class\s+\w+\s*\([^)]*\)', 'class UserAnimationScene(Scene)', code)
    if not re.search(r'def\s+construct\s*\(\s*self\s*\)', code):
        code = re.sub(r'def\s+\w+\s*\(\s*self\s*\)', 'def construct(self)', code)
    code = re.sub(
        r'\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]',
        lambda m: f'[{min(max(float(m.group(1)), -7), 7)}, {min(max(float(m.group(2)), -4), 4)}, {m.group(3)}]',
        code
    )
    if not re.search(r'self\.wait\s*\(\s*[1-9]\s*\)\s*$', code):
        method_end = re.search(r'(def\s+construct\s*\(.*?\):)(.*)', code, re.DOTALL)
        if method_end:
            code = method_end.group(1) + method_end.group(2) + '\n        self.wait(2)\n'
        else:
            code = code.rstrip() + '\n        self.wait(2)\n'
    return code

def add_compatibility_imports() -> str:
    """Generate compatibility imports for common Manim errors."""
    return """
# Compatibility imports for different Manim versions
if 'ShowCreation' not in globals():
    ShowCreation = Create  # Updated name in newer Manim versions

if 'FRAME_WIDTH' not in globals():
    FRAME_WIDTH = config.frame_width  # Updated in newer Manim versions
    FRAME_HEIGHT = config.frame_height

# Add missing shapes/objects that might be referenced
if 'Checkmark' not in globals():
    class Checkmark(VMobject):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_points_as_corners([
                UP + LEFT, DOWN, RIGHT + UP,
            ])
            self.scale(0.5)

if 'Pyramid' not in globals():
    class Pyramid(ThreeDObject):
        def __init__(self, base_side_length=2, height=3, color=BLUE, **kwargs):
            super().__init__(**kwargs)
            self.base_side_length = base_side_length
            self.height = height
            self.set_color(color)
            self.create_pyramid()
            
        def create_pyramid(self):
            # Create square base
            base = Square(side_length=self.base_side_length)
            base.rotate(PI/4, axis=UP)  # Rotate to diamond shape
            
            # Create apex point
            apex = Dot3D(point=OUT * self.height)
            
            # Create triangular faces
            square_vertices = base.get_vertices()
            self.add(base)
            
            for i in range(4):
                face = Polygon(
                    square_vertices[i],
                    square_vertices[(i+1) % 4],
                    apex.get_center(),
                    color=self.color,
                    fill_opacity=0.7
                )
                self.add(face)
"""

def clean_api_response_code(raw_code: str) -> str:
    """
    Extract clean Python code from API response.
    
    Args:
        raw_code: Raw code text from API.
        
    Returns:
        Cleaned code string.
    """
    logger.info("Cleaning API response code")
    if not raw_code or not raw_code.strip():
        logger.warning("Empty API response")
        return ""
    if raw_code.strip().startswith('{') and raw_code.strip().endswith('}'):
        try:
            response_json = json.loads(raw_code)
            if 'code' in response_json:
                raw_code = response_json['code']
                logger.info("Extracted code from JSON response")
        except json.JSONDecodeError:
            pass
    code_regex = r"```(?:python)?(.*?)```"
    code_matches = re.findall(code_regex, raw_code, re.DOTALL)
    if code_matches:
        logger.info("Found code blocks in API response")
        code = ""
        for match in code_matches:
            if "class" in match and "Scene" in match:
                code = match
                break
        if not code:
            code = code_matches[0]
        
        # Add compatibility imports to the code
        compatibility_imports = add_compatibility_imports()
        if "from manim import *" in code:
            code = code.replace("from manim import *", f"from manim import *\n{compatibility_imports}")
        else:
            # If for some reason the import line is missing, add it at the beginning
            code = f"from manim import *\n{compatibility_imports}\n{code}"
            
        return code.strip()
    
    if "class" in raw_code and "Scene" in raw_code:
        code = raw_code.strip()
        
        # Add compatibility imports to the code
        compatibility_imports = add_compatibility_imports()
        if "from manim import *" in code:
            code = code.replace("from manim import *", f"from manim import *\n{compatibility_imports}")
        else:
            # If for some reason the import line is missing, add it at the beginning
            code = f"from manim import *\n{compatibility_imports}\n{code}"
            
        return code
        
    logger.warning("Could not extract valid code from API response")
    return raw_code.strip()

def extract_scene_topic(scene_description: str) -> str:
    """Extract a concise topic from the scene description."""
    try:
        first_sentence = scene_description.split('.')[0]
        return (first_sentence[:30] + "...") if len(first_sentence) > 30 else first_sentence
    except Exception:
        return "Mathematical Animation"

def clean_existing_scene_file(file_path: str) -> bool:
    """
    Clean a scene file to fix common issues.
    
    Args:
        file_path: Path to the scene file.
        
    Returns:
        True if cleaning was successful, False otherwise.
    """
    try:
        logger.info(f"Cleaning scene file: {file_path}")
        with open(file_path, 'r') as f:
            content = f.read()
        if "from manim import *" not in content:
            content = "from manim import *\n" + content
            logger.info("Added missing Manim import")
        content = re.sub(r"```python\s*", "", content)
        content = re.sub(r"```\s*", "", content)
        class_match = re.search(r"class\s+(\w+)\s*\(([^)]*)\):", content)
        if class_match:
            class_name = class_match.group(1)
            parent_class = class_match.group(2)
            if "Scene" not in parent_class:
                content = content.replace(f"class {class_name}({parent_class}):",
                                          f"class {class_name}(Scene):")
                logger.info(f"Fixed class inheritance for {class_name}")
        construct_match = re.search(r"def\s+construct\s*\(([^)]*)\):", content)
        if construct_match:
            params = construct_match.group(1).strip()
            if not params or "self" not in params:
                content = content.replace("def construct():", "def construct(self):")
                logger.info("Fixed missing self parameter in construct method")
        with open(file_path, 'w') as f:
            f.write(content)
        logger.info(f"Scene file cleaned successfully: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error cleaning scene file: {e}")
        return False

def render_scene(scene_file_path: str, output_file_path: str = None) -> str:
    """
    Render a Manim scene from a Python file.
    
    Args:
        scene_file_path: Path to the scene file.
        output_file_path: Optional output file path.
        
    Returns:
        Path to the rendered video file, or None if failed.
    """
    try:
        logger.info(f"Rendering scene from {scene_file_path}")
        if not os.path.exists(scene_file_path):
            logger.error(f"Scene file does not exist: {scene_file_path}")
            return None
        with open(scene_file_path, 'r') as f:
            content = f.read()
        class_match = re.search(r"class\s+(\w+)\s*\([^)]*Scene[^)]*\):", content)
        if class_match:
            scene_class = class_match.group(1)
            logger.info(f"Found scene class: {scene_class}")
        else:
            logger.error("Could not find Scene class in file")
            return None

        cmd = [
            sys.executable, "-m", "manim",
            scene_file_path, scene_class,
            "-q", "h", "--format", "mp4"
        ]
        if output_file_path:
            output_dir = os.path.dirname(output_file_path)
            if output_dir:
                cmd.extend(["-o", os.path.basename(output_file_path)])
        logger.info(f"Running command: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(scene_file_path)
        )
        if process.returncode != 0:
            logger.error(f"Manim rendering failed: {process.stderr}")
            return None
        logger.info("Rendering completed successfully")
        output_path_match = re.search(r"File written to\s+([^\n]+)", process.stdout)
        if output_path_match:
            rendered_file = output_path_match.group(1).strip()
            logger.info(f"Rendered file path: {rendered_file}")
            if output_file_path and rendered_file != output_file_path:
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                shutil.move(rendered_file, output_file_path)
                return output_file_path
            return rendered_file
        media_dir = os.path.join(os.path.dirname(scene_file_path), "media")
        video_files = []
        for root, _, files in os.walk(media_dir):
            for file in files:
                if file.endswith(".mp4") and scene_class in file:
                    video_files.append(os.path.join(root, file))
        if video_files:
            video_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            logger.info(f"Found rendered file by search: {video_files[0]}")
            if output_file_path and video_files[0] != output_file_path:
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                shutil.move(video_files[0], output_file_path)
                return output_file_path
            return video_files[0]
        logger.error("Could not find rendered video file")
        return None
    except Exception as e:
        logger.error(f"Error rendering scene: {e}")
        return None

# ---------------------------
# Code Validation and Fixing
# ---------------------------
def validate_and_fix_manim_code(code: str) -> str:
    """
    Validate Manim code for common errors and fix them.
    
    Args:
        code: The Manim code to validate and fix.
        
    Returns:
        Fixed Manim code.
    """
    logger.info("Validating and fixing Manim code")
    fixed_code = code
    
    # Fix 1: Replace ShowCreation() with Create()
    if "ShowCreation" in fixed_code and "ShowCreation = Create" not in fixed_code:
        fixed_code = fixed_code.replace("ShowCreation(", "Create(")
        logger.info("Fixed: Replaced ShowCreation with Create")
    
    # Fix 2: Replace FRAME_WIDTH with config.frame_width
    if "FRAME_WIDTH" in fixed_code and "FRAME_WIDTH = config.frame_width" not in fixed_code:
        fixed_code = fixed_code.replace("FRAME_WIDTH", "config.frame_width")
        logger.info("Fixed: Replaced FRAME_WIDTH with config.frame_width")
    
    # Fix 3: Check for ThreeDScene but using 3D objects
    if "ThreeDObject" in fixed_code and "class UserAnimationScene(Scene)" in fixed_code:
        fixed_code = fixed_code.replace("class UserAnimationScene(Scene)", "class UserAnimationScene(ThreeDScene)")
        logger.info("Fixed: Changed Scene to ThreeDScene for 3D objects")
    
    # Fix 4: Check for physics objects
    physics_classes = ["GravityForce", "Pendulum", "Spring", "Pyramid", "Wave", "ArrowVectorField"]
    if any(cls in fixed_code for cls in physics_classes) and "class UserAnimationScene(Scene)" in fixed_code:
        fixed_code = fixed_code.replace("class UserAnimationScene(Scene)", "class UserAnimationScene(ThreeDScene)")
        logger.info("Fixed: Changed Scene to ThreeDScene for physics simulation")
        
        # Add imports for missing physics classes
        physics_imports = """
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
"""
        if "from manim import *" in fixed_code and "# Physics compatibility imports" not in fixed_code:
            fixed_code = fixed_code.replace("from manim import *", f"from manim import *\n{physics_imports}")
            logger.info("Fixed: Added physics compatibility classes")
    
    # Fix 5: Check for imports
    required_imports = {
        "Polygon": "from manim import Polygon",
        "ThreeDObject": "from manim import ThreeDObject",
        "ThreeDScene": "from manim import ThreeDScene"
    }
    
    for symbol, import_statement in required_imports.items():
        if symbol in fixed_code and import_statement not in fixed_code and f"from manim import {symbol}" not in fixed_code:
            # Add the import after the main manim import
            if "from manim import *" in fixed_code:
                fixed_code = fixed_code.replace("from manim import *", f"from manim import *\n# Added import\n{import_statement}")
            else:
                fixed_code = f"{import_statement}\n{fixed_code}"
            logger.info(f"Fixed: Added missing import for {symbol}")
    
    return fixed_code

# ---------------------------
# Function: Generate Manim Code
# ---------------------------
def generate_manim_code(scene_description: str, scene_index: int = 0, output_dirs: dict = None, dry_run: bool = False) -> str:
    """
    Generate Manim code for a given scene description.
    
    Args:
        scene_description: The scene description text.
        scene_index: Index of the scene (for naming).
        output_dirs: Dictionary with output directory paths.
        dry_run: If True, skip API call and return fallback code.
        
    Returns:
        Generated Manim code as a string.
    """
    logger.info(f"Generating Manim code for scene {scene_index}: {scene_description[:50]}...")
    
    if dry_run:
        logger.info("Dry run mode - returning fallback code")
        return create_fallback_code(scene_description)
    
    # Use generative-manim approach if available
    if generative_manim_available:
        logger.info("Using generative-manim approach for code generation")
        generated_code = generate_manim_code_with_generative_manim(scene_description, scene_index)
        # Apply validation and fixes to the generated code
        return validate_and_fix_manim_code(generated_code)
    
    # Fall back to original approach if generative-manim is not available
    try:
        base_code = create_base_code_with_timing(scene_description)
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": (
                    "You are an expert in creating educational math visualizations with Manim. "
                    "Return ONLY complete, working Python code that starts with 'from manim import *'."
                    f"\n\nMANIM VERSION INFO: You are generating code for Manim Community v0.19.0."
                    "\n\nIMPORTANT NOTES:"
                    "\n1. Use Create() instead of ShowCreation() which is outdated"
                    "\n2. Use config.frame_width instead of FRAME_WIDTH"
                    "\n3. Do not use Checkmark() which is not defined - use custom shapes instead"
                    "\n4. Ensure all objects are created with valid parameters and methods"
                    "\n5. Use Text() instead of Tex() or MathTex() to avoid LaTeX dependencies"
                    f"\n\nMANIM KNOWLEDGE: {MANIM_KNOWLEDGE}"
                )},
                {"role": "user", "content": f"Create a Manim visualization for:\n{scene_description}\n\nTemplate:\n{base_code}"}
            ],
            temperature=0.7,
            max_tokens=2500
        )
        raw_code = response.choices[0].message.content
        logger.info(f"Received response ({len(raw_code)} characters)")
        cleaned_code = clean_api_response_code(raw_code)
        if not cleaned_code:
            logger.error("Failed to extract clean code; using fallback code")
            return create_fallback_code(scene_description)
            
        # Apply validation and fixes to the cleaned code
        fixed_code = validate_and_fix_manim_code(cleaned_code)
        logger.info(f"Generated and fixed Manim code successfully ({len(fixed_code)} characters)")
        return fixed_code
    except Exception as e:
        logger.error(f"Error generating Manim code via API: {e}")
        return create_fallback_code(scene_description)

# ---------------------------
# Testing and Fallback Utilities
# ---------------------------
def extract_scene_topic(scene_description: str) -> str:
    """Extract a short topic from the scene description."""
    try:
        first_sentence = scene_description.split('.')[0]
        return (first_sentence[:30] + "...") if len(first_sentence) > 30 else first_sentence
    except Exception:
        return "Mathematical Animation"

# For testing directly from this module
if __name__ == "__main__":
    from config import get_scene_path
    test_description = (
        "Let's start with a title screen that displays \"Pythagorean Theorem\" in large, blue text against a light background. "
        "At 0:03, animate the title moving to the top of the screen. At 0:05, draw a right-angled triangle in the center of the screen, "
        "with sides of lengths 3 and 4, and hypotenuse 5. Use bright colors: red for the vertical side (labeled 'a=3'), green for the horizontal side (labeled 'b=4'), "
        "and blue for the hypotenuse (labeled 'c=5'). At 0:10, highlight the right angle with a small square in the corner. "
        "At 0:15, draw three squares growing outward from each side of the triangle - a red square on side 'a', a green square on side 'b', and a blue square on side 'c'."
    )
    
    code = generate_manim_code(test_description)
    test_path = get_scene_path(0)
    Path(test_path).parent.mkdir(parents=True, exist_ok=True)
    with open(test_path, "w") as f:
        f.write(code)
    logger.info(f"Test animation code saved to {test_path}")
