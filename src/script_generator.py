from dotenv import load_dotenv
import os
import re
from openai import OpenAI

# Load environment variables from the .env file
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_script(topic: str, duration_minutes: int = 5, sophistication_level: int = 2, output_dir: str = None) -> str:
    """
    Generate an educational script with scene markers for a math topic.
    
    Args:
        topic: The mathematical topic to create a script for
        duration_minutes: The desired length of the video in minutes (default: 5)
        sophistication_level: The level of sophistication (1-3) (default: 2)
        output_dir: Directory to save script and related files (default: None)
        
    Returns:
        A formatted script with time codes and scene markers
    """
    # Determine total duration in seconds and expected word count
    duration_seconds = duration_minutes * 60
    expected_words = duration_seconds * (100/60)  # Based on 100 WPM
    
    # Calculate number of scenes - using fewer scenes for better quality
    if duration_minutes <= 3:
        scene_count = 3  # Minimum 3 scenes
    elif duration_minutes <= 5:
        scene_count = 4  # 4 scenes for 4-5 minute videos
    elif duration_minutes <= 7:
        scene_count = 5  # 5 scenes for 6-7 minute videos
    else:
        scene_count = 6  # 6 scenes for 8-10 minute videos
    
    # Adjust sophistication level description
    if sophistication_level == 1:
        level_desc = "beginner-friendly, using simple language and basic concepts"
    elif sophistication_level == 2:
        level_desc = "intermediate level, assuming basic knowledge of the subject"
    else:
        level_desc = "advanced level, using sophisticated concepts and terminology appropriate for advanced students"
    
    # Create a detailed example of a good first scene based on sophistication level
    if sophistication_level == 1:
        first_scene_example = """
[SCENE]
Start with a title screen that displays "{TOPIC}" in large, blue text against a light background. At 0:03, animate the title moving to the top of the screen. At 0:05, draw a right-angled triangle in the center of the screen, with sides of lengths 3 and 4, and hypotenuse 5. Use bright colors: red for the vertical side (labeled 'a=3'), green for the horizontal side (labeled 'b=4'), and blue for the hypotenuse (labeled 'c=5'). At 0:10, highlight the right angle with a small square in the corner. At 0:15, draw three squares growing outward from each side of the triangle - a red square on side 'a', a green square on side 'b', and a blue square on side 'c'. At 0:20, label each square with its area: "a² = 9", "b² = 16", and "c² = 25". At 0:25, show the equation "a² + b² = c²" at the bottom of the screen. At 0:30, animate the equation by showing "9 + 16 = 25" with arrows pointing from the squares to the numbers in the equation. At 0:35, show a checkmark next to the equation to verify that it works for this triangle. At 0:40, smoothly transition to a second example with a 5-12-13 triangle, demonstrating the same principle with different numbers. This scene should clearly establish what the Pythagorean theorem states and provide a concrete visual demonstration.
[/SCENE]
"""
    elif sophistication_level == 2:
        first_scene_example = """
[SCENE]
Begin with a title screen displaying "{TOPIC}" in white serif font against a deep blue gradient background. At 0:03, fade in a subtitle "The Relationship Between Sides of a Right Triangle" below the title. At 0:07, transition to a coordinate plane with x and y axes from -10 to 10, with grid lines at each unit. At 0:10, draw a right triangle in the first quadrant with vertices at (0,0), (8,0), and (8,6), using thick lines: orange for the horizontal side, purple for the vertical side, and teal for the hypotenuse. At 0:15, label the sides with their lengths: "a=8", "b=6", and "c=10". At 0:20, animate squares growing outward from each side of the triangle in matching colors. At 0:25, label the areas of these squares: "a²=64", "b²=36", and "c²=100". At 0:30, display the equation "a² + b² = c²" at the top of the screen in white text and animate each term lighting up in the corresponding color of the square. At 0:35, show the calculation "64 + 36 = 100" beneath the original equation with an arrow connecting the corresponding terms. At 0:40, add the historical note "Attributed to Pythagoras (570-495 BCE)" with a small ancient Greek icon. At 0:45, zoom out and begin showing a 3D version of the same triangle where the squares become cubes, illustrating that the theorem applies only to squares (not cubes). At 0:50, return to the 2D view and highlight the right angle with a small square, emphasizing that this relationship only holds for right triangles.
[/SCENE]
"""
    else:  # Advanced
        first_scene_example = """
[SCENE]
Open with a minimalist title card displaying "{TOPIC}" in an elegant serif font against a black background. At 0:03, subtly fade in "Geometric and Algebraic Foundations" beneath the title. At 0:07, transition to a complex plane with real and imaginary axes, rendered in muted colors with grid lines. At 0:11, position a right triangle in the first quadrant, with vertices at origin (0,0), point (4,0) on the real axis, and point (4,3) in the complex plane. At 0:15, label the sides a=4 (horizontal, in amber), b=3 (vertical, in teal), and c=5 (hypotenuse, in magenta). At 0:20, trace out squares on each side using dashed lines in matching colors. At 0:25, render the areas as a²=16, b²=9, and c²=25 inside each square. At 0:30, display the vector notation [4,3] representing the position of the third vertex. At 0:35, animate the Euclidean norm calculation ||[4,3]|| = √(4² + 3²) = √(16 + 9) = √25 = 5. At 0:40, show the generalized form for any right triangle with sides a, b, and hypotenuse c: "c = √(a² + b²)". At 0:45, show three alternative proofs simultaneously in small panels: geometric proof with squares, algebraic proof using coordinate geometry, and a proof using similar triangles. At 0:50, show the theorem's connection to the distance formula in n-dimensional space, d(p,q) = √(Σ(qᵢ-pᵢ)²), with a visual connecting the hypotenuse to this concept. At 0:55, introduce the extension to non-Euclidean geometries by showing a curved surface where the theorem doesn't hold, setting up for the more complex discussion to follow.
[/SCENE]
"""

    # Create another example scene specific to the topic
    example_scene = """
[SCENE]
Draw a real-world application of the theorem. At 0:05, show a ladder leaning against a wall, forming a right triangle with the ground. The wall is 20 feet high (vertical side, labeled in blue), the ladder is 25 feet long (hypotenuse, labeled in red), and the ground distance from wall to ladder base needs to be determined (horizontal side, labeled with "?" in green). At 0:10, overlay the Pythagorean theorem formula, a² + b² = c². At 0:15, substitute the known values: a² + b² = 25². At 0:20, simplify: a² + b² = 625. At 0:25, since a = 20 (the wall height), substitute: 20² + b² = 625. At 0:30, calculate: 400 + b² = 625. At 0:35, solve for b²: b² = 225. At 0:40, take the square root: b = 15 feet. At 0:45, update the diagram to show the distance from the wall to the ladder base is 15 feet. At 0:50, animate a safety warning showing that for stability, the ladder should be at a specific angle with the ground (around 75 degrees), verifying this angle using the calculated distances and trigonometry. At 0:55, show other practical applications in a small montage: architects using the theorem to calculate distances, navigation systems calculating direct routes, and physicists using it to find resultant vectors.
[/SCENE]
"""

    # Build the system prompt
    system_prompt = f"""
You are an expert math professor capable of teaching any concept with clarity and precision. Your task is to generate a highly structured, {duration_minutes}-minute educational script on {topic} at a {level_desc}.

### **Formatting and Structure Rules:**
1. **Time Codes:**  
   - Every single sentence must be preceded by a time code in the format `[mm:ss] {{sentence}}`.  
   - The time code must reflect a speaking pace of **exactly 100 words per minute (WPM)**.  
   - Time must increment appropriately so that the total script length is EXACTLY **{duration_minutes} minutes ({duration_seconds} seconds, ~{int(expected_words)} words).**
   - ENSURE THE SCRIPT RUNS THE FULL {duration_minutes} MINUTES - DO NOT END EARLY.
   - The final time code should be at least [{duration_minutes-1}:40] to ensure proper length.

2. **Mathematical Notation:**  
   - **Mathematical expressions must be written out in words, not symbols.**  
   - **Do not use** `x^2`, `f'(x)`, `sin(x)`, etc.  
   - **Instead, write:** `"x squared"`, `"the derivative of f of x"`, `"sine of x"`, etc.  

3. **Script Structure:**  
   - START with a clear introduction explaining what {topic} is in basic terms
   - The FIRST scene must appear within the first 20 seconds of the script
   - The FIRST scene must clearly visualize the core concept of {topic}
   - Include clear explanations of the theorem/concept
   - Provide multiple examples showing the concept in action
   - Include at least one real-world application
   - End with a concise summary that reinforces key takeaways

4. **Scene Management:**
   - Include EXACTLY {scene_count} detailed scenes distributed evenly throughout the script
   - Place the FIRST scene within the first 20 seconds of narration
   - Each scene MUST start with "[SCENE]" and end with "[/SCENE]"
   - Scene descriptions must be EXTREMELY detailed (150+ words)
   - Include specific colors, positions, sizes, and timing for animations
   - Specify exactly what should be shown at specific time points (e.g., "At 0:10, draw...")
   - Each scene should build upon previous knowledge and illustrate current concepts
   - Ensure the scenes match what the narration is discussing at that moment

5. **Example First Scene (Required):**
{first_scene_example.replace("{TOPIC}", topic)}

6. **Example Content Scene:**
{example_scene}

### **Final Instructions:**  
- **Ensure every sentence follows the exact `[mm:ss] {{sentence}}` format.**  
- **Ensure the script runs for the FULL {duration_minutes} minutes, ending no earlier than [{duration_minutes-1}:40].**
- **Place the FIRST scene within the first 20 seconds and make it explain the core concept.**
- **Include EXACTLY {scene_count} detailed scene descriptions.**
- **Make scene descriptions extremely detailed with specific animation instructions.**
- **Generate a complete {duration_minutes}-minute script on {topic}.**
"""

    # Make the API call to generate the script
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a detailed {duration_minutes}-minute educational script about {topic} at a {level_desc} sophistication level. The script MUST include {scene_count} extremely detailed scene descriptions, with the FIRST scene appearing within the first 20 seconds and clearly explaining what {topic} is visually. The script must run the FULL {duration_minutes} minutes (ending at least at [{duration_minutes-1}:40])."}
        ],
        max_tokens=4000,
        temperature=0.7
    )

    result = response.choices[0].message.content
    
    # Verify script length and add warning if too short
    last_time_code = extract_last_time_code(result)
    if last_time_code:
        last_minutes, last_seconds = last_time_code
        last_total_seconds = last_minutes * 60 + last_seconds
        if last_total_seconds < (duration_minutes * 60 - 30):  # If more than 30 seconds short
            warning = f"\n\nWARNING: Script may be too short. Last time code is [{last_minutes:02d}:{last_seconds:02d}] but requested duration was {duration_minutes} minutes.\n"
            result += warning
            print(warning)
    
    # Save script to a text file for review if output_dir is provided
    if output_dir:
        script_path = os.path.join(output_dir, "math_script.txt")
        with open(script_path, "w") as f:
            f.write(result)
        print(f"Script saved to {script_path}")
        
    return result

def extract_last_time_code(script: str) -> tuple:
    """Extract the last time code from the script."""
    time_codes = re.findall(r'\[(\d+):(\d+)\]', script)
    if time_codes:
        last_time = time_codes[-1]
        return int(last_time[0]), int(last_time[1])
    return None

def extract_scenes_from_script(script: str) -> list[str]:
    """
    Extract scene descriptions from a script.
    
    Args:
        script: The complete script with scene markers
        
    Returns:
        A list of scene descriptions
    """
    scenes = []
    scene_pattern = r'\[SCENE\](.*?)\[/SCENE\]'
    matches = re.finditer(scene_pattern, script, re.DOTALL)
    
    for match in matches:
        scene_desc = match.group(1).strip()
        scenes.append(scene_desc)
    
    # Print scene info for verification
    print(f"Extracted {len(scenes)} scene descriptions")
    for i, scene in enumerate(scenes):
        print(f"Scene {i+1} length: {len(scene)} characters")
        
    return scenes

def extract_timing_from_script(script: str) -> dict:
    """
    Extract timing information from the script to help control speech pace.
    
    Args:
        script: The complete script with time codes
        
    Returns:
        Dictionary with extracted timing information
    """
    # Extract time codes and text
    pattern = r'\[(\d+):(\d+)\]\s*(?:\{([^}]*)\}|([^[\n{][^\n]*))'
    matches = re.findall(pattern, script)
    
    timing_data = []
    total_words = 0
    
    for match in matches:
        minutes, seconds = int(match[0]), int(match[1])
        # Get text from either braced format or plain format
        text = match[2] if match[2] else match[3]
        
        time_seconds = minutes * 60 + seconds
        word_count = len(text.strip().split())
        total_words += word_count
        
        timing_data.append({
            "time": time_seconds,
            "text": text.strip(),
            "word_count": word_count
        })
    
    # Calculate the total script duration and words per minute
    if timing_data:
        total_duration = timing_data[-1]["time"]
        words_per_minute = (total_words / total_duration) * 60 if total_duration > 0 else 100
    else:
        total_duration = 300  # Default 5 minutes
        words_per_minute = 100  # Default WPM
    
    return {
        "timing_data": timing_data,
        "total_words": total_words,
        "total_duration": total_duration,
        "words_per_minute": words_per_minute
    }

def clean_script_for_narration(script: str) -> str:
    """
    Thoroughly clean script for narration by removing ALL formatting.
    
    Args:
        script: The complete script with scene markers and time codes
        
    Returns:
        Clean, narration-ready text
    """
    # Step 1: Remove scene markers and all content between them
    clean_text = re.sub(r'\[SCENE\].*?\[/SCENE\]', '', script, flags=re.DOTALL)
    
    # Step 2: Remove time codes - multiple formats
    clean_text = re.sub(r'\[\d+:\d+\]\s*\{', '', clean_text)  # [00:00] {text format}
    clean_text = re.sub(r'\[\d+:\d+\]', '', clean_text)       # [00:00] text format
    
    # Step 3: Remove remaining braces and formatting characters
    clean_text = re.sub(r'[{}]', '', clean_text)
    
    # Step 4: Clean up extra whitespace and newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)  # Multiple newlines to double newline
    clean_text = re.sub(r'^\s+', '', clean_text, flags=re.MULTILINE)  # Leading whitespace
    clean_text = re.sub(r'\s+$', '', clean_text, flags=re.MULTILINE)  # Trailing whitespace
    
    # Step 5: Final polish - ensure no weird characters remain
    clean_text = clean_text.replace('\t', ' ')  # Replace tabs with spaces
    clean_text = re.sub(r'\s+', ' ', clean_text)  # Multiple spaces to single space
    
    return clean_text.strip()

# Test code (will only run if this script is executed directly)
if __name__ == "__main__":
    # Simple test of the script generator
    topic = input("Enter a math topic for testing: ")
    
    # Get duration
    while True:
        try:
            duration_minutes = int(input("Enter desired video length in minutes (2-10): "))
            if 2 <= duration_minutes <= 10:
                break
            else:
                print("Please enter a number between 2 and 10.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get sophistication
    while True:
        try:
            sophistication_level = int(input("Enter sophistication level (1=Beginner, 2=Intermediate, 3=Advanced): "))
            if 1 <= sophistication_level <= 3:
                break
            else:
                print("Please enter a number between 1 and 3.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Create a simple output directory for testing
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Generate and test
        script = generate_script(topic, duration_minutes, sophistication_level, temp_dir)
        
        # Extract and display scene count
        scenes = extract_scenes_from_script(script)
        print(f"Generated script with {len(scenes)} scenes")
        
        # Extract and display timing info
        timing = extract_timing_from_script(script)
        print(f"Script has {timing['total_words']} words with {timing['words_per_minute']:.1f} words per minute")
        print(f"Script duration: {timing['total_duration'] // 60} minutes and {timing['total_duration'] % 60} seconds")
        
        # Test narrator script
        clean_text = clean_script_for_narration(script)
        cleaned_script_path = os.path.join(temp_dir, "test_narrator_script.txt")
        with open(cleaned_script_path, "w") as f:
            f.write(clean_text)
        print(f"Test narration script saved to {cleaned_script_path}")