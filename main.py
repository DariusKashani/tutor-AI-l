from dotenv import load_dotenv
import os
import subprocess
from openai import OpenAI
import re

# Load environment variables from the .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def prompt_claude(user_description: str) -> str:
    # Updated system message to request only code
    system_content = (
        "You are an expert in Python and the Manim animation library. Your task is to generate a complete, self-contained Python code snippet that creates a Manim animation based on a user-provided description. The code should:\n"
        "1. Import all necessary modules from Manim.\n"
        "2. Define a scene class named \"UserAnimationScene\" inheriting from Scene (or a related subclass).\n"
        "3. Use Manim's built-in methods (like Create, Transform, FadeOut, etc.) to animate the objects as described.\n"
        "4. Be structured and commented clearly so that it’s easy to understand and run.\n"
        "Please provide only the Python code without any additional explanation or text."
    )

    # Send the request to OpenAI GPT-4
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_description}
        ],
        max_tokens=1000,
        temperature=0
    )

    # Get the raw response
    response_text = response.choices[0].message.content
    
    # Extract code block if wrapped in triple backticks (e.g., ```python ... ```)
    match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)
    if match:
        return match.group(1)  # Return only the code inside the block
    return response_text  # Fallback to full response if no code block is found

def run_manim():
    command = ["manim", "generated_animation.py", "UserAnimationScene", "-p", "-ql"]
    print("\nRunning Manim to render the animation...\n")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print("Manim Output:\n", result.stdout)
    if result.stderr:
        print("Manim Errors:\n", result.stderr)

if __name__ == "__main__":
    user_prompt = input("Enter your animation description (e.g., 'A red square moving left to right'): ")
    print("\nRequesting code from OpenAI GPT-4...\n")
    generated_code = prompt_claude(user_prompt)
    print("Generated Manim Code:\n")
    print(generated_code)
    with open("generated_animation.py", "w") as f:
        f.write(generated_code)
    print("\nThe generated code has been written to 'generated_animation.py'.")
    run_manim()