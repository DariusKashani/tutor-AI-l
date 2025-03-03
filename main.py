import requests
import subprocess
import sys
from dotenv import load_dotenv
import os

load_dotenv()  # This loads the variables from the .env file

# Replace with your actual Anthropic API key.
API_KEY = os.getenv("API_KEY")
# Adjust this API URL according to the latest Anthropic API documentation.
API_URL = "https://api.anthropic.com/v1/complete"

def prompt_claude(user_description: str) -> str:
    # Construct the meta prompt for Claude Sonnet 3.7.
    # IMPORTANT: The scene class is explicitly named "UserAnimationScene"
    # so that we can call it later with Manim.
    prompt = f"""
You are an expert in Python and the Manim animation library. Your task is to generate a complete, self-contained Python code snippet that creates a Manim animation based on a user-provided description. The code should:
1. Import all necessary modules from Manim.
2. Define a scene class named "UserAnimationScene" inheriting from Scene (or a related subclass).
3. Use Manim's built-in methods (like Create, Transform, FadeOut, etc.) to animate the objects as described.
4. Be structured and commented clearly so that it’s easy to understand and run.

For example, if the user prompt is "Animate a square transforming into a circle," your code should create a square, animate its creation, transform it into a circle, and then fade it out.

User prompt: {user_description}

Please output only the Python code without additional commentary.
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": "claude-v3.7",
        "prompt": prompt,
        "max_tokens_to_sample": 500,
        "stop_sequences": []
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        # Extract the generated code from the API response.
        data = response.json()
        return data.get("completion", "")
    else:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)

def run_manim():
    # Run the manim command on the generated file.
    # - "generated_animation.py" is the file with our generated code.
    # - "UserAnimationScene" is the scene class name as specified in the prompt.
    # - "-p" triggers preview and "-ql" uses low quality for faster rendering.
    command = ["manim", "generated_animation.py", "UserAnimationScene", "-p", "-ql"]
    print("\nRunning Manim to render the animation...\n")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print("Manim Output:\n", result.stdout)
    if result.stderr:
        print("Manim Errors:\n", result.stderr)

if __name__ == "__main__":
    # Step 1: Get a description from the user.
    user_prompt = input("Enter your animation description: ")

    # Step 2: Call Claude to get the corresponding Manim code.
    print("\nRequesting code from Claude Sonnet 3.7...\n")
    generated_code = prompt_claude(user_prompt)

    # Display the generated code for review.
    print("Generated Manim Code:\n")
    print(generated_code)

    # Step 3: Write the generated code to a Python file.
    with open("generated_animation.py", "w") as f:
        f.write(generated_code)
    print("\nThe generated code has been written to 'generated_animation.py'.")

    # Step 4: Call Manim to run the animation and preview the result.
    run_manim()
