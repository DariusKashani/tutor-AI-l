#!/usr/bin/env python3
"""
Test script for the video generator.
This script tests the video generation process locally.
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
        logging.FileHandler('logs/test_video_generator.log')
    ]
)
logger = logging.getLogger('test_video_generator')

# Add the project root to the Python path
project_root = Path(__file__).parent.resolve()
sys.path.append(str(project_root))

# Import the necessary modules
from src.backend.script_generator import (
    generate_script, 
    generate_math_tutorial_script, 
    extract_scenes_from_script, 
    extract_timing_from_script, 
    clean_script_for_narration
)
from src.backend.manim_generator import generate_manim_code
from src.backend.video_generator import (
    create_placeholder_video,
    render_manim_scenes,
    create_timing_data,
    merge_videos_with_audio,
    generate_subtitle_file,
    generate_audio_narration
)
from config import get_project_dirs, get_script_path, get_scene_path, get_final_video_path

def test_video_generation(topic="Simple Addition", duration_minutes=1, sophistication_level=1, dry_run=True, use_generative_manim=True):
    """
    Test the entire video generation process.
    
    Args:
        topic: The topic of the video.
        duration_minutes: The duration of the video in minutes.
        sophistication_level: The sophistication level of the video (1-5).
        dry_run: If True, use placeholder content instead of generating real content.
        use_generative_manim: If True, use the generative-manim approach for code generation.
    
    Returns:
        Path to the final video if successful, None otherwise.
    """
    try:
        logger.info(f"Starting test video generation for topic: {topic}")
        logger.info(f"Parameters: duration={duration_minutes}min, sophistication_level={sophistication_level}, dry_run={dry_run}, use_generative_manim={use_generative_manim}")
        
        # Get output directories
        output_dirs = get_project_dirs(create_dirs=True)
        logger.info(f"Output directories: {output_dirs}")
        
        start_time = time.time()
        
        # Step 1: Generate script
        logger.info("Step 1: Generating script...")
        script = generate_script(
            topic=topic,
            duration_minutes=duration_minutes,
            sophistication_level=sophistication_level,
            output_dirs=output_dirs,
            dry_run=dry_run
        )
        logger.info(f"Script generated with {len(script)} characters")
        
        # Step 2: Extract scenes from script
        logger.info("Step 2: Extracting scenes from script...")
        scenes = extract_scenes_from_script(script)
        logger.info(f"Extracted {len(scenes)} scenes from script")
        
        # Step 3: Generate Manim code for each scene
        logger.info("Step 3: Generating Manim code for each scene...")
        scene_files = []
        for i, scene_description in enumerate(scenes):
            scene_path = get_scene_path(i)
            logger.info(f"Generating Manim code for scene {i+1} at {scene_path}")
            
            manim_code = generate_manim_code(
                scene_description=scene_description,
                scene_index=i,
                output_dirs=output_dirs,
                dry_run=dry_run
            )
            
            scene_path.parent.mkdir(parents=True, exist_ok=True)
            scene_path.write_text(manim_code)
            scene_files.append(scene_path)
            logger.info(f"Manim code for scene {i+1} saved to {scene_path}")
            
            # Create a backup copy of the scene file
            backup_path = Path(f"output/scenes/backup_scene_{i}.py")
            backup_path.write_text(manim_code)
            logger.info(f"Backup of scene {i+1} saved to {backup_path}")
        
        # Step 4: Create timing data
        logger.info("Step 4: Creating timing data...")
        timing_data = create_timing_data(scenes, output_dirs, duration_minutes)
        logger.info(f"Created timing data for {len(timing_data)} scenes")
        
        # Step 5: Render scenes
        logger.info("Step 5: Rendering scenes...")
        video_files = render_manim_scenes(scene_files, output_dirs["videos"])
        logger.info(f"Rendered {len(video_files)} scene videos")
        
        # Step 6: Generate audio narration
        logger.info("Step 6: Generating audio narration...")
        audio_path = generate_audio_narration(
            text=script,
            filename="narration.mp3",
            dry_run=dry_run
        )
        logger.info(f"Generated audio narration at {audio_path}")
        
        # Step 7: Generate subtitle file
        logger.info("Step 7: Generating subtitle file...")
        subtitle_path = generate_subtitle_file(script, output_dirs)
        logger.info(f"Generated subtitle file at {subtitle_path}")
        
        # Step 8: Merge videos with audio
        logger.info("Step 8: Merging videos with audio...")
        final_video = merge_videos_with_audio(
            video_files=video_files,
            timing_data=timing_data,
            output_dirs=output_dirs,
            audio_path=audio_path,
            duration_minutes=duration_minutes,
            subtitle_path=subtitle_path
        )
        
        end_time = time.time()
        logger.info(f"Video generation completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Final video: {final_video}")
        
        # Verify the final video exists and has content
        if final_video and Path(final_video).exists() and Path(final_video).stat().st_size > 0:
            logger.info(f"Verified final video exists at {final_video} with size {Path(final_video).stat().st_size} bytes")
            return final_video
        else:
            if final_video:
                logger.error(f"Final video was reported as {final_video} but file does not exist or is empty")
            return None
    except Exception as e:
        logger.exception(f"Error in test_video_generation: {e}")
        return None

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Test video generation')
    parser.add_argument('--topic', type=str, default="Simple Addition", help='Topic of the video')
    parser.add_argument('--duration', type=int, default=1, help='Duration of the video in minutes')
    parser.add_argument('--level', type=int, default=1, help='Sophistication level (1-5)')
    parser.add_argument('--dry-run', action='store_true', help='Use placeholder content')
    parser.add_argument('--no-generative-manim', action='store_true', help='Do not use generative-manim approach')
    args = parser.parse_args()
    
    # Run the test
    final_video = test_video_generation(
        topic=args.topic,
        duration_minutes=args.duration,
        sophistication_level=args.level,
        dry_run=args.dry_run,
        use_generative_manim=not args.no_generative_manim
    )
    
    if final_video:
        print(f"\nFinal video generated at: {final_video}")
        print(f"Video generation completed successfully!")
    else:
        print(f"\nVideo generation failed!") 