"""
Centralized configuration for all paths in the math tutorial generator.
"""

import os
from pathlib import Path

# Base directories - the script is in src/ directory, so we need to go up one level for project root
ROOT_DIR = Path(__file__).parent.parent.resolve()
STORED_DATA_DIR = ROOT_DIR / "stored_data"
OUTPUT_DIR = ROOT_DIR / "output"

# Get paths to key files
MANIM_KNOWLEDGE_PATH = STORED_DATA_DIR / "manim_knowledge.txt"

# Create and get project directories
def get_project_dirs(create_dirs=True):
    """Get all project directories."""
    
    # Define all directory paths
    paths = {
        "project": OUTPUT_DIR,
        "scenes": OUTPUT_DIR / "scenes",
        "videos": OUTPUT_DIR / "videos",
        "audio": OUTPUT_DIR / "audio",
        "data": OUTPUT_DIR / "data",
        "temp": OUTPUT_DIR / "temp"
    }
    
    # Create directories if requested
    if create_dirs:
        for dir_path in paths.values():
            os.makedirs(dir_path, exist_ok=True)
    
    return paths

# Helper functions for specific file paths
def get_scene_path(scene_index):
    """Get path to a scene file."""
    return OUTPUT_DIR / "scenes" / f"scene_{scene_index}.py"

def get_script_path():
    """Get path to the full script file."""
    return OUTPUT_DIR / "data" / "full_script.txt"

def get_narrator_script_path():
    """Get path to the narrator script file."""
    return OUTPUT_DIR / "audio" / "narrator_script.txt"

def get_audio_path(filename="narration.mp3"):
    """Get path to the audio file."""
    return OUTPUT_DIR / "audio" / filename

def get_timing_data_path():
    """Get path to the timing data file."""
    return OUTPUT_DIR / "data" / "script_timing.json"

def get_video_path(scene_index):
    """Get path to a scene video file."""
    return OUTPUT_DIR / "videos" / f"scene_{scene_index}.mp4"

def get_processed_video_path(scene_index):
    """Get path to a processed video file."""
    return OUTPUT_DIR / "temp" / f"processed_{scene_index}.mp4"

def get_final_video_path():
    """Get path to the final video file."""
    return OUTPUT_DIR / "final_math_lesson.mp4"

# Initialize paths if this module is imported
output_dirs = get_project_dirs()

# Print configuration information if run directly
if __name__ == "__main__":
    print("Math Tutorial Generator Configuration")
    print(f"Root directory: {ROOT_DIR}")
    print(f"Stored data directory: {STORED_DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("\nProject directories:")
    for name, path in get_project_dirs(create_dirs=False).items():
        print(f"  {name}: {path}")
        print(f"    exists: {path.exists()}")
    
    print(f"\nManim knowledge file: {MANIM_KNOWLEDGE_PATH}")
    print(f"  exists: {MANIM_KNOWLEDGE_PATH.exists()}")