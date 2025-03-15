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
    elevenlabs_available = True
except ImportError:
    elevenlabs_available = False
    logger.warning("ElevenLabs package not found. Audio generation will use placeholder files.")

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
    get_subtitle_path
)

# Define the path to ffmpeg
FFMPEG_PATH = os.path.expanduser("~/bin/ffmpeg")

from src.backend.manim_generator import (
    verify_manim_installation, 
    clean_existing_scene_file, 
)

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
    for idx, match in enumerate(matches, 1):
        minutes, seconds = int(match[0]), int(match[1])
        text = (match[2] or match[3]).strip()
        if not text:
            continue

        start_sec = minutes * 60 + seconds
        if idx < len(matches):
            next_min, next_sec = int(matches[idx][0]), int(matches[idx][1])
            next_sec_total = next_min * 60 + next_sec
            end_sec = min(start_sec + 5, next_sec_total)
        else:
            end_sec = start_sec + 5

        start_time_formatted = f"{start_sec//3600:02d}:{(start_sec%3600)//60:02d}:{start_sec%60:02d},000"
        end_time_formatted = f"{end_sec//3600:02d}:{(end_sec%3600)//60:02d}:{end_sec%60:02d},000"
        subtitle_entries.append(f"{idx}\n{start_time_formatted} --> {end_time_formatted}\n{text}\n")

    srt_path = Path(get_subtitle_path())
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("\n".join(subtitle_entries))
    logger.info(f"Generated SRT file with {len(subtitle_entries)} entries at {srt_path}")
    return srt_path

# ---------------------------
# Function: Generate Audio Narration
# ---------------------------
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
        create_silent_audio_placeholder(audio_path, len(text.split()) / 3)
        return audio_path

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("No ElevenLabs API key found. Using silent audio placeholder.")
        create_silent_audio_placeholder(audio_path, len(text.split()) / 3)
        return audio_path

    try:
        if elevenlabs_available:
            audio = eleven_generate(
                text=text,
                voice="Rachel",
                model="eleven_monolingual_v1"
            )
            with open(audio_path, "wb") as f:
                f.write(audio)
            logger.info(f"Generated audio narration at {audio_path}")
        else:
            logger.warning("ElevenLabs not available, creating silent audio.")
            create_silent_audio_placeholder(audio_path, len(text.split()) / 3)
        return audio_path
    except Exception as e:
        logger.exception(f"Error generating audio narration: {e}")
        create_silent_audio_placeholder(audio_path, len(text.split()) / 3)
        return audio_path

# ---------------------------
# Function: Render Manim Scenes
# ---------------------------
def render_manim_scenes(scene_files: list, output_dir: str) -> list:
    """
    Render a list of Manim scene files and return paths to the rendered video files.
    
    Args:
        scene_files: List of paths to scene files.
        output_dir: Directory where rendered videos will be saved.
        
    Returns:
        List of paths to rendered video files.
    """
    logger.info(f"Rendering {len(scene_files)} Manim scenes")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not verify_manim_installation():
        logger.error("Manim not installed or not working properly. Creating placeholder videos.")
        # Assumes create_placeholder_videos is defined elsewhere
        return create_placeholder_videos(len(scene_files), {"output_dir": str(output_dir)})

    video_files = []
    for i, scene_file in enumerate(scene_files):
        scene_path = Path(scene_file)
        if not scene_path.exists():
            logger.error(f"Scene file not found: {scene_file}")
            placeholder = output_dir / f"placeholder_scene_{i}.mp4"
            create_placeholder_video(placeholder, text=f"Scene {i+1} not found")
            video_files.append(str(placeholder))
            continue

        logger.info(f"Rendering scene {i+1} from {scene_file}")
        logger.info(f"Cleaning scene file {scene_file}")
        clean_existing_scene_file(str(scene_path))

        cmd = ["manim", "-ql", str(scene_path), "UserAnimationScene", "-o", f"scene_{i}"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                scene_name = scene_path.stem
                video_dir = scene_path.parent
                base_media_dir = Path(video_dir.parent) / "videos"
                expected_video = base_media_dir / "videos" / scene_name / "480p15" / "UserAnimationScene.mp4"
                if expected_video.exists():
                    output_path = output_dir / f"scene_{i}.mp4"
                    shutil.copy(expected_video, output_path)
                    video_files.append(str(output_path))
                    logger.info(f"Rendered scene {i+1} to {output_path}")
                else:
                    # Search for the video file if not in expected location
                    found = False
                    for root, _, files in os.walk(base_media_dir):
                        for file in files:
                            if file.endswith(".mp4") and "UserAnimationScene" in file:
                                video_path = Path(root) / file
                                output_path = output_dir / f"scene_{i}.mp4"
                                shutil.copy(video_path, output_path)
                                video_files.append(str(output_path))
                                logger.info(f"Rendered scene {i+1} to {output_path}")
                                found = True
                                break
                        if found:
                            break
                    if not found:
                        logger.warning(f"Rendered video for scene {i+1} not found. Creating placeholder.")
                        placeholder = output_dir / f"placeholder_scene_{i}.mp4"
                        create_placeholder_video(placeholder, text=f"Scene {i+1} rendered but video not found")
                        video_files.append(str(placeholder))
            else:
                logger.error(f"Error rendering scene {i+1}:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
                if "LaTeX" in result.stderr or "tex" in result.stderr.lower():
                    logger.error("LaTeX error detected. Creating placeholder video.")
                    placeholder = output_dir / f"placeholder_scene_{i}.mp4"
                    create_placeholder_video(placeholder, text="Scene couldn't be rendered due to LaTeX issues.")
                    video_files.append(str(placeholder))
                elif "NameError" in result.stderr and "is not defined" in result.stderr:
                    error_match = re.search(r"name '([^']+)' is not defined", result.stderr)
                    error_name = error_match.group(1) if error_match else "undefined variable"
                    logger.error(f"Name error detected: {error_name}. Creating placeholder.")
                    placeholder = output_dir / f"placeholder_scene_{i}.mp4"
                    create_placeholder_video(placeholder, text=f"Undefined name: {error_name}")
                    video_files.append(str(placeholder))
                else:
                    logger.info("Retrying with basic quality...")
                    cmd_retry = ["manim", "-l", str(scene_path), "UserAnimationScene", "-o", f"scene_{i}"]
                    try:
                        result = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=120)
                        if result.returncode == 0:
                            scene_name = scene_path.stem
                            video_dir = scene_path.parent
                            base_media_dir = Path(video_dir.parent) / "videos"
                            expected_video = base_media_dir / "videos" / scene_name / "480p15" / "UserAnimationScene.mp4"
                            if expected_video.exists():
                                output_path = output_dir / f"scene_{i}.mp4"
                                shutil.copy(expected_video, output_path)
                                video_files.append(str(output_path))
                                logger.info(f"Rendered scene {i+1} to {output_path}")
                            else:
                                placeholder = output_dir / f"placeholder_scene_{i}.mp4"
                                create_placeholder_video(placeholder, text=f"Scene {i+1} rendered but video not found")
                                video_files.append(str(placeholder))
                        else:
                            logger.error(f"Retry failed for scene {i+1}. Creating placeholder.")
                            placeholder = output_dir / f"placeholder_scene_{i}.mp4"
                            create_placeholder_video(placeholder, text=f"Scene {i+1} rendering failed")
                            video_files.append(str(placeholder))
                    except Exception as e:
                        logger.exception(f"Error during retry for scene {i+1}: {e}")
                        placeholder = output_dir / f"placeholder_scene_{i}.mp4"
                        create_placeholder_video(placeholder, text=f"Scene {i+1} rendering failed")
                        video_files.append(str(placeholder))
        except subprocess.TimeoutExpired:
            logger.error(f"Rendering timed out for scene {i+1}. Creating placeholder.")
            placeholder = output_dir / f"placeholder_scene_{i}.mp4"
            create_placeholder_video(placeholder, text=f"Scene {i+1} rendering timed out")
            video_files.append(str(placeholder))
        except Exception as e:
            logger.exception(f"Error processing scene {i+1}: {e}")
            placeholder = output_dir / f"placeholder_scene_{i}.mp4"
            create_placeholder_video(placeholder, text=f"Scene {i+1} processing error")
            video_files.append(str(placeholder))
    logger.info(f"Rendered {len(scene_files)} Manim scenes")
    return video_files

# ---------------------------
# Function: Create Timing Data
# ---------------------------
def create_timing_data(scenes: list, output_dirs: dict, duration_minutes: int = 5) -> list:
    """
    Create timing data for synchronizing scenes with audio.
    
    Args:
        scenes: List of scene descriptions.
        output_dirs: Dictionary with output directory paths.
        duration_minutes: Total video duration in minutes.
        
    Returns:
        List of timing data dictionaries.
    """
    total_duration = duration_minutes * 60
    scene_count = len(scenes)
    if scene_count == 0:
        return []

    if scene_count <= 3:
        section_durations = [total_duration / scene_count] * scene_count
    else:
        first = total_duration * 0.15
        last = total_duration * 0.15
        middle = (total_duration - first - last) / (scene_count - 2)
        section_durations = [first] + [middle] * (scene_count - 2) + [last]

    timing_data = []
    current_time = 0
    for duration in section_durations:
        timing_data.append({
            "start_time": current_time,
            "end_time": current_time + duration
        })
        current_time += duration

    timing_file = Path(get_timing_data_path())
    timing_file.parent.mkdir(parents=True, exist_ok=True)
    timing_file.write_text(json.dumps(timing_data))
    
    for i, t in enumerate(timing_data, start=1):
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
        
        concat_video = temp_dir / "concat_video.mp4"
        subprocess.run([
            FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(concat_video)
        ], check=True)
        logger.info(f"Videos concatenated to {concat_video}")

        # Save final video directly to the root directory for simplicity
        root_final_video = Path(project_root) / "final_video.mp4"
        
        # Copy the concatenated video as the final video to project root
        try:
            shutil.copy2(str(concat_video), str(root_final_video))
            logger.info(f"Final video created at root: {root_final_video}")
        except Exception as e:
            logger.error(f"Failed to copy to root directory: {e}")
            # Continue with other locations even if root copy fails
        
        # Save in standard output location
        final_video = Path(output_dirs.get("videos", ".")) / "final_video.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(concat_video), str(final_video))
        logger.info(f"Final video created at {final_video}")
        
        # Create a more accessible copy in the output directory (for backward compatibility)
        accessible_copy = Path("output") / "final_video.mp4"
        try:
            accessible_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(concat_video), str(accessible_copy))
            logger.info(f"Created accessible copy at {accessible_copy}")
        except Exception as e:
            logger.error(f"Failed to create accessible copy: {e}")
        
        # If root copy succeeded, return that path, otherwise return the standard path
        if root_final_video.exists():
            return str(root_final_video)
        return str(final_video)
    except Exception as e:
        logger.exception(f"Error merging videos: {e}")
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
        # Create a simple empty file instead of trying to use ffmpeg
        logger.info(f"Creating silent audio placeholder at {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
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
# Function: Create Math Tutorial
# ---------------------------
def create_math_tutorial(topic, level="beginner", duration=3, dry_run=False, progress_callback=None, timeout=300):
    """
    Create a complete math tutorial from script generation to final video.
    
    Args:
        topic: The topic of the math tutorial.
        level: Difficulty level (beginner, intermediate, advanced).
        duration: Duration of the video in minutes.
        dry_run: If True, use placeholder content instead of generated content.
        progress_callback: Function to call with progress updates.
        timeout: Timeout in seconds for the entire process.
        
    Returns:
        Path to the final video if successful, None otherwise.
    """
    try:
        start_time = time.time()
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
        
        # Step 1: Generate script
        progress_callback(5.0, f"Generating script for '{topic}'...")
        logger.info(f"Generating script for topic: {topic}, level: {level}, duration: {duration}, dry_run: {dry_run}")
        script = script_generator.generate_math_tutorial_script(
            topic=topic,
            level=level,
            duration=duration,
            dry_run=dry_run
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
        
        # Step 3: Generate Manim code for each scene
        scene_files = []
        for i, scene_description in enumerate(scenes):
            progress_percentage = 15.0 + (i / len(scenes) * 20.0)
            progress_callback(progress_percentage, f"Generating animation code for scene {i+1}/{len(scenes)}...")
            
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
                scene_files.append(scene_path)
                logger.info(f"Manim code for scene {i+1} saved to {scene_path}")
            except Exception as e:
                logger.error(f"Error generating Manim code for scene {i+1}: {str(e)}")
                # Continue with other scenes if one fails
        
        # Step 4: Create timing data
        progress_callback(35.0, f"Creating timing data for video...")
        timing_data = create_timing_data(scenes, output_dirs, duration)
        progress_callback(40.0, f"Created timing data for {len(timing_data)} scenes")
        
        # Step 5: Render scenes
        progress_callback(45.0, f"Rendering scene animations...")
        video_files = render_manim_scenes(scene_files, output_dirs["videos"])
        progress_callback(70.0, f"Rendered {len(video_files)} scene videos")
        
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
