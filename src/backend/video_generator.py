import os
import sys
import time
import math
import shutil
import subprocess
import re
import json
import tempfile
from pathlib import Path
import logging
import traceback
import concurrent.futures
from typing import List, Dict, Any, Tuple, Optional

from dotenv import load_dotenv
load_dotenv()

# ---------------------------
# Logging Setup
# ---------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = logging.FileHandler(LOG_DIR / "video_generator.log")
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# ---------------------------
# Update Python Path to Include Project Root
# ---------------------------
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

# ---------------------------
# Optional External Libraries
# ---------------------------
try:
    from elevenlabs import generate as eleven_generate
    from elevenlabs import set_api_key as eleven_set_api_key
    elevenlabs_available = True
    logger.info("ElevenLabs package found and imported.")
except ImportError:
    elevenlabs_available = False
    logger.warning("ElevenLabs package not found. Audio generation will use placeholder files.")
    logger.info("To install ElevenLabs, run: pip install elevenlabs")

try:
    from openai import OpenAI
    openai_available = True
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except ImportError:
    openai_available = False
    logger.warning("OpenAI package not found. Using fallback methods.")

# ---------------------------
# Centralized Configuration and Function Imports
# ---------------------------
from config import (
    get_timing_data_path,
    get_subtitle_path,
    get_scene_path,
    get_project_dirs
)

# Import the script generator module
from src.backend import script_generator
from src.backend import manim_generator
from src.backend.manim_generator import (
    clean_existing_scene_file,
)

# Define the path to ffmpeg
FFMPEG_PATH = os.path.expanduser("~/bin/ffmpeg")
# If ffmpeg not found in user bin, try to find it in system
if not os.path.exists(FFMPEG_PATH):
    try:
        # First try the bundled ffmpeg that's already in the virtual environment
        bundled_ffmpeg = os.path.join(
            os.path.dirname(sys.executable),
            "../lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
        )
        if os.path.exists(bundled_ffmpeg):
            FFMPEG_PATH = bundled_ffmpeg
            logger.info(f"Using bundled ffmpeg from imageio: {FFMPEG_PATH}")
        else:
            # Try to find ffmpeg in PATH
            ffmpeg_result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
            if ffmpeg_result.returncode == 0:
                FFMPEG_PATH = ffmpeg_result.stdout.strip()
                logger.info(f"Using ffmpeg from PATH: {FFMPEG_PATH}")
            else:
                # Check some common locations
                common_locations = [
                    "/usr/bin/ffmpeg",
                    "/usr/local/bin/ffmpeg",
                    "/opt/homebrew/bin/ffmpeg",
                    "/opt/local/bin/ffmpeg"
                ]
                for loc in common_locations:
                    if os.path.exists(loc):
                        FFMPEG_PATH = loc
                        logger.info(f"Using ffmpeg from {FFMPEG_PATH}")
                        break
                if not os.path.exists(FFMPEG_PATH):
                    logger.warning(f"ffmpeg not found at {FFMPEG_PATH}. Video generation may fail.")
    except Exception as e:
        logger.warning(f"Error finding ffmpeg: {e}. Using default path: {FFMPEG_PATH}")

# Only importing clean_existing_scene_file as we have our own verify_manim_installation
from src.backend.manim_generator import clean_existing_scene_file

# ---------------------------
# Verify Manim Installation
# ---------------------------
def verify_manim_installation():
    """Verify that Manim is installed and working."""
    try:
        # Try to import manim
        import manim
        logger.info(f"Found manim version: {manim.__version__}")
        
        # Run a simple check command
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-c", "import manim; print('Manim works!')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "Manim works!" in result.stdout:
                logger.info("Manim installation verified")
                return True
            else:
                logger.warning(f"Manim might not be working properly: {result.stderr}")
                return False
        except subprocess.SubprocessError as e:
            logger.warning(f"Failed to verify manim installation: {e}")
            return False
            
    except ImportError:
        logger.error("Manim package not found. Please install it with: pip install manim")
        return False
    except Exception as e:
        logger.error(f"Error verifying Manim installation: {e}")
        return False

# ---------------------------
# Function: Generate Subtitle File
# ---------------------------
def generate_subtitle_file(script: str, output_dirs: dict) -> Path:
    """
    Generate an SRT subtitle file from the script timing data.
    
    Args:
        script: The complete script with time codes.
        output_dirs: Dictionary with output directory paths.
        
    Returns:
        Path to the generated SRT file.
    """
    logger.info("Generating subtitle file from script...")
    pattern = r'\[(\d+):(\d+)\]\s*(?:\{([^}]*)\}|([^[\n{][^\n]*))'
    matches = re.findall(pattern, script)
    
    subtitle_entries = []
    
    # Process subtitles with improved timing
    for idx, match in enumerate(matches, 1):
        minutes, seconds = int(match[0]), int(match[1])
        text = (match[2] or match[3]).strip()
        if not text:
            continue

        # Calculate start and end times
        start_sec = minutes * 60 + seconds
        
        # Determine how long this subtitle should stay on screen
        # Split text into chunks for better readability (approx 10-12 words per subtitle)
        words = text.split()
        
        # Calculate a reasonable display time based on word count
        # Average reading speed is about 2-3 words per second
        # We'll use 2.2 words per second for comfortable reading
        display_duration = max(len(words) / 2.2, 3)  # At least 3 seconds
        
        # For long text, split into multiple subtitle entries
        if len(words) > 15:
            chunks = []
            current_chunk = []
            current_length = 0
            
            for word in words:
                current_length += len(word) + 1
                current_chunk.append(word)
                
                # Split at natural sentence boundaries if possible, or after ~12 words
                if (word.endswith('.') or word.endswith('!') or word.endswith('?')) and len(current_chunk) >= 5:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                elif current_length > 70 or len(current_chunk) >= 12:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
            
            # Add any remaining words
            if current_chunk:
                chunks.append(' '.join(current_chunk))
                
            # Create subtitles for each chunk with appropriate timing
            chunk_duration = display_duration / len(chunks)
            for i, chunk_text in enumerate(chunks):
                chunk_start = start_sec + (i * chunk_duration)
                chunk_end = chunk_start + chunk_duration
                
                start_time_formatted = f"{int(chunk_start)//3600:02d}:{(int(chunk_start)%3600)//60:02d}:{int(chunk_start)%60:02d},{int(chunk_start*1000)%1000:03d}"
                end_time_formatted = f"{int(chunk_end)//3600:02d}:{(int(chunk_end)%3600)//60:02d}:{int(chunk_end)%60:02d},{int(chunk_end*1000)%1000:03d}"
                
                subtitle_entries.append(f"{idx + i}\n{start_time_formatted} --> {end_time_formatted}\n{chunk_text}\n")
        else:
            # Simple case for short text
            end_sec = start_sec + display_duration
            
            # Check for next subtitle to avoid overlap
            if idx < len(matches):
                next_min, next_sec = int(matches[idx][0]), int(matches[idx][1])
                next_sec_total = next_min * 60 + next_sec
                end_sec = min(end_sec, next_sec_total - 0.1)  # Avoid overlap
            
            start_time_formatted = f"{int(start_sec)//3600:02d}:{(int(start_sec)%3600)//60:02d}:{int(start_sec)%60:02d},{int(start_sec*1000)%1000:03d}"
            end_time_formatted = f"{int(end_sec)//3600:02d}:{(int(end_sec)%3600)//60:02d}:{int(end_sec)%60:02d},{int(end_sec*1000)%1000:03d}"
            
            subtitle_entries.append(f"{idx}\n{start_time_formatted} --> {end_time_formatted}\n{text}\n")

    srt_path = Path(get_subtitle_path())
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("\n".join(subtitle_entries))
    logger.info(f"Generated SRT file with {len(subtitle_entries)} entries at {srt_path}")
    return srt_path

# ---------------------------
# Function: Generate Audio Narration
# ---------------------------
def call_elevenlabs_api(endpoint, method="GET", data=None, headers=None):
    """Make a direct call to the ElevenLabs API"""
    import requests
    
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("No ElevenLabs API key found in environment variables")
        return None
        
    base_url = "https://api.elevenlabs.io/v1"
    url = f"{base_url}/{endpoint.lstrip('/')}"
    
    default_headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return None
            
        if response.status_code == 200:
            return response.content if endpoint.startswith("text-to-speech") else response.json()
        else:
            logger.error(f"API call failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.exception(f"Error calling ElevenLabs API: {e}")
        return None

def generate_audio_narration(text: str, filename: str = None, dry_run: bool = False) -> Path:
    """
    Generate audio narration for the given text using ElevenLabs API.
    
    Args:
        text: Text to convert to speech.
        filename: Desired filename for the generated audio.
        dry_run: If True, creates a silent audio placeholder.
        
    Returns:
        Path to the generated audio file.
    """
    audio_dir = Path("generated/audio")
    audio_dir.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = f"speech_{int(time.time())}.mp3"
    audio_path = audio_dir / filename

    if dry_run:
        logger.info("[DRY RUN] Creating silent audio placeholder.")
        estimated_duration = len(text.split()) / 2.5  # More realistic timing
        create_silent_audio_placeholder(audio_path, estimated_duration)
        return audio_path

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("No ElevenLabs API key found. Using silent audio placeholder.")
        estimated_duration = len(text.split()) / 2.5
        create_silent_audio_placeholder(audio_path, estimated_duration)
        return audio_path

    # Method 1: Try using elevenlabs package if available
    if elevenlabs_available:
        try:
            logger.info("Using ElevenLabs package for voice generation")
            
            # List of voices to try in order of preference
            voices = ["Rachel", "Adam", "Bella", "Antoni"]
            
            for voice in voices:
                try:
                    logger.info(f"Attempting to generate audio with voice: {voice}")
                    audio = eleven_generate(
                        text=text,
                        voice=voice,
                        model="eleven_multilingual_v2"
                    )
                    
                    with open(audio_path, "wb") as f:
                        f.write(audio)
                    
                    logger.info(f"Successfully generated audio narration with voice {voice} at {audio_path}")
                    return audio_path
                except Exception as voice_error:
                    logger.warning(f"Failed with voice {voice}: {str(voice_error)}")
                    continue
                    
            logger.warning("All voice attempts with package failed. Trying direct API calls.")
        except Exception as e:
            logger.exception(f"Error using ElevenLabs package: {e}")
    
    # Method 2: Use direct API calls if package isn't available or failed
    try:
        logger.info("Attempting direct ElevenLabs API calls")
        
        # Default voice IDs to try
        voice_ids = [
            "21m00Tcm4TlvDq8ikWAM",  # Rachel
            "pNInz6obpgDQGcFmaJgB",  # Adam
            "EXAVITQu4vr4xnSDxMaL",  # Bella
            "ErXwobaYiN019PkySvjV"   # Antoni
        ]
        
        # Try to get available voices first
        try:
            voices_data = call_elevenlabs_api("voices")
            if voices_data and "voices" in voices_data:
                # Get voice IDs from API response
                api_voice_ids = [v["voice_id"] for v in voices_data["voices"]]
                if api_voice_ids:
                    voice_ids = api_voice_ids[:4]  # Limit to first 4 voices
                    logger.info(f"Retrieved {len(voice_ids)} voice IDs from API")
        except Exception as e:
            logger.warning(f"Could not retrieve voices from API, using default voice IDs: {e}")
        
        # Try each voice ID
        for voice_id in voice_ids:
            try:
                logger.info(f"Attempting to generate audio with voice ID: {voice_id}")
                
                # Direct API call to generate speech
                data = {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5
                    }
                }
                
                audio_content = call_elevenlabs_api(
                    f"text-to-speech/{voice_id}", 
                    method="POST", 
                    data=data
                )
                
                if audio_content:
                    with open(audio_path, "wb") as f:
                        f.write(audio_content)
                    
                    logger.info(f"Successfully generated audio with direct API call using voice ID {voice_id}")
                    return audio_path
                else:
                    logger.warning(f"Failed to generate audio with voice ID {voice_id}")
            except Exception as voice_error:
                logger.warning(f"API call failed for voice ID {voice_id}: {str(voice_error)}")
                continue
    
    except Exception as e:
        logger.exception(f"Error with direct API implementation: {e}")
    
    # If all methods fail, use silent audio
    logger.error("All audio generation attempts failed. Using silent audio placeholder.")
    estimated_duration = len(text.split()) / 2.5
    create_silent_audio_placeholder(audio_path, estimated_duration)
    return audio_path

# ---------------------------
# Function: Render Single Scene
# ---------------------------
def render_single_scene(scene_data: Tuple[int, str, Path, bool]) -> Tuple[int, str, bool]:
    """
    Render a single Manim scene file.
    
    Args:
        scene_data: Tuple containing (index, scene_file_path, output_directory, force_regenerate)
        
    Returns:
        Tuple containing (index, output_file_path, success_status)
    """
    i, scene_file, output_dir, force_regenerate = scene_data
    output_path = output_dir / f"scene_{i}.mp4"
    scene_path = Path(scene_file)
    
    logger.info(f"Rendering scene {i+1} from {scene_file}")
    logger.info(f"Cleaning scene file {scene_file}")
    clean_existing_scene_file(str(scene_path))

    # If output file already exists with non-zero size and we're not force regenerating, skip rendering
    if not force_regenerate and output_path.exists() and output_path.stat().st_size > 0:
        logger.info(f"Output file already exists at {output_path}, skipping rendering")
        return (i, str(output_path), True)
    elif force_regenerate and output_path.exists():
        logger.info(f"Force regenerating scene at {output_path}")
        try:
            output_path.unlink()  # Delete the existing file
            logger.info(f"Deleted existing file: {output_path}")
        except Exception as e:
            logger.warning(f"Could not delete existing scene file: {e}")
        
    # Try multiple approaches to render the scene
    success = False
    
    # Approach 1: Using Python module approach (most reliable)
    try:
        logger.info(f"Trying Python module approach to render Manim scene {i+1}")
        # Use importlib to dynamically import the scene file and run it
        import importlib.util
        import sys
        
        # Prepare a unique module name
        module_name = f"scene_module_{i}_{int(time.time())}"
        
        # Create a spec and import the module
        spec = importlib.util.spec_from_file_location(module_name, scene_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Check if UserAnimationScene exists in the module
            if hasattr(module, 'UserAnimationScene'):
                # Configure Manim to output directly to our desired location with the desired filename
                from manim import config
                config.media_dir = str(output_dir)
                config.video_dir = str(output_dir)
                config.output_file = f"scene_{i}"
                
                # Create and render the scene
                scene = module.UserAnimationScene()
                scene.render()
                
                # Verify the output file exists
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"Successfully rendered to {output_path} using Python module approach")
                    success = True
                else:
                    # Look for any other generated mp4 file in the output directory
                    possible_outputs = list(output_dir.glob("*.mp4"))
                    if possible_outputs:
                        for possible_output in possible_outputs:
                            if "scene_" in possible_output.name and possible_output.stat().st_size > 0:
                                if possible_output.name != output_path.name:
                                    # If found but with wrong name, rename it
                                    possible_output.rename(output_path)
                                    logger.info(f"Renamed {possible_output} to {output_path}")
                                success = True
                                break
            else:
                logger.warning(f"UserAnimationScene not found in {scene_path}")
        else:
            logger.warning(f"Failed to create spec for {scene_path}")
    except Exception as e:
        logger.warning(f"Python module approach failed for scene {i+1}: {e}")
    
    # Approach 2: Using subprocess with improved command and error handling
    if not success:
        try:
            # Try with Python executable to ensure correct environment
            logger.info(f"Trying subprocess approach with Python executable for scene {i+1}")
            
            # Create a temporary script that runs the scene
            temp_dir = Path(tempfile.mkdtemp())
            temp_script = temp_dir / "run_scene.py"
            
            with open(temp_script, "w") as f:
                f.write(f"""
import sys
import os
sys.path.append("{str(project_root)}")

from manim import config
config.media_dir = "{str(output_dir)}"
config.video_dir = "{str(output_dir)}"
config.output_file = "scene_{i}"

# Import and run the scene
sys.path.append(os.path.dirname("{str(scene_path)}"))
from {scene_path.stem} import UserAnimationScene

scene = UserAnimationScene()
scene.render()
""")
            
            # Run the temporary script
            cmd = [sys.executable, str(temp_script)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            
            if proc.returncode == 0:
                logger.info(f"Subprocess execution successful for scene {i+1}")
                if output_path.exists() and output_path.stat().st_size > 0:
                    logger.info(f"Successfully rendered to {output_path} using subprocess approach")
                    success = True
            else:
                logger.warning(f"Subprocess failed: {proc.stderr}")
            
            # Clean up
            shutil.rmtree(temp_dir)
            
        except Exception as e:
            logger.warning(f"Subprocess approach failed for scene {i+1}: {e}")
    
    # If all approaches failed, create a placeholder video
    if not success:
        logger.error(f"All rendering approaches failed for scene {i+1}. Creating placeholder video.")
        create_placeholder_video(output_path, text=f"Scene {i+1} failed to render")
    
    return (i, str(output_path), success)

# ---------------------------
# Function: Render Manim Scenes
# ---------------------------
def render_manim_scenes(scene_files: List[str], output_dir: str, force_regenerate: bool = False, max_workers: int = None) -> List[str]:
    """
    Render a list of Manim scene files in parallel and return paths to the rendered video files.
    
    Args:
        scene_files: List of paths to scene files.
        output_dir: Directory where rendered videos will be saved.
        force_regenerate: If True, regenerate scenes even if they already exist.
        max_workers: Maximum number of worker processes. If None, uses the number of CPUs.
        
    Returns:
        List of paths to rendered video files.
    """
    logger.info(f"Rendering {len(scene_files)} Manim scenes in parallel")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Make sure ffmpeg is accessible to Manim by setting environment variables
    if os.path.exists(FFMPEG_PATH):
        logger.info(f"Setting FFMPEG_BINARY environment variable to {FFMPEG_PATH}")
        os.environ["FFMPEG_BINARY"] = FFMPEG_PATH
        os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH
    
    if not verify_manim_installation():
        logger.error("Manim not installed or not working properly. Creating placeholder videos.")
        # Assumes create_placeholder_videos is defined elsewhere
        return create_placeholder_videos(len(scene_files), {"output_dir": str(output_dir)})

    # Prepare the data for parallel processing
    scene_data = [(i, scene_file, output_dir, force_regenerate) for i, scene_file in enumerate(scene_files)]
    results = []
    
    # Use ProcessPoolExecutor for CPU-bound tasks
    # If max_workers is None, it will default to the number of CPUs
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_scene = {executor.submit(render_single_scene, sd): sd for sd in scene_data}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_scene):
            scene_data_item = future_to_scene[future]
            try:
                idx, output_path, success = future.result()
                results.append((idx, output_path, success))
                logger.info(f"Completed rendering scene {idx+1}/{len(scene_files)}")
            except Exception as e:
                idx = scene_data_item[0]
                logger.error(f"Scene {idx+1} generated an exception: {e}")
                traceback.print_exc()
                # Create a placeholder for failed scene
                output_path = output_dir / f"scene_{idx}.mp4"
                create_placeholder_video(output_path, text=f"Scene {idx+1} failed with error")
                results.append((idx, str(output_path), False))
    
    # Sort results by index to maintain correct order
    results.sort(key=lambda x: x[0])
    
    # Return just the output paths
    return [result[1] for result in results]

# ---------------------------
# Function: Create Timing Data
# ---------------------------
def create_timing_data(scenes: list, output_dirs: dict, duration_minutes: int = 5) -> list:
    """
    Create timing data for scene transitions.
    
    Args:
        scenes: List of scene descriptions.
        output_dirs: Dictionary with output directory paths.
        duration_minutes: Total video duration in minutes.
        
    Returns:
        List of dictionaries with timing data (start_time, end_time) for each scene.
    """
    scene_count = len(scenes)
    if scene_count == 0:
        logger.warning("No scenes provided for timing data")
        return []
    
    # Ensure minimum duration is respected
    total_duration = max(duration_minutes * 60, scene_count * 20)  # Ensure at least 20 seconds per scene
    
    timing_data = []
    
    # More sophisticated time distribution with minimum scene durations
    if scene_count == 1:
        # Single scene gets all the time
        timing_data = [{"start_time": 0, "end_time": total_duration}]
    elif scene_count == 2:
        # Two scenes get roughly equal time with intro slightly shorter
        first = total_duration * 0.45
        second = total_duration * 0.55
        timing_data = [
            {"start_time": 0, "end_time": first},
            {"start_time": first, "end_time": total_duration}
        ]
    else:
        # Distribute time with more weight to middle content
        # Introduction (15%), Content (70%), Conclusion (15%)
        first = max(total_duration * 0.15, 30)  # At least 30 seconds for intro
        last = max(total_duration * 0.15, 30)   # At least 30 seconds for conclusion
        
        # Calculate middle section, ensuring at least 45 seconds per middle section
        remaining_time = total_duration - first - last
        middle_sections = scene_count - 2
        
        # Ensure minimum middle section duration
        min_middle_section = 45  # seconds
        if remaining_time < middle_sections * min_middle_section:
            # Adjust total duration to accommodate minimums
            additional_needed = (middle_sections * min_middle_section) - remaining_time
            total_duration += additional_needed
            remaining_time += additional_needed
            logger.info(f"Adjusted total duration to {total_duration}s to ensure minimum scene durations")
        
        middle = remaining_time / middle_sections
        
        # Create section durations list
        section_durations = [first] + [middle] * middle_sections + [last]
        
        # Create timing data
        current_time = 0
        for duration in section_durations:
            timing_data.append({
                "start_time": current_time,
                "end_time": current_time + duration
            })
            current_time += duration
    
    # Log the timing data
    for i, t in enumerate(timing_data):
        logger.info(f"Scene {i}: {t['start_time']:.1f}s to {t['end_time']:.1f}s (duration: {t['end_time'] - t['start_time']:.1f}s)")
    
    return timing_data

# ---------------------------
# Function: Extend Video Duration
# ---------------------------
def extend_video_duration(video_path: str, target_duration: float, output_path: str) -> str:
    """
    Extend a video to the target duration by freezing the last frame.
    
    Args:
        video_path: Path to the input video.
        target_duration: Desired duration in seconds.
        output_path: Path to save the extended video.
        
    Returns:
        Path to the extended video if successful, otherwise None.
    """
    try:
        result = subprocess.run(
            [FFMPEG_PATH, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, check=True
        )
        original_duration = float(result.stdout.strip())
        logger.info(f"Original video duration: {original_duration:.2f}s")
        
        if original_duration >= target_duration:
            shutil.copy2(video_path, output_path)
            return output_path
        
        freeze_duration = target_duration - original_duration
        logger.info(f"Extending video by freezing last frame for {freeze_duration:.2f}s")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            last_frame_path = temp_dir_path / "last_frame.png"
            frame_time = max(0, original_duration - 0.1)
            subprocess.run([
                FFMPEG_PATH, "-y", "-ss", str(frame_time),
                "-i", video_path, "-vframes", "1",
                "-q:v", "1", str(last_frame_path)
            ], check=True)
            
            frozen_video_path = temp_dir_path / "frozen.mp4"
            subprocess.run([
                FFMPEG_PATH, "-y", "-loop", "1", "-i", str(last_frame_path),
                "-c:v", "libx264", "-t", str(freeze_duration),
                "-pix_fmt", "yuv420p", str(frozen_video_path)
            ], check=True)
            
            concat_file = temp_dir_path / "concat.txt"
            with concat_file.open("w") as f:
                f.write(f"file '{Path(video_path).resolve()}'\n")
                f.write(f"file '{frozen_video_path.resolve()}'\n")
            
            subprocess.run([
                FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_file), "-c", "copy", output_path
            ], check=True)
        
        logger.info(f"Successfully extended video to {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"Error extending video: {e}")
        return None

# ---------------------------
# Function: Merge Videos with Audio
# ---------------------------
def merge_videos_with_audio(video_files: list, timing_data: list, output_dirs: dict,
                            audio_path: str = None, duration_minutes: int = 5,
                            subtitle_path: str = None) -> str:
    """
    Merge videos with audio using ffmpeg.
    
    Args:
        video_files: List of paths to video files.
        timing_data: Timing data for synchronization.
        output_dirs: Dictionary of output directories.
        audio_path: Path to the audio file.
        duration_minutes: Target duration in minutes.
        subtitle_path: Path to subtitle file.
        
    Returns:
        Path to the final video if successful, otherwise None.
    """
    if not video_files:
        logger.error("No video files to merge")
        return None

    try:
        temp_dir = Path(output_dirs.get("temp", "temp"))
        temp_dir.mkdir(parents=True, exist_ok=True)
        list_file = temp_dir / "concat_list.txt"
        with list_file.open("w") as f:
            for video in video_files:
                f.write(f"file '{Path(video).resolve()}'\n")
        
        # First concatenate the video files
        concat_video = temp_dir / "concat_video.mp4"
        subprocess.run([
            FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(concat_video)
        ], check=True)
        logger.info(f"Videos concatenated to {concat_video}")

        # Intermediate file with audio
        audio_video = temp_dir / "audio_video.mp4"
        
        # Add audio if available
        if audio_path and Path(audio_path).exists() and Path(audio_path).stat().st_size > 0:
            logger.info(f"Adding audio narration from {audio_path}")
            
            # Get video duration
            try:
                # Use ffprobe to get video duration
                ffprobe_cmd = [
                    FFMPEG_PATH, "-v", "error", "-select_streams", "v:0", 
                    "-show_entries", "stream=duration", "-of", "csv=p=0", 
                    str(concat_video)
                ]
                logger.info(f"Running ffprobe command: {' '.join(ffprobe_cmd)}")
                result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
                video_duration = float(result.stdout.strip())
                logger.info(f"Video duration: {video_duration:.2f} seconds")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error getting video duration: {str(e)}")
                if e.stderr:
                    logger.error(f"ffprobe error output: {e.stderr}")
                logger.info("Using estimated duration from timing data")
            
            # Add audio to video
            subprocess.run([
                FFMPEG_PATH, "-y",
                "-i", str(concat_video),  # Video input
                "-i", str(audio_path),    # Audio input
                "-c:v", "copy",           # Copy video codec
                "-c:a", "aac",            # Convert audio to AAC
                "-shortest",              # Match to shortest input
                str(audio_video)
            ], check=True)
            logger.info(f"Added audio to video: {audio_video}")
            
            # Use the audio+video file for final steps
            processed_video = audio_video
        else:
            logger.warning("No valid audio file found. Using video without narration.")
            processed_video = concat_video
        
        # Final video with subtitles if available
        final_output = temp_dir / "final_with_subs.mp4"
        
        if subtitle_path and Path(subtitle_path).exists():
            logger.info(f"Adding subtitles from {subtitle_path}")
            
            # Add subtitles to the video
            subprocess.run([
                FFMPEG_PATH, "-y",
                "-i", str(processed_video),
                "-vf", f"subtitles={subtitle_path}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=4,Outline=1,Shadow=0,MarginV=30'",
                "-c:a", "copy",
                str(final_output)
            ], check=True)
            logger.info(f"Added subtitles to video: {final_output}")
            
            # Use file with subtitles as the final version
            final_source = final_output
        else:
            logger.warning("No subtitle file found. Using video without subtitles.")
            final_source = processed_video
        
        # Save final video directly to the root directory for simplicity
        root_final_video = Path(project_root) / "final_video.mp4"
        
        # Copy the final video to project root
        try:
            shutil.copy2(str(final_source), str(root_final_video))
            logger.info(f"Final video created at root: {root_final_video}")
        except Exception as e:
            logger.error(f"Failed to copy to root directory: {e}")
            # Continue with other locations even if root copy fails
        
        # Save in standard output location
        final_video = Path(output_dirs.get("videos", ".")) / "final_video.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(final_source), str(final_video))
        logger.info(f"Final video created at {final_video}")
        
        # Create a more accessible copy in the output directory (for backward compatibility)
        accessible_copy = Path("output") / "final_video.mp4"
        try:
            accessible_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(final_source), str(accessible_copy))
            logger.info(f"Created accessible copy at {accessible_copy}")
        except Exception as e:
            logger.error(f"Failed to create accessible copy: {e}")
        
        return str(final_video)
    except Exception as e:
        logger.exception(f"Error merging videos with audio: {e}")
        return None

# ---------------------------
# Function: Create Silent Audio Placeholder
# ---------------------------
def create_silent_audio_placeholder(output_path: Path, duration_seconds: float) -> Path:
    """
    Create a silent audio file as a placeholder.
    
    Args:
        output_path: Path where to save the silent audio file.
        duration_seconds: Duration in seconds.
        
    Returns:
        Path to the created silent audio file.
    """
    try:
        duration_seconds = math.ceil(duration_seconds)
        logger.info(f"Creating silent audio placeholder at {output_path} for {duration_seconds} seconds")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use ffmpeg to create a proper silent audio file
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "lavfi", 
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration_seconds),
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Created silent audio with ffmpeg at {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.warning(f"FFmpeg error creating silent audio: {e.stderr}")
            # Fallback to touching the file if ffmpeg fails
            output_path.touch()
            return output_path
            
    except Exception as e:
        logger.exception(f"Error creating silent audio placeholder: {e}")
        output_path.touch()
        return output_path

# ---------------------------
# Function: Create Placeholder Video
# ---------------------------
def create_placeholder_video(output_path: Path, text: str, duration: int = 10) -> Path:
    """
    Create a simple placeholder video with text.
    
    Args:
        output_path: Path where to save the placeholder video.
        text: Text to display in the placeholder video.
        duration: Duration of the video in seconds.
        
    Returns:
        Path to the created placeholder video.
    """
    try:
        logger.info(f"Creating placeholder video at {output_path} with text: {text}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use a simpler ffmpeg command without text overlay
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Created placeholder video at {output_path}")
        return output_path
    except Exception as e:
        logger.exception(f"Error creating placeholder video: {e}")
        # If ffmpeg fails, create an empty file as a fallback
        output_path.touch()
        return output_path

# ---------------------------
# Function: Create Placeholder Videos (Multiple)
# ---------------------------
def create_placeholder_videos(count: int, output_dirs: dict) -> list:
    """
    Create multiple placeholder videos.
    
    Args:
        count: Number of placeholder videos to create.
        output_dirs: Dictionary with output directory paths.
        
    Returns:
        List of paths to created placeholder videos.
    """
    output_dir = Path(output_dirs.get("output_dir", "output/videos"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    video_files = []
    for i in range(count):
        video_path = output_dir / f"scene_{i}.mp4"
        create_placeholder_video(video_path, text=f"Placeholder for scene {i+1}")
        video_files.append(str(video_path))
    
    logger.info(f"Created {count} placeholder videos")
    return video_files

# ---------------------------
# Function: Generate Manim Code in Parallel
# ---------------------------
def generate_manim_code_parallel(scene_data, output_dirs, dry_run=False):
    """
    Generate Manim code for a scene in parallel.
    
    Args:
        scene_data: A tuple of (index, scene_description)
        output_dirs: Dictionary with output directories
        dry_run: Whether to use placeholder content
        
    Returns:
        Tuple of (index, scene_path, success)
    """
    i, scene_description = scene_data
    try:
        scene_path = get_scene_path(i)
        logger.info(f"Generating Manim code for scene {i+1} at {scene_path}")
        
        manim_code = manim_generator.generate_manim_code(
            scene_description=scene_description,
            scene_index=i,
            output_dirs=output_dirs,
            dry_run=dry_run
        )
        
        scene_path.parent.mkdir(parents=True, exist_ok=True)
        scene_path.write_text(manim_code)
        logger.info(f"Manim code for scene {i+1} saved to {scene_path}")
        return (i, scene_path, True)
    except Exception as e:
        logger.error(f"Error generating Manim code for scene {i+1}: {str(e)}")
        return (i, get_scene_path(i), False)

# ---------------------------
# Function: Create Math Tutorial
# ---------------------------
def create_math_tutorial(topic, level="beginner", duration=5, dry_run=False, progress_callback=None, 
                        timeout=300, use_gm_api=False, gm_model="gemini-1.5-flash"):
    """
    Create a complete math tutorial from script generation to final video.
    
    Args:
        topic: The topic of the math tutorial.
        level: Difficulty level (1=beginner, 2=intermediate, 3=advanced) or string.
        duration: Duration of the video in minutes.
        dry_run: If True, use placeholder content instead of generated content.
        progress_callback: Function to call with progress updates.
        timeout: Timeout in seconds for the entire process.
        use_gm_api: Whether to use Google's Gemini API.
        gm_model: Gemini model to use.
        
    Returns:
        Path to the final video if successful, None otherwise.
    """
    try:
        start_time = time.time()
        
        # Ensure duration is within range of 3-15 minutes
        duration = max(3, min(int(duration), 15))  # Minimum 3, maximum 15 minute duration
        
        logger.info(f"Creating math tutorial: {topic}, level: {level}, duration: {duration} min, dry_run: {dry_run}")
        
        # Default progress callback if none provided
        if progress_callback is None:
            def progress_callback(progress, message):
                logger.info(f"Progress: {progress}% - {message}")
        
        # Get output directories
        output_dirs = get_project_dirs(create_dirs=True)
        logger.info(f"Retrieved project directories: {output_dirs}")
        
        # Create tutorial-specific directory using timestamp as ID
        tutorial_id = f"{int(time.time())}"
        tutorial_dir = output_dirs["tutorials"] / tutorial_id
        tutorial_dir.mkdir(exist_ok=True)
        logger.info(f"Created tutorial directory: {tutorial_dir}")
        
        # Step 1: Generate script with appropriate duration
        progress_callback(5.0, f"Generating script for '{topic}' ({duration} min)...")
        logger.info(f"Generating script for topic: {topic}, level: {level}, duration: {duration}, dry_run: {dry_run}")
        
        # Adjust target duration for script to ensure final video is at least the requested duration
        script_duration = int(duration * 1.2)  # Generate script for 20% longer than target
        logger.info(f"Using adjusted script duration of {script_duration} minutes to ensure minimum video length")
        
        script = script_generator.generate_math_tutorial_script(
            topic=topic,
            level=level,
            duration=script_duration,
            dry_run=dry_run,
            use_gm_api=use_gm_api,
            gm_model=gm_model
        )
        progress_callback(10.0, f"Script generation completed ({len(script)} characters)")
        
        # Save the script to the tutorial directory
        script_path = tutorial_dir / "script.txt"
        script_path.write_text(script)
        logger.info(f"Script saved to {script_path}")
        
        # Step 2: Extract scenes
        progress_callback(12.0, f"Extracting scene descriptions...")
        scenes = script_generator.extract_scenes_from_script(script)
        logger.info(f"Extracted {len(scenes)} scenes from script")
        progress_callback(15.0, f"Extracted {len(scenes)} scenes from script")
        
        # Step 3: Generate Manim code for each scene IN PARALLEL
        progress_callback(20.0, f"Generating animation code for {len(scenes)} scenes in parallel...")
        
        # Prepare data for parallel processing
        scene_data = [(i, scene_description) for i, scene_description in enumerate(scenes)]
        
        # Determine number of workers for scene generation
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        max_workers = min(max(1, cpu_count - 1), len(scenes))  # Use all CPUs except one
        
        scene_files = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_scene = {executor.submit(generate_manim_code_parallel, sd, output_dirs, dry_run): sd for sd in scene_data}
            
            # Process results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_scene)):
                progress_percentage = 20.0 + ((i + 1) / len(scenes) * 15.0)
                try:
                    idx, scene_path, success = future.result()
                    if success:
                        scene_files.append(scene_path)
                    progress_callback(progress_percentage, f"Generated code for scene {idx+1}/{len(scenes)}")
                except Exception as e:
                    logger.error(f"Error in scene generation executor: {e}")
        
        # Sort scene files by index to maintain correct order
        scene_files.sort(key=lambda p: int(p.stem.split('_')[-1]))
        logger.info(f"Generated {len(scene_files)} scene files in parallel")
        
        # Step 4: Create timing data 
        progress_callback(35.0, f"Creating timing data for video...")
        timing_data = create_timing_data(scenes, output_dirs, duration)
        progress_callback(40.0, f"Created timing data for {len(timing_data)} scenes")
        
        # Step 5: Render scenes
        progress_callback(45.0, f"Rendering scene animations in parallel...")
        video_files = render_manim_scenes(scene_files, output_dirs["videos"], max_workers=max_workers)
        progress_callback(70.0, f"Rendered {len(video_files)} scene videos in parallel")
        
        # Step 6: Generate audio narration
        progress_callback(75.0, f"Generating audio narration...")
        narrator_script = script_generator.clean_script_for_narration(script)
        audio_path = generate_audio_narration(
            text=narrator_script,
            filename="narration.mp3",
            dry_run=dry_run
        )
        progress_callback(80.0, f"Generated audio narration")
        
        # Step 7: Generate subtitle file
        progress_callback(85.0, f"Generating subtitles...")
        subtitle_path = generate_subtitle_file(script, output_dirs)
        progress_callback(90.0, f"Generated subtitles")
        
        # Step 8: Merge videos with audio
        progress_callback(95.0, f"Assembling final video...")
        final_video = merge_videos_with_audio(
            video_files=video_files,
            timing_data=timing_data,
            output_dirs=output_dirs,
            audio_path=audio_path,
            duration_minutes=duration,
            subtitle_path=subtitle_path
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Create a copy of the final video in the tutorial directory
        if final_video and Path(final_video).exists():
            tutorial_video = tutorial_dir / "tutorial.mp4"
            shutil.copy2(final_video, tutorial_video)
            progress_callback(100.0, f"Tutorial video completed in {total_time:.1f} seconds")
            logger.info(f"Tutorial completion time: {total_time:.1f} seconds")
            return str(tutorial_video)
        else:
            logger.error("Failed to create final video")
            progress_callback(100.0, f"Failed to create final video")
            return None
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error creating math tutorial: {str(e)}")
        logger.debug(f"Error details: {error_details}")
        if progress_callback:
            progress_callback(100.0, f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # This module is intended to be imported and its functions called from other scripts.
    pass
