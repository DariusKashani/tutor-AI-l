"""
Integration module for test video generation.
This module provides functions to run the test_video_generator from the web API.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_video_integration.log')
    ]
)
logger = logging.getLogger('test_video_integration')

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

# Import the test video generation function
from test_video_generator import test_video_generation

def run_test_video_and_return_path(topic="Simple Triangle", duration_minutes=1, sophistication_level=1, dry_run=False):
    """
    Run the test video generation and return the path to the video and a status message.
    
    Args:
        topic: The topic of the video.
        duration_minutes: The duration of the video in minutes.
        sophistication_level: The sophistication level of the video (1-5).
        dry_run: If True, use placeholder content instead of generating real content.
    
    Returns:
        Tuple of (video_path, message).
    """
    try:
        logger.info(f"Starting test video generation for topic: {topic}")
        logger.info(f"Parameters: duration={duration_minutes}min, sophistication_level={sophistication_level}, dry_run={dry_run}")
        
        start_time = time.time()
        
        # Run the test video generation
        final_video = test_video_generation(
            topic=topic,
            duration_minutes=duration_minutes,
            sophistication_level=sophistication_level,
            dry_run=dry_run
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check all possible video locations
        possible_paths = [
            Path(project_root) / "final_video.mp4",  # Root directory
            Path("final_video.mp4"),                 # Current directory
            Path("output") / "final_video.mp4",      # Output directory
            Path("output/videos") / "final_video.mp4"  # Output videos directory
        ]
        
        # If a specific path was returned, add it to the list
        if final_video:
            possible_paths.insert(0, Path(final_video))
        
        # Find the first existing video path
        video_path = None
        for path in possible_paths:
            if path.exists():
                video_path = path
                logger.info(f"Found video at: {video_path}")
                break
        
        if video_path:
            size_kb = video_path.stat().st_size / 1024
            message = f"Video generated successfully in {duration:.2f} seconds. Size: {size_kb:.2f} KB"
            logger.info(message)
            
            # If the video is not in the root, try to copy it there
            root_path = Path(project_root) / "final_video.mp4"
            if not root_path.exists() and video_path != root_path:
                try:
                    import shutil
                    shutil.copy2(str(video_path), str(root_path))
                    logger.info(f"Copied video to root directory: {root_path}")
                    return str(root_path), message
                except Exception as e:
                    logger.warning(f"Could not copy to root directory: {e}")
            
            return str(video_path), message
        else:
            message = f"Failed to generate video after {duration:.2f} seconds. Could not find video file."
            logger.error(message)
            return None, message
    except Exception as e:
        logger.exception(f"Error in run_test_video_and_return_path: {e}")
        return None, f"Error: {str(e)}"

if __name__ == "__main__":
    # For testing directly from this module
    video_path, message = run_test_video_and_return_path()
    print(f"Result: {message}")
    print(f"Video path: {video_path}") 