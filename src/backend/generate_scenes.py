import sys
import os
import subprocess
import concurrent.futures
from pathlib import Path
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve project and repo paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
# Add both generative-manim and your src directory to the Python path
sys.path.insert(0, os.path.join(project_root, "generative-manim"))
sys.path.insert(0, os.path.join(project_root, "src"))  # ← this fixes the 'No module named backend' issue

generative_manim_path = os.path.join(project_root, "generative-manim")

# Add generative-manim repo to path
sys.path.insert(0, generative_manim_path)
print("Added to sys.path:", generative_manim_path)

# Import code generation logic directly from the API route module
try:
    from api.routes import code_generation
except ImportError as e:
    raise ImportError(f"Import failed. Ensure 'generative-manim' is correctly cloned and in your path: {e}")

# Load API keys
load_dotenv(os.path.join(project_root, ".env"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set your OPENAI_API_KEY in the .env file")


def generate_and_save_scene(i: int, description: str, scenes_dir: Path):
    """Generates Manim code from description and saves to file."""
    try:
        logger.info(f"Generating Manim code for scene {i}")
        result = code_generation.generate_code(description)
        manim_code = result["code"]
        scene_class = result.get("file_class", "GenScene")
        scene_file_name = result.get("file_name", f"scene_{i}")

        scene_file_path = scenes_dir / f"{scene_file_name}.py"
        scene_file_path.write_text(manim_code)

        logger.info(f"Scene {i} code saved to {scene_file_path}")
        return (scene_file_path, scene_class)
    except Exception as e:
        logger.error(f"Failed generating code for scene {i}: {e}")
        return None


def render_scene(scene_file: Path, scene_class: str, output_dir: Path):
    """Render a single Manim scene file."""
    try:
        cmd = [
            sys.executable, "-m", "manim",
            str(scene_file), scene_class,
            "-o", scene_file.stem,
            "--media_dir", str(output_dir.parent)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        output_path = output_dir / f"{scene_file.stem}.mp4"
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"Successfully rendered {output_path}")
            return str(output_path)

        # Check fallback outputs
        for output in output_dir.glob(f"*{scene_file.stem}*.mp4"):
            if output.exists() and output.stat().st_size > 0:
                logger.info(f"Alternative rendered file: {output}")
                return str(output)

        raise FileNotFoundError(f"No output file found for scene: {scene_file.stem}")
    except Exception as e:
        logger.error(f"Rendering failed for {scene_file.stem}: {e}")
        return None


def generate_and_render_all_scenes(descriptions, base_output_dir="../../output", dry_run=False):
    base_output_dir = Path(base_output_dir)
    scenes_dir = base_output_dir / "generated_scenes"
    render_output_dir = base_output_dir / "rendered_scenes"

    scenes_dir.mkdir(parents=True, exist_ok=True)
    render_output_dir.mkdir(parents=True, exist_ok=True)

    generation_results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(generate_and_save_scene, i, desc, scenes_dir)
            for i, desc in enumerate(descriptions)
        ]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                generation_results.append(result)

    if dry_run:
        logger.info("Dry run enabled; skipping rendering.")
        return [str(scene[0]) for scene in generation_results]

    rendered_paths = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(render_scene, scene_file, scene_class, render_output_dir)
            for scene_file, scene_class in generation_results
        ]
        for future in concurrent.futures.as_completed(futures):
            rendered_path = future.result()
            if rendered_path:
                rendered_paths.append(rendered_path)

    return rendered_paths


if __name__ == "__main__":
    scene_descriptions = [
        "A red circle moves horizontally across the screen.",
        "A green square rotating around its center.",
        "A triangle transforms into a star."
    ]

    results = generate_and_render_all_scenes(scene_descriptions)
    print("\nRendered Scenes:")
    for path in results:
        print(path)
