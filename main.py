from dotenv import load_dotenv
import os
import subprocess
from openai import OpenAI
import re
import os
from dotenv import load_dotenv
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
import glob
import os
import json
from dotenv import load_dotenv
from elevenlabs import set_api_key, generate
from elevenlabs.client import ElevenLabs


# Load environment variables from the .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = ElevenLabs(apikey=os.getenv("ELEVENLABS_API_KEY"))

def gpt_generates_script(user_description: str) -> str:
    system_content = (

        """
Steps

You are an expert math professor capable of teaching any concept with clarity and precision. Your task is to generate a highly structured, 5-minute educational script on a given mathematical topic. 

### **Formatting and Structure Rules:**
1. **Time Codes:**  
   - Every single sentence must be preceded by a time code in the format `[mm:ss] {sentence}`.  
   - The time code must reflect a speaking pace of **exactly 100 words per minute (WPM)**.  
   - Time must increment appropriately so that the total script length is **5 minutes (300 seconds, ~500 words).**  

2. **Mathematical Notation:**  
   - **Mathematical expressions must be written out in words, not symbols.**  
   - **Do not use** `x^2`, `f'(x)`, `sin(x)`, etc.  
   - **Instead, write:** `"x squared"`, `"the derivative of f of x"`, `"sine of x"`, etc.  

3. **Lesson Structure:**  
   - **Do not include section headers** in the final script.  
   - The script must follow this structure but flow naturally as if spoken by a professor:  
     - **Hook (First 30 seconds):** Start with an engaging analogy, puzzle, or real-world connection.  
     - **Introduction (Next 30 seconds):** Recall prior knowledge, introduce key terms, and state the lesson objective.  
     - **Main Explanation (3 minutes, 30 seconds):** Provide step-by-step explanations, examples, and intuitive insights.  
     - **Practice Problem (30 seconds):** Present a problem, prompt the audience to think, then reveal the answer.  
     - **Conclusion (Final 30 seconds):** Summarize key takeaways and encourage further exploration.  

4. **Scene Management:**
    - Embedded within the structure are scenes.
    - Each scene is a single animation.
    - Each scene must be self-contained and not rely on other scenes.
    - Each scene corresponds to a chunk of text.
    - Each scene should be marked with [SCENE] at the start and [/SCENE] at the end.
    - Each scene should have a brief description of what should be animated.

5. **Common Mistakes:**  
   - **Only include common mistakes if they are critical to understanding the concept.**  

### **Final Instructions:**  
- **Ensure every sentence follows the exact `[mm:ss] {sentence}` format.**  
- **Ensure all time codes increase precisely according to 100 WPM pacing.**  
- **Ensure all math notation is fully written out in words.**  
- **Ensure the script feels natural and engaging, as if a professor is speaking.**  
- **Generate a 5-minute script on topic the user gives you. * 

"""
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_description}
        ],
        max_tokens=1500,
        temperature=0.7
    )

    return response.choices[0].message.content

def elevenlabs_generates_audio(text, output_file="output.mp3"):
    try:
        audio = generate(
            text=text,
            voice_id="pqHfZKP75CvOlQylNhV4",
            model_id="eleven_multilingual_v2"
        )
        with open(output_file, "wb") as f:
            f.write(audio)
        return f"Audio saved to {output_file}"
    except Exception as e:
        return f"Error: {e}"

def gpt_splits_script_into_scenes(script: str) -> list[str]:
    """
    Split a script into scenes based on [SCENE] markers.
    Returns a list of scene descriptions.
    """
    scenes = []
    scene_pattern = r'\[SCENE\](.*?)\[/SCENE\]'
    matches = re.finditer(scene_pattern, script, re.DOTALL)
    
    for match in matches:
        scene_desc = match.group(1).strip()
        scenes.append(scene_desc)
        
    return scenes

def gpt_codes_single_scene(user_description: str) -> str:
    # Updated system message to request only code
    system_content = (
        "You are an expert in Python and the Manim animation library. Your task is to generate a complete, self-contained Python code snippet that creates a Manim animation based on a user-provided description. The code should:\n"
        "1. Import all necessary modules from Manim.\n"
        "2. Define a scene class named \"UserAnimationScene\" inheriting from Scene (or a related subclass).\n"
        "3. Use Manim's built-in methods (like Create, Transform, FadeOut, etc.) to animate the objects as described.\n"
        "4. Be structured and commented clearly so that it's easy to understand and run.\n"
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

def gpt_renders_multiple_scenes(scenes: list[str]) -> list[str]:
    """
    Render a list of scenes into multiple video files.
    Returns a list of video file paths.
    """
    video_files = []
    for i, scene in enumerate(scenes):
        # Generate the Manim code for this scene
        scene_code = gpt_codes_single_scene(scene)
        
        # Write the code to a temporary file
        scene_file = f"scene_{i}.py"
        with open(scene_file, "w") as f:
            f.write(scene_code)
            
        # Render the scene using Manim
        command = ["manim", scene_file, "UserAnimationScene", "-p", "-ql"]
        subprocess.run(command)
        
        # Add the generated video file to our list
        video_file = f"media/videos/1080p60/UserAnimationScene.mp4"
        if os.path.exists(video_file):
            video_files.append(video_file)
            
        # Clean up the temporary file
        os.remove(scene_file)
        
    return video_files

def merge_scenes_into_video(scenes: list[str]) -> str:
    """
    Merge a list of scenes into a single video, synchronizing with audio timestamps.
    Each scene will hold its final frame until the next scene's timestamp.
    """

    # Get all generated MP4 files in order
    video_files = sorted(glob.glob("media/videos/1080p60/*.mp4"))
    if not video_files:
        print("No video files found to merge")
        return None

    # Load the script timing data (assuming it's saved as JSON)
    with open("script_timing.json", "r") as f:
        timing_data = json.load(f)

    # Load all video clips and prepare segments
    final_clips = []
    current_time = 0
    
    for i, (video_file, scene_data) in enumerate(zip(video_files, timing_data)):
        clip = VideoFileClip(video_file)
        
        # Get the timestamp when this scene should end
        scene_end_time = scene_data["end_time"]
        
        # Calculate how long to hold the final frame
        scene_duration = scene_end_time - current_time
        
        if scene_duration > clip.duration:
            # Freeze the final frame for the remaining duration
            frozen_duration = scene_duration - clip.duration
            last_frame = clip.to_ImageClip(clip.duration)
            last_frame = last_frame.set_duration(frozen_duration)
            
            # Combine the animated part with the frozen part
            scene_clip = concatenate_videoclips([clip, last_frame])
        else:
            scene_clip = clip.subclip(0, scene_duration)
        
        final_clips.append(scene_clip)
        current_time = scene_end_time

    # Concatenate all video segments
    final_video = concatenate_videoclips(final_clips)

    # Load and add the audio
    if os.path.exists("narration.mp3"):
        audio = AudioFileClip("narration.mp3")
        final_video = final_video.set_audio(audio)

    # Write the final video
    output_path = "final_animation.mp4"
    final_video.write_videofile(output_path)

    # Clean up
    for clip in final_clips:
        clip.close()
    if 'audio' in locals():
        audio.close()
    final_video.close()

    return output_path

def run_manim():
    command = ["manim", "generated_animation.py", "UserAnimationScene", "-p", "-ql"]
    print("\nRunning Manim to render the animation...\n")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print("Manim Output:\n", result.stdout)
    if result.stderr:
        print("Manim Errors:\n", result.stderr)

if __name__ == "__main__":
    # Get user input for the math topic
    topic = input("Enter the mathematical topic you want to learn about: ")
    
    # Generate the script with scene markers
    print("\nGenerating educational script...\n")
    script = gpt_generates_script(topic)
    print("Script generated successfully!")
    
    # Generate audio narration
    print("\nGenerating audio narration...\n")
    audio_file = elevenlabs_generates_audio(script)
    print("Audio generated successfully!")
    
    # Split script into scenes
    print("\nSplitting script into scenes...\n")
    scenes = gpt_splits_script_into_scenes(script)
    print(f"Split into {len(scenes)} scenes")
    
    # Render all scenes
    print("\nRendering individual scenes...\n")
    video_files = gpt_renders_multiple_scenes(scenes)
    print("All scenes rendered successfully!")
    
    # Merge scenes with audio
    print("\nMerging scenes and audio...\n")
    final_video = merge_scenes_into_video(scenes)
    print(f"\nFinal video created at: {final_video}")