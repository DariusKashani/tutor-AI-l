from dotenv import load_dotenv
import os
import re
from openai import OpenAI

# ---------------------------
# Constants
# ---------------------------
WORDS_PER_MINUTE = 100

# Map sophistication level to descriptions
SOPHISTICATION_DESCRIPTIONS = {
    1: "beginner-friendly, using simple language and basic concepts",
    2: "intermediate level, assuming basic knowledge of the subject",
    3: "advanced level, using sophisticated concepts and terminology appropriate for advanced students"
}

# Example scene descriptions based on sophistication level
SCENE_EXAMPLES = {
    1: """[NEW CONCEPT]
Welcome to our lesson on the Pythagorean Theorem. This is a fundamental concept in geometry that helps us understand the relationship between the sides of a right triangle. A right triangle is a triangle with one angle measuring exactly 90 degrees.

The Pythagorean Theorem states that in a right triangle, the square of the length of the hypotenuse equals the sum of the squares of the other two sides. If we call the sides a and b, and the hypotenuse c, then we can write this as: a squared plus b squared equals c squared.
[END CONCEPT|| Scene description: Draw a colorful right triangle with sides clearly labeled a=3, b=4, and c=5. Use a bright blue color for the right angle. Then show squares growing from each side of the triangle - a small square on side a (9 units), a bigger square on side b (16 units), and the largest square on the hypotenuse (25 units). Animate the equation 9 + 16 = 25 appearing below, with arrows connecting each number to its corresponding square.]""",
    
    2: """[NEW CONCEPT]
The concept of limits is essential to calculus. A limit describes the behavior of a function as its input approaches a specific value. We write the limit of a function f(x) as x approaches a as: "the limit as x approaches a of f(x)."

For example, consider the function f(x) = (x² - 1)/(x - 1). What happens as x gets closer and closer to 1? If we try to calculate f(1) directly, we get 0/0, which is undefined. However, if we simplify the function algebraically, we can see that f(x) = x + 1 for all values except x = 1. So as x approaches 1, f(x) approaches 2.
[END CONCEPT|| Scene description: Start with a coordinate plane showing the function f(x) = (x² - 1)/(x - 1) with a hole at x=1. Use a blue line for the function. Add a zooming animation that magnifies the area around x=1. Show arrows approaching x=1 from both sides with values getting closer to 2. Display the algebraic simplification step-by-step alongside: (x² - 1)/(x - 1) = ((x-1)(x+1))/(x-1) = x+1. End with a visual indication that as x→1, f(x)→2, perhaps with dotted lines converging to the point (1,2).]"""
}

# ---------------------------
# Setup OpenAI
# ---------------------------
load_dotenv()  # Load environment variables
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key)

# ---------------------------
# Utility Functions
# ---------------------------
def extract_concepts(script):
    """Extract concept segments and their scene descriptions from the script."""
    pattern = r'\[NEW CONCEPT\](.*?)\[END CONCEPT\|\| Scene description: (.*?)\]'
    matches = re.findall(pattern, script, flags=re.DOTALL)
    
    narrations = []
    scene_descriptions = []
    
    for match in matches:
        narrations.append(match[0].strip())
        scene_descriptions.append(match[1].strip())
    
    return narrations, scene_descriptions

# ---------------------------
# Core Script Generation Function
# ---------------------------
def generate_script(topic, duration_minutes=5, sophistication_level=2):
    """
    Generate an educational script about a math topic with concept segments and scene descriptions.
    
    Args:
        topic: The math topic for the script.
        duration_minutes: Desired length of the video in minutes.
        sophistication_level: Level (1=beginner, 2=intermediate, 3=advanced).
        
    Returns:
        Tuple of (narrations, scene_descriptions)
    """
    # Validate and default parameters
    if sophistication_level not in [1, 2, 3]:
        sophistication_level = 2
    
    expected_words = int(duration_minutes * 60 * (WORDS_PER_MINUTE/60))
    
    # Determine number of concepts based on duration
    if duration_minutes <= 3:
        concept_count = 3
    elif duration_minutes <= 5:
        concept_count = 5
    elif duration_minutes <= 7:
        concept_count = 7
    else:
        concept_count = 10
    
    # Get sophistication level description
    level_desc = SOPHISTICATION_DESCRIPTIONS.get(sophistication_level, SOPHISTICATION_DESCRIPTIONS[2])
    
    # Get appropriate example based on sophistication level
    scene_example = SCENE_EXAMPLES.get(sophistication_level, SCENE_EXAMPLES[2])
    
    # Build prompts for the API call
    system_prompt = f"""
You are an expert math professor creating educational scripts. Generate a structured educational script on {topic} at a {level_desc} that would be about {duration_minutes} minutes long when read aloud (approximately {expected_words} words total).

### Formatting Rules:
1. Divide the script into exactly {concept_count} concept segments.
2. Each concept should focus on one key idea related to {topic}.
3. Mark the beginning of each concept segment with [NEW CONCEPT].
4. End each concept segment with [END CONCEPT|| Scene description: ...] where you provide a detailed visual description of what should be shown during this concept.
5. Mathematical expressions should be written in words (e.g., "x squared" instead of "x^2").

### Important Instructions:
1. While talking about each concept, assume a corresponding animation will be alongside it.
2. The narration can refer to visual elements (e.g., "As you can see in this diagram") that will be described in the scene description.
3. Each scene description should be highly detailed (at least 80 words) and include specific visuals:
   - What elements to show (diagrams, equations, examples)
   - Colors, layout, and animation instructions
   - How to visually represent abstract concepts
   - Transitions between visual elements

Example of a concept segment with scene description:
{scene_example}

Generate a complete script following these rules.
"""
    user_prompt = f"Create a detailed educational script about {topic} at a {level_desc} sophistication level. The script should have exactly {concept_count} concepts, each with [NEW CONCEPT] and [END CONCEPT|| Scene description: ...] markers. While explaining each concept, assume corresponding animations are being shown, and provide detailed scene descriptions at the end of each concept segment."
    
    # Call OpenAI API
    try:
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
        
        full_script = response.choices[0].message.content
        
        # Extract narrations and scene descriptions
        narrations, scene_descriptions = extract_concepts(full_script)
        
        return narrations, scene_descriptions
        
    except Exception as e:
        print(f"Error generating script: {str(e)}")
        # Return a simple fallback script in case of error
        fallback_script = f"""[NEW CONCEPT]
Welcome to this introduction to {topic}. This is an important concept in mathematics that has many applications.
[END CONCEPT|| Scene description: Show a title screen with "{topic}" in large blue text on a white background. Include relevant mathematical symbols or simple illustrations around the title.]

[NEW CONCEPT]
Let's start by understanding the basic definition and key properties of {topic}.
[END CONCEPT|| Scene description: Create a simple diagram illustrating the core concept with labels for key components. Use different colors to highlight important elements.]

[NEW CONCEPT]
Thank you for learning about {topic} with us today. We hope this introduction has been helpful.
[END CONCEPT|| Scene description: Show a summary screen with the key points covered, using bullet points and a small illustration of the main concept.]
"""
        narrations, scene_descriptions = extract_concepts(fallback_script)
        return narrations, scene_descriptions

# ---------------------------
# Simple CLI for testing
# ---------------------------
def main():
    topic = input("Enter a math topic for the video: ")
    
    try:
        duration_minutes = int(input("Enter desired video length in minutes (2-10): "))
        if not (2 <= duration_minutes <= 10):
            print("Using default duration of 5 minutes.")
            duration_minutes = 5
    except ValueError:
        print("Using default duration of 5 minutes.")
        duration_minutes = 5
    
    try:
        sophistication_level = int(input("Enter sophistication level (1=Beginner, 2=Intermediate, 3=Advanced): "))
        if not (1 <= sophistication_level <= 3):
            print("Using default level: 2 (Intermediate).")
            sophistication_level = 2
    except ValueError:
        print("Using default level: 2 (Intermediate).")
        sophistication_level = 2
    
    print(f"Generating script for '{topic}' ({duration_minutes} minutes, level {sophistication_level})...")
    
    narrations, scene_descriptions = generate_script(
        topic, 
        duration_minutes, 
        sophistication_level
    )
    
    print("\n--- NARRATIONS ---")
    for i, narration in enumerate(narrations, 1):
        print(f"\nNarration {i}:")
        print(narration)
    
    print("\n\n--- SCENE DESCRIPTIONS ---")
    for i, scene in enumerate(scene_descriptions, 1):
        print(f"\nScene {i}:")
        print(scene)
    
    print(f"\n\nGenerated {len(narrations)} concept segments with narrations and scene descriptions")

if __name__ == "__main__":
    main()