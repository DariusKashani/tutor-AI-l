import time
import os
import logging
from pathlib import Path
from src.backend.video_generator import create_math_tutorial

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_video_fixes')

def test_video_generation():
    """Test the fixed video generation system with a specific topic and parameters."""
    # Parameters for testing
    topic = "The Pythagorean Theorem"  # Math topic
    level = 2  # Using level-based sophistication (1=beginner, 2=intermediate, 3=advanced)
    duration = 5  # Duration in minutes (increased for longer video test)
    
    # Ensure ELEVENLABS_API_KEY is set for voice generation
    if not os.environ.get("ELEVENLABS_API_KEY"):
        api_key = input("Please enter your ElevenLabs API key for voice generation: ")
        os.environ["ELEVENLABS_API_KEY"] = api_key
    
    logger.info(f"Starting video generation test with topic: {topic}, level: {level}, duration: {duration}min")
    
    start_time = time.time()
    
    # Progress callback to track video generation progress
    def progress_callback(progress, message):
        logger.info(f"Progress: {progress:.1f}% - {message}")
    
    # Create the math tutorial with our parameters
    video_path = create_math_tutorial(
        topic=topic,
        level=level,
        duration=duration,
        dry_run=False,  # False to use real generation, True for placeholders
        progress_callback=progress_callback
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Check results
    if video_path and Path(video_path).exists():
        size_bytes = Path(video_path).stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        logger.info(f"Video generation completed successfully in {duration:.2f} seconds")
        logger.info(f"Video file: {video_path}")
        logger.info(f"Video size: {size_mb:.2f} MB")
        logger.info("Test completed successfully!")
        return True
    else:
        logger.error(f"Video generation failed after {duration:.2f} seconds")
        return False

if __name__ == "__main__":
    test_video_generation() 