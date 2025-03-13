from dotenv import load_dotenv
import os
import json
import subprocess
import requests
import shutil
import tempfile
import sys
import re
from openai import OpenAI

# Import functions from script generator
from script_generator import generate_script, extract_scenes_from_script, extract_timing_from_script, clean_script_for_narration

# Import functions from manim generator
from manim_generator import generate_manim_code

# Load environment variables from the .env file
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_audio_narration(script: str, output_file="narration.mp3") -> str:
    """
    Generate audio narration from the script using ElevenLabs API.
    
    Args:
        script: The script text to convert to speech
        output_file: Filename to save the generated audio
        
    Returns:
        A message indicating success or error
    """
    # Use the improved clean_script_for_narration function
    clean_text = clean_script_for_narration(script)
    
    # Double-check for any remaining formatting characters
    clean_text = re.sub(r'[\[\]\{\}]', '', clean_text)  # Remove any remaining brackets or braces
    
    # Extract timing information to adjust speech pace
    timing_info = extract_timing_from_script(script)
    
    # Save the cleaned text to a file for verification
    with open("narrator_script.txt", "w") as f:
        f.write(clean_text)
    print("Cleaned script saved to narrator_script.txt for verification")
    
    # Verify the script is clean by checking for bracket-like characters
    bracket_check = re.findall(r'[\[\]\{\}]', clean_text)
    if bracket_check:
        print(f"WARNING: Narrator script still contains {len(bracket_check)} brackets or braces")
        print(f"Examples: {bracket_check[:5]}")
    
    try:
        print("Using ElevenLabs API to generate audio with controlled timing...")
        print(f"Script has {timing_info['total_words']} words with target pace of {timing_info['words_per_minute']:.1f} WPM")
        
        # Calculate ideal stability and speaking rate based on script analysis
        target_wpm = timing_info['words_per_minute']
        
        # Normalize speaking rate (1.0 is roughly 150 WPM for ElevenLabs)
        speaking_rate = target_wpm / 150  
        
        # Use the REST API directly
        url = "https://api.elevenlabs.io/v1/text-to-speech/pqHfZKP75CvOlQylNhV4"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
        }
        
        # Include voice_settings to control timing and style
        data = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.4,                 # Lower for more natural variations
                "similarity_boost": 0.75,         # Higher to maintain voice consistency 
                "use_speaker_boost": True,        # Better voice clarity
                "speaking_rate": speaking_rate    # Adjust speed to match our target WPM
            }
        }
        
        print(f"Speech settings: stability=0.4, similarity_boost=0.75, speaking_rate={speaking_rate:.2f}")
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"Audio saved successfully to {output_file}")
            return f"Audio saved to {output_file}"
        else:
            print(f"API request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return f"Error with ElevenLabs API: {response.status_code}"
                
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return f"Error: {e}"

def render_manim_scenes(scenes: list[str]) -> list[str]:
    """
    Render a list of scenes into multiple video files.
    
    Args:
        scenes: List of scene descriptions
        
    Returns:
        List of video file paths
    """
    video_files = []
    
    if not scenes:
        print("No scenes to render!")
        return video_files
    
    # Record existing MP4 files before rendering
    existing_mp4s = set()
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.mp4'):
                existing_mp4s.add(os.path.join(root, file))
    
    for i, scene in enumerate(scenes):
        print(f"\nRendering scene {i+1}/{len(scenes)}...")
        print(f"Scene description length: {len(scene)} characters")
        print(f"Scene preview: {scene[:100]}...")
        
        # Generate the Manim code for this scene using the imported function
        scene_code = generate_manim_code(scene)
        
        # Write the code to a temporary file
        scene_file = f"scene_{i}.py"
        with open(scene_file, "w") as f:
            f.write(scene_code)
            
        # Render the scene using Manim
        print(f"Running Manim on scene_{i}.py...")
        command = ["manim", scene_file, "UserAnimationScene", "-p", "-ql"]
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Print any errors for debugging
        if result.stderr:
            print(f"Manim output for scene {i}:")
            print(result.stderr[:500])  # Print first 500 chars of error
        
        # Find newly created MP4 files
        new_mp4s = set()
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.mp4'):
                    filepath = os.path.join(root, file)
                    if filepath not in existing_mp4s:
                        new_mp4s.add(filepath)
        
        # Update existing MP4s for next iteration
        existing_mp4s.update(new_mp4s)
        
        if new_mp4s:
            # Use the most recently created MP4
            newest_file = max(new_mp4s, key=os.path.getctime)
            video_files.append(newest_file)
            print(f"Found new video file: {newest_file}")
        else:
            print(f"WARNING: No new video file detected for scene {i}")
        
    return video_files

def create_timing_data(scenes: list[str], duration_minutes: int = 5) -> list[dict]:
    """
    Create timing data for synchronizing scenes with audio.
    
    Args:
        scenes: List of scene descriptions
        duration_minutes: Total video duration in minutes
        
    Returns:
        List of timing data dictionaries
    """
    # Convert minutes to seconds
    duration = duration_minutes * 60
    
    scene_count = len(scenes)
    if scene_count == 0:
        return []
    
    # Calculate section durations based on script structure
    # Allocate more time to middle scenes, less to intro/conclusion
    if scene_count <= 3:
        # For 3 or fewer scenes, simple even distribution
        section_durations = [duration / scene_count] * scene_count
    else:
        # For more scenes, weight middle sections slightly heavier
        # First scene: 15% of total time
        # Last scene: 15% of total time
        # Middle scenes: remainder distributed evenly
        first_section = duration * 0.15
        last_section = duration * 0.15
        middle_total = duration - first_section - last_section
        middle_section = middle_total / (scene_count - 2)
        
        section_durations = [first_section]
        for _ in range(scene_count - 2):
            section_durations.append(middle_section)
        section_durations.append(last_section)
    
    # Create timing data
    timing_data = []
    current_time = 0
    
    for i, duration in enumerate(section_durations):
        timing_data.append({
            "start_time": current_time,
            "end_time": current_time + duration
        })
        
        current_time += duration
    
    # Save timing data to file
    with open("script_timing.json", "w") as f:
        json.dump(timing_data, f)
    
    # Print timing info for verification
    for i, timing in enumerate(timing_data):
        start = timing["start_time"]
        end = timing["end_time"]
        duration = end - start
        print(f"Scene {i+1}: {start:.1f}s to {end:.1f}s (duration: {duration:.1f}s)")
        
    return timing_data

def check_ffmpeg_installation():
    """Check if FFmpeg is installed and available."""
    try:
        # Try to run FFmpeg with the -version flag
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

def extend_video_duration(video_path, target_duration, output_path):
    """
    Extend a video to the target duration by freezing the last frame.
    
    Args:
        video_path: Path to the input video
        target_duration: Desired duration in seconds
        output_path: Path to save the extended video
    
    Returns:
        Path to the extended video if successful, None otherwise
    """
    try:
        # Get original video duration
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"Error getting video duration: {result.stderr}")
            return None
            
        original_duration = float(result.stdout.strip())
        print(f"Original video duration: {original_duration:.2f}s")
        
        if original_duration >= target_duration:
            # No need to extend, just copy
            shutil.copy2(video_path, output_path)
            return output_path
            
        # Calculate freeze duration
        freeze_duration = target_duration - original_duration
        print(f"Extending video by freezing last frame for {freeze_duration:.2f}s")
        
        # Create a temporary directory for our work
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract the last frame as an image
            last_frame_path = os.path.join(temp_dir, "last_frame.png")
            frame_time = max(0, original_duration - 0.1)  # 0.1 seconds before the end
            
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(frame_time), 
                "-i", video_path, "-vframes", "1", 
                "-q:v", "1", last_frame_path
            ], check=True)
            
            # Create a video from the last frame with the required duration
            frozen_video_path = os.path.join(temp_dir, "frozen.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", last_frame_path,
                "-c:v", "libx264", "-t", str(freeze_duration),
                "-pix_fmt", "yuv420p", frozen_video_path
            ], check=True)
            
            # Create a file list for concatenation
            concat_file_path = os.path.join(temp_dir, "concat.txt")
            with open(concat_file_path, "w") as f:
                f.write(f"file '{os.path.abspath(video_path)}'\n")
                f.write(f"file '{os.path.abspath(frozen_video_path)}'\n")
            
            # Concatenate the original video with the frozen frame video
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file_path, "-c", "copy", output_path
            ], check=True)
            
        print(f"Successfully extended video to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error extending video: {e}")
        return None

def merge_videos_with_audio(video_files, timing_data, audio_path="narration.mp3", duration_minutes=5):
    """
    Merge scene videos and audio using FFmpeg.
    
    Args:
        video_files: List of video file paths
        timing_data: List of dictionaries with start and end times
        audio_path: Path to the narration audio file
        duration_minutes: Total desired duration of the video
        
    Returns:
        Path to the final video file
    """
    if not video_files:
        print("No video files to merge")
        return None
        
    print(f"Merging {len(video_files)} video files using FFmpeg")
    
    # Check if FFmpeg is installed
    if not check_ffmpeg_installation():
        print("FFmpeg is not installed or not working. Please install FFmpeg.")
        return None
    
    try:
        # Create a temporary directory for our work
        with tempfile.TemporaryDirectory() as temp_dir:
            # Process each video - extend or trim as needed
            processed_videos = []
            
            for i, (video_file, timing) in enumerate(zip(video_files, timing_data)):
                # Calculate target duration for this scene
                target_duration = timing["end_time"] - timing["start_time"]
                print(f"Processing video {i+1}: {video_file} (target duration: {target_duration:.2f}s)")
                
                # Output path for the processed video
                processed_path = os.path.join(temp_dir, f"processed_{i}.mp4")
                
                # Extend or trim the video
                extended_video = extend_video_duration(video_file, target_duration, processed_path)
                if extended_video:
                    processed_videos.append(extended_video)
                else:
                    print(f"Warning: Could not process video {i+1}. Using original.")
                    processed_videos.append(video_file)
            
            # Create a file list for concatenation
            concat_file_path = os.path.join(temp_dir, "concat.txt")
            with open(concat_file_path, "w") as f:
                for video in processed_videos:
                    f.write(f"file '{os.path.abspath(video)}'\n")
            
            # Concatenate all videos
            combined_video_path = os.path.join(temp_dir, "combined.mp4")
            print("Concatenating videos...")
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_file_path, "-c", "copy", combined_video_path
            ], check=True)
            
            # Check final video duration
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", combined_video_path],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                video_duration = float(result.stdout.strip())
                print(f"Combined video duration: {video_duration:.2f}s")
                expected_duration = duration_minutes * 60
                if abs(video_duration - expected_duration) > 30:  # More than 30 seconds off
                    print(f"WARNING: Video duration ({video_duration:.2f}s) differs significantly from expected ({expected_duration:.2f}s)")
            
            # Final output path
            output_path = "final_math_lesson.mp4"
            
            # Add audio if it exists
            if os.path.exists(audio_path):
                print(f"Adding audio from {audio_path}")
                # Add audio to the video
                subprocess.run([
                    "ffmpeg", "-y", "-i", combined_video_path, 
                    "-i", audio_path, "-c:v", "copy", "-c:a", "aac",
                    "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                    output_path
                ], check=True)
            else:
                print("No audio file found. Creating video without audio.")
                shutil.copy2(combined_video_path, output_path)
            
            print(f"Final video created successfully: {output_path}")
            return output_path
    except Exception as e:
        print(f"Error merging videos with FFmpeg: {e}")
        return None

def create_math_tutorial(topic, duration_minutes=5, sophistication_level=2):
    """
    Create a complete math tutorial video.
    
    Args:
        topic: Mathematical topic to create a video about
        duration_minutes: The desired length of the video in minutes
        sophistication_level: The level of sophistication (1-3)
        
    Returns:
        Path to the final video
    """
    print(f"Creating {duration_minutes}-minute math tutorial on: {topic} (Level {sophistication_level})")
    
    # Step 1: Generate script with scene markers
    script = generate_script(topic, duration_minutes, sophistication_level)
    
    # Step 2: Extract scenes from script
    scenes = extract_scenes_from_script(script)
    print(f"Found {len(scenes)} scenes in script")
    
    # Step 3: Generate audio narration with controlled timing
    audio_result = generate_audio_narration(script)
    print(audio_result)
    
    # Step 4: Create timing data for scene synchronization
    timing_data = create_timing_data(scenes, duration_minutes)
    
    # Step 5: Render animations for each scene
    video_files = render_manim_scenes(scenes)
    print(f"Generated {len(video_files)} scene videos")
    
    # Step 6: Merge everything into a final video
    if len(video_files) > 0:
        final_video = merge_videos_with_audio(video_files, timing_data, "narration.mp3", duration_minutes)
        
        if final_video:
            print(f"Success! Final video saved to: {final_video}")
            return final_video
        else:
            print("Failed to create final video")
            return None
    else:
        print("No video files were generated")
        return None

if __name__ == "__main__":    
    # Get the topic from command line or prompt
    if len(sys.argv) > 1:
        topic = sys.argv[1]
    else:
        topic = input("Enter a mathematical topic: ")
    
    # Ask for video length preference
    while True:
        try:
            duration_minutes = int(input("Enter desired video length in minutes (2-10): "))
            if 2 <= duration_minutes <= 10:
                break
            else:
                print("Please enter a number between 2 and 10.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Ask for sophistication level
    while True:
        try:
            sophistication_level = int(input("Enter sophistication level (1=Beginner, 2=Intermediate, 3=Advanced): "))
            if 1 <= sophistication_level <= 3:
                break
            else:
                print("Please enter a number between 1 and 3.")
        except ValueError:
            print("Please enter a valid number.")
    
    create_math_tutorial(topic, duration_minutes, sophistication_level)