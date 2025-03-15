from dotenv import load_dotenv
import os
import re
import sys
import time
import logging
from pathlib import Path
from openai import OpenAI

# ---------------------------
# Setup Logging and Paths
# ---------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("script_generator")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh = logging.FileHandler(LOG_DIR / "script_generator.log")
fh.setFormatter(formatter)
sh = logging.StreamHandler()
sh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(sh)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

# ---------------------------
# Import Config and Setup OpenAI
# ---------------------------
from config import MANIM_KNOWLEDGE_PATH, get_script_path, get_narrator_script_path
import config  # For access to other functions within config

load_dotenv()  # Load environment variables

api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key)
print(f"Using Manim knowledge file: {MANIM_KNOWLEDGE_PATH}")

# ---------------------------
# Utility Functions
# ---------------------------
def extract_last_time_code(script: str) -> tuple:
    """Extract the last time code from the script in [mm:ss] format."""
    matches = re.findall(r'\[(\d+):(\d+)\]', script)
    return (int(matches[-1][0]), int(matches[-1][1])) if matches else None

def extract_scenes_from_script(script: str) -> list:
    """Extract and log all scene descriptions from the script."""
    scenes = re.findall(r'\[SCENE\](.*?)\[/SCENE\]', script, re.DOTALL)
    for i, scene in enumerate(scenes, start=1):
        logger.info(f"Scene {i} length: {len(scene.strip())} characters")
    return [scene.strip() for scene in scenes]

def extract_timing_from_script(script: str) -> dict:
    """
    Extract timing data from the script to help control speech pace.
    Returns a dictionary with timing data, total word count, total duration, and words per minute.
    """
    pattern = r'\[(\d+):(\d+)\]\s*(?:\{([^}]*)\}|([^[\n{][^\n]*))'
    matches = re.findall(pattern, script)
    timing_data = []
    total_words = 0
    for match in matches:
        minutes, seconds = int(match[0]), int(match[1])
        text = match[2] if match[2] else match[3]
        word_count = len(text.strip().split())
        total_words += word_count
        timing_data.append({
            "time": minutes * 60 + seconds,
            "text": text.strip(),
            "word_count": word_count
        })
    total_duration = timing_data[-1]["time"] if timing_data else 300
    words_per_minute = (total_words / total_duration) * 60 if total_duration else 100
    return {
        "timing_data": timing_data,
        "total_words": total_words,
        "total_duration": total_duration,
        "words_per_minute": words_per_minute
    }

def clean_script_for_narration(script: str) -> str:
    """
    Remove scene markers, time codes, and extra formatting to produce a clean narration script.
    """
    text = re.sub(r'\[SCENE\].*?\[/SCENE\]', '', script, flags=re.DOTALL)
    text = re.sub(r'\[\d+:\d+\]\s*\{', '', text)
    text = re.sub(r'\[\d+:\d+\]', '', text)
    text = re.sub(r'[{}]', '', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
    return re.sub(r'\s+', ' ', text.replace('\t', ' ')).strip()

# ---------------------------
# Core Script Generation Function
# ---------------------------
def generate_script(topic: str, duration_minutes: int = 5, sophistication_level: int = 2, output_dirs: dict = None, dry_run: bool = False) -> str:
    """
    Generate an educational script with detailed scene markers for a given math topic.
    
    Args:
        topic: The math topic for the script.
        duration_minutes: Desired length of the video in minutes.
        sophistication_level: Level (1=beginner, 2=intermediate, 3=advanced).
        output_dirs: Dictionary with output directory paths.
        dry_run: If True, return a placeholder script.
        
    Returns:
        The generated script as a string.
    """
    logger.info(f"Starting script generation for topic: {topic} with duration {duration_minutes}min, sophistication {sophistication_level}, dry_run={dry_run}")
    
    # Dry-run returns a placeholder script
    if dry_run:
        logger.info("DRY RUN mode: Returning placeholder script")
        return f"""# Math Tutorial: {topic}

[00:00] Welcome to this math tutorial on {topic}.
[00:05] In this video, we'll explore the key concepts and applications.

[SCENE]
Start with a title screen showing "{topic}" in large blue text on a white background.
[/SCENE]

[00:15] {topic} is a fundamental concept in mathematics.
[00:20] Understanding this concept is important for many applications.

[SCENE]
Show a detailed diagram and explanation of the concept.
[/SCENE]

[00:35] This concludes our brief introduction to {topic}.
[00:40] For more in-depth tutorials, check out our other videos.
"""
    
    start_time = time.time()
    logger.info(f"Script generation started at {time.strftime('%H:%M:%S', time.localtime(start_time))}")

    duration_seconds = duration_minutes * 60
    expected_words = int(duration_seconds * (100/60))
    
    # Determine number of scenes based on duration
    if duration_minutes <= 3:
        scene_count = 3
    elif duration_minutes <= 5:
        scene_count = 4
    elif duration_minutes <= 7:
        scene_count = 5
    else:
        scene_count = 6
    logger.info(f"Planning {scene_count} scenes for a {duration_minutes}-minute video")
    
    # Map sophistication level to description
    level_desc = {
        1: "beginner-friendly, using simple language and basic concepts",
        2: "intermediate level, assuming basic knowledge of the subject",
        3: "advanced level, using sophisticated concepts and terminology appropriate for advanced students"
    }.get(sophistication_level, "beginner-friendly, using simple language and basic concepts")
    logger.info(f"Sophistication level: {level_desc}")

    # Define first scene example based on sophistication level
    if sophistication_level == 1:
        first_scene_example = """
[SCENE]
Start with a title screen that displays "{TOPIC}" in large, blue text against a light background. At 0:03, animate the title moving to the top. At 0:05, draw a right-angled triangle with sides three and four, and hypotenuse five. Use bright colors and label each side. At 0:10, highlight the right angle. At 0:15, draw squares on each side and label their areas. At 0:25, show the phrase "a squared plus b squared equals c squared." At 0:30, animate matching arrows to the numbers. At 0:35, display a checkmark confirming the equation. At 0:40, transition to a second triangle example.
[/SCENE]
"""
    elif sophistication_level == 2:
        first_scene_example = """
[SCENE]
Begin with a title screen displaying "{TOPIC}" in white serif font against a deep blue gradient. At 0:03, fade in the subtitle "The Relationship Between Sides of a Right Triangle." At 0:07, switch to a coordinate plane with axes from minus ten to ten. At 0:10, draw a right triangle in the first quadrant with vertices at (0,0), (8,0), and (8,6) using thick, colored lines. At 0:15, label each side. At 0:20, animate squares growing from each side and label their areas. At 0:30, display "a squared plus b squared equals c squared" with matching color animations. At 0:35, show the calculation "64 plus 36 equals 100" with arrows linking the terms. At 0:40, add the note "Attributed to Pythagoras (570 to 495 BCE)." At 0:45, zoom out for a brief 3D effect and then return to 2D.
[/SCENE]
"""
    else:  # Advanced
        first_scene_example = """
[SCENE]
Open with a minimalist title card displaying "{TOPIC}" in an elegant serif font on a black background. At 0:03, fade in "Geometric and Algebraic Foundations." At 0:07, transition to a complex plane with real and imaginary axes. At 0:11, draw a right triangle with vertices at (0,0), (4,0), and (4,3). At 0:15, label the sides and trace dashed-line squares on each side. At 0:25, render the areas within each square. At 0:30, display vector notation and animate the Euclidean norm calculation. At 0:40, show the general form "c equals the square root of a squared plus b squared." At 0:45, display three alternative proofs side-by-side. At 0:50, link the theorem to the n-dimensional distance formula, and at 0:55, introduce non-Euclidean geometry.
[/SCENE]
"""
    # Define an additional scene for real-world application
    example_scene = """
[SCENE]
Illustrate a real-world application of the theorem. At 0:05, show a ladder leaning against a wall forming a right triangle. Label the wall as twenty feet, the ladder as twenty-five feet, and mark the unknown horizontal distance. At 0:10, overlay the phrase "a squared plus b squared equals c squared." At 0:15, substitute values to demonstrate that the horizontal distance equals fifteen feet. At 0:45, update the diagram with the calculated distance and animate a safety warning about ladder angle. At 0:55, display a montage of similar applications in architecture, navigation, and physics.
[/SCENE]
"""

    # Build prompts for the API call
    system_prompt = f"""
You are an expert math professor. Generate a highly structured, {duration_minutes}-minute educational script on {topic} at a {level_desc}.

### Formatting Rules:
1. Every sentence must be preceded by a time code in the format "[mm:ss] {{sentence}}". The pace is exactly 100 words per minute.
2. The total script length must be exactly {duration_minutes} minutes ({duration_seconds} seconds, about {expected_words} words). The final time code should be at least [{duration_minutes-1}:40].
3. Mathematical expressions must be written in words (e.g., "x squared" instead of "x^2").
4. The script must start with a clear introduction to {topic}, include the first scene within the first 20 seconds, provide multiple examples (including at least one real-world application), and end with a summary.
5. Include exactly {scene_count} detailed scene descriptions. Each scene (delimited by "[SCENE]" and "[/SCENE]") must be at least 150 words long and include precise animation instructions (colors, positions, sizes, timings).

First Scene Example:
{first_scene_example.replace("{TOPIC}", topic)}

Real-World Application Scene Example:
{example_scene}

Generate a complete script following these rules.
"""
    user_prompt = f"Create a detailed {duration_minutes}-minute educational script about {topic} at a {level_desc} sophistication level. The script MUST include {scene_count} extremely detailed scene descriptions, with the FIRST scene within the first 20 seconds visualizing {topic}. The script must run the full {duration_minutes} minutes (ending at least at [{duration_minutes-1}:40])."
    
    logger.info("Calling OpenAI API...")
    if not api_key:
        logger.error("No OpenAI API key found in environment variables!")
    
    try:
        api_call_start = time.time()
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=4000,
            temperature=0.7,
            timeout=90
        )
        result = response.choices[0].message.content
        api_call_duration = time.time() - api_call_start
        logger.info(f"OpenAI API call completed in {api_call_duration:.2f} seconds with response length {len(result)} characters")

        last_time_code = extract_last_time_code(result)
        if last_time_code:
            last_total_seconds = last_time_code[0] * 60 + last_time_code[1]
            logger.info(f"Last time code: [{last_time_code[0]:02d}:{last_time_code[1]:02d}] ({last_total_seconds} seconds)")
            if last_total_seconds < (duration_minutes * 60 - 30):
                warning = f"\n\nWARNING: Script may be too short. Last time code is [{last_time_code[0]:02d}:{last_time_code[1]:02d}] but requested duration was {duration_minutes} minutes.\n"
                result += warning
                logger.warning("Script too short!")
        else:
            logger.error("No time codes found in generated script!")
        
        if output_dirs:
            script_path = config.get_script_path()
            Path(script_path).parent.mkdir(parents=True, exist_ok=True)
            with open(script_path, "w") as f:
                f.write(result)
            logger.info(f"Full script saved to {script_path}")
        
        total_duration = time.time() - start_time
        logger.info(f"Script generation completed in {total_duration:.2f} seconds")
        return result

    except Exception as e:
        logger.exception("Error generating script:")
        if "openai" in str(e).lower() and ("timeout" in str(e).lower() or "timed out" in str(e).lower()):
            logger.error("API call timed out. Returning fallback script.")
            return f"""# Math Tutorial: {topic} (FALLBACK DUE TO API TIMEOUT)

[00:00] Welcome to this math tutorial on {topic}.
[00:05] In this video, we'll explore the key concepts and applications.

[SCENE]
Start with a title screen showing "{topic}" in large blue text on a white background.
[/SCENE]

[00:15] {topic} is a fundamental concept in mathematics.
[00:20] Understanding this concept is important for many applications.

[SCENE]
Show a simple diagram illustrating the basic concept.
[/SCENE]

[00:35] This concludes our brief introduction to {topic}.
[00:40] Please try again later for a more detailed explanation.
"""
        raise

def generate_math_tutorial_script(topic, level="beginner", duration=3, dry_run=False):
    """Wrapper to generate a math tutorial script based on difficulty level."""
    logger.info(f"Generating math tutorial script for '{topic}' at '{level}' level")
    sophistication_level = 1
    if level.lower() in ["intermediate", "medium"]:
        sophistication_level = 2
    elif level.lower() in ["advanced", "expert"]:
        sophistication_level = 3
    return generate_script(topic=topic, duration_minutes=duration, sophistication_level=sophistication_level, dry_run=dry_run)

# ---------------------------
# Main Function for Testing
# ---------------------------
def main():
    from config import get_project_dirs
    topic = input("Enter a math topic for testing: ")
    while True:
        try:
            duration_minutes = int(input("Enter desired video length in minutes (2-10): "))
            if 2 <= duration_minutes <= 10:
                break
            print("Please enter a number between 2 and 10.")
        except ValueError:
            print("Please enter a valid number.")
    
    while True:
        try:
            sophistication_level = int(input("Enter sophistication level (1=Beginner, 2=Intermediate, 3=Advanced): "))
            if 1 <= sophistication_level <= 3:
                break
            print("Please enter a number between 1 and 3.")
        except ValueError:
            print("Please enter a valid number.")
    
    output_dirs = get_project_dirs()
    script = generate_script(topic, duration_minutes, sophistication_level, output_dirs)
    
    scenes = extract_scenes_from_script(script)
    print(f"Generated script with {len(scenes)} scenes")
    
    timing = extract_timing_from_script(script)
    print(f"Script has {timing['total_words']} words with {timing['words_per_minute']:.1f} words per minute")
    print(f"Script duration: {timing['total_duration'] // 60} minutes and {timing['total_duration'] % 60} seconds")
    
    clean_text = clean_script_for_narration(script)
    cleaned_script_path = config.get_narrator_script_path()
    Path(cleaned_script_path).parent.mkdir(parents=True, exist_ok=True)
    with open(cleaned_script_path, "w") as f:
        f.write(clean_text)
    print(f"Test narration script saved to {cleaned_script_path}")

if __name__ == "__main__":
    main()
