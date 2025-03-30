import os
import sys
import json
import uuid
import threading
import random
import string
import logging
import time
import traceback
from glob import glob
from pathlib import Path

from flask import Blueprint, Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ---------------------------
# External Module Imports
# ---------------------------
from src.backend.manim_generator import (
    generate_manim_code, 
    clean_existing_scene_file, 
    render_scene
)
from src.backend import video_generator, manim_generator, script_generator
from src.backend.task_manager import task_manager
from config import get_project_dirs

# ---------------------------
# Logging Setup
# ---------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "api.log")
    ]
)
logger = logging.getLogger("api")

# ---------------------------
# Add Project Root to Python Path
# ---------------------------
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.append(str(project_root))

# ---------------------------
# Flask Blueprint Setup
# ---------------------------
api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------------------------
# Endpoint: Generate Tutorial
# ---------------------------
@api_bp.route("/generate", methods=["POST"])
def generate_tutorial():
    """Start generating a tutorial video."""
    try:
        logger.info("Received request to generate tutorial")
        data = request.get_json()
        logger.info(f"Request data: {data}")

        # Validate required parameters
        for param in ["topic", "level", "duration"]:
            if param not in data:
                logger.warning(f"Missing required parameter: {param}")
                return jsonify({"error": f"Missing required parameter: {param}"}), 400

        topic = data["topic"]
        level = data.get("level", "beginner")
        duration = int(data.get("duration", 3))
        api_key = data.get("api_key")
        dry_run = data.get("dry_run", False)

        if not topic:
            logger.warning("Empty topic provided")
            return jsonify({"error": "Topic cannot be empty"}), 400

        if not (1 <= duration <= 10):
            logger.warning(f"Invalid duration: {duration}")
            return jsonify({"error": "Duration must be between 1 and 10 minutes"}), 400

        logger.info(f"Starting tutorial generation for '{topic}', level: {level}, duration: {duration}min")
        task_id = generate_tutorial_task(topic, level, duration, api_key, dry_run)
        logger.info(f"Created task with ID: {task_id}")

        return jsonify({"task_id": task_id})
    except Exception as e:
        logger.exception("Error in generate_tutorial endpoint")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


def generate_tutorial_task(topic, level, duration, api_key=None, dry_run=False):
    """
    Create and run a tutorial generation task in a background thread.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"[TASK:{task_id}] Creating tutorial task for topic: {topic}")

    # Create and update task tracking
    task_manager.create_task(task_id, "tutorial", {
        "topic": topic,
        "level": level,
        "duration": duration,
        "dry_run": dry_run
    })
    task_manager.update_task(task_id, status="processing", progress=0,
                             message=f"Initializing tutorial generation for '{topic}'...")

    def task_thread():
        try:
            logger.info(f"[TASK:{task_id}] Starting tutorial generation thread")
            if api_key:
                logger.info(f"[TASK:{task_id}] Using custom API key")
                os.environ["OPENAI_API_KEY"] = api_key

            def progress_callback(progress, message):
                logger.info(f"[TASK:{task_id}] Progress {progress}%: {message}")
                task_manager.update_task(task_id, progress=progress, message=message)

            timeout_seconds = 300  # 5 minutes timeout
            logger.info(f"[TASK:{task_id}] Starting video generation with timeout {timeout_seconds}s")

            result = video_generator.create_math_tutorial(
                topic=topic,
                level=level,
                duration=duration,
                dry_run=dry_run,
                progress_callback=progress_callback,
                timeout=timeout_seconds
            )

            if result:
                logger.info(f"[TASK:{task_id}] Tutorial generation completed: {result}")
                task_manager.update_task(task_id, status="completed", progress=100,
                                         message=f"Tutorial generation completed for '{topic}'",
                                         result=str(result))
            else:
                logger.error(f"[TASK:{task_id}] Tutorial generation failed: No result returned")
                task_manager.update_task(task_id, status="error", progress=100,
                                         message=f"Tutorial generation failed for '{topic}': No result returned",
                                         error="No result returned from the video generator")
        except Exception as e:
            logger.exception(f"[TASK:{task_id}] Error in tutorial generation")
            task_manager.update_task(task_id, status="error", progress=100,
                                     message=f"Error in tutorial generation: {str(e)}",
                                     error=str(e))

    thread = threading.Thread(target=task_thread, daemon=True)
    thread.start()
    return task_id

# ---------------------------
# Endpoint: Get Task Status
# ---------------------------
@api_bp.route("/status/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Return the status of a task."""
    logger.info(f"Status check for task {task_id}")
    active_tasks = list(task_manager.get_all_tasks().keys())
    task = task_manager.get_task(task_id)
    if not task:
        logger.warning(f"Task {task_id} not found")
        return jsonify({
            "error": "Task not found",
            "message": "The requested task was not found in the task manager.",
            "active_tasks": active_tasks
        }), 404

    response = {
        "task_id": task_id,
        "status": getattr(task, "status", "pending"),
        "progress": getattr(task, "progress", 0),
        "message": getattr(task, "message", "")
    }
    if getattr(task, "error", None):
        response["error"] = task.error
    if getattr(task, "result", None):
        response["result"] = task.result

    logger.info(f"Task {task_id} status: {response['status']}, progress: {response['progress']}")
    return jsonify(response)

# ---------------------------
# Endpoint: Serve Video Files
# ---------------------------
@api_bp.route("/videos/<path:filename>", methods=["GET"])
def serve_video(filename):
    """Serve generated video files."""
    videos_dir = get_project_dirs().get("videos", "generated/videos")
    return send_from_directory(videos_dir, filename)

# ---------------------------
# Endpoint: List All Tasks
# ---------------------------
@api_bp.route("/tasks", methods=["GET"])
def get_all_tasks():
    """List all active tasks."""
    tasks = {tid: task.to_dict() for tid, task in task_manager.get_all_tasks().items()}
    return jsonify({"tasks": list(tasks.values())})

# ---------------------------
# Endpoint: Clear a Completed Task
# ---------------------------
@api_bp.route("/clear/<task_id>", methods=["DELETE"])
def clear_task(task_id):
    """Clear a completed task."""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if task.status not in ["completed", "failed", "error"]:
        return jsonify({"error": "Cannot clear a task that is still in progress"}), 400
    task_manager.remove_task(task_id)
    return jsonify({"success": True})

# ---------------------------
# Endpoint: Generate Script
# ---------------------------
@api_bp.route("/generate-script", methods=["POST"])
def generate_script_endpoint():
    """
    Start generating a math tutorial script.
    Expected JSON:
      { "topic": "...", "level": "...", "style": "...", "duration": ... }
    """
    try:
        data = request.get_json()
        logger.info(f"Received script generation request: {data}")
        for field in ["topic", "level", "style", "duration"]:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        params = {
            "topic": data["topic"],
            "level": data["level"],
            "style": data["style"],
            "duration": data["duration"]
        }
        task_id = task_manager.create_task("script", params)
        task_manager.run_task_in_thread(task_id, target=generate_script_task, kwargs=params)
        return jsonify({"task_id": task_id, "message": "Script generation started"})
    except Exception as e:
        logger.exception("Error in generate_script_endpoint")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


def generate_script_task(task_id, **params):
    """Background task to generate a script."""
    try:
        topic = params["topic"]
        level = params["level"]
        style = params.get("style", "enthusiastic")
        duration = params["duration"]
        logger.info(f"Generating script for task {task_id}: {topic}, {level}, {style}, {duration}min")
        task_manager.update_task(task_id, progress=10, message=f"Generating script for {topic}...")
        script = script_generator.generate_script(topic, level, style, duration)
        task_manager.update_task(task_id, progress=100, message="Script generation completed",
                                 status="completed", result={"script": script})
        return {"script": script}
    except Exception as e:
        logger.exception(f"Error in generate_script_task {task_id}")
        task_manager.update_task(task_id, progress=100, message=f"Error: {str(e)}",
                                 status="error", error=str(e))
        return None

# ---------------------------
# Endpoint: Generate Scene (Manim)
# ---------------------------
@api_bp.route("/generate-scene", methods=["POST"])
def generate_scene_endpoint():
    """
    Start generating a single Manim scene from a scene description.
    Expected JSON:
      { "scene_text": "Detailed description...", "api_key": "optional" }
    """
    try:
        data = request.get_json()
        if not data or "scene_text" not in data:
            return jsonify({"error": "Missing required field: scene_text"}), 400
        scene_text = data["scene_text"]
        api_key = data.get("api_key")
        task_id = generate_scene_task(scene_text, api_key)
        return jsonify({"task_id": task_id})
    except Exception as e:
        logger.exception("Error in generate_scene_endpoint")
        return jsonify({"error": str(e)}), 500


def generate_scene_task(scene_text, api_key=None):
    """
    Create and run a Manim scene generation task.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"[TASK:{task_id}] Creating scene generation task")
    task_manager.create_task(task_id, "scene", {
        "scene_text": scene_text[:100] + "..." if len(scene_text) > 100 else scene_text
    })
    task_manager.update_task(task_id, status="processing", progress=0,
                             message="Initializing scene generation...")

    def task_thread():
        try:
            logger.info(f"[TASK:{task_id}] Starting scene generation thread")
            if api_key:
                logger.info(f"[TASK:{task_id}] Using custom API key")
                os.environ["OPENAI_API_KEY"] = api_key

            scene_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
            output_dirs = get_project_dirs()
            scene_files_dir = Path(output_dirs["scenes"])
            videos_dir = Path(output_dirs["videos"])
            scene_file_path = scene_files_dir / f"scene_{scene_id}.py"
            output_file = videos_dir / f"scene_{scene_id}.mp4"

            logger.info(f"[TASK:{task_id}] Scene ID: {scene_id}")
            logger.info(f"[TASK:{task_id}] Saving Manim code to: {scene_file_path}")
            logger.info(f"[TASK:{task_id}] Output video will be: {output_file}")

            task_manager.update_task(task_id, progress=10, message="Generating Manim code...")
            manim_code = generate_manim_code(scene_text)
            if not manim_code:
                raise Exception("Failed to generate Manim code")
            logger.info(f"[TASK:{task_id}] Generated Manim code ({len(manim_code)} characters)")
            task_manager.update_task(task_id, progress=40, message="Manim code generated")

            with open(scene_file_path, "w") as f:
                f.write(manim_code)
            logger.info(f"[TASK:{task_id}] Saved Manim code")
            task_manager.update_task(task_id, progress=50, message="Manim code saved")

            rendered_file = render_scene(scene_file_path, output_file)
            logger.info(f"[TASK:{task_id}] Rendered scene to {rendered_file}")
            task_manager.update_task(task_id, progress=100, message="Scene rendered",
                                     result=str(rendered_file))
        except Exception as e:
            logger.exception(f"[TASK:{task_id}] Error in scene generation")
            task_manager.update_task(task_id, status="error", progress=100,
                                     message=f"Error: {str(e)}", error=str(e))

    thread = threading.Thread(target=task_thread, daemon=True)
    thread.start()
    return task_id

# ---------------------------
# Endpoint: Create Tutorial (Alternate)
# ---------------------------
@api_bp.route("/create-tutorial", methods=["POST"])
def create_tutorial_endpoint():
    """
    Create a complete math tutorial.
    Expected JSON:
      { "topic": "...", "level": "...", "duration": ..., "use_gm_api": false, "gm_model": "model-name" }
    """
    try:
        data = request.get_json()
        for field in ["topic", "level", "duration"]:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        params = {
            "topic": data["topic"],
            "level": data["level"],
            "duration": data["duration"],
            "use_gm_api": data.get("use_gm_api", False),
            "gm_model": data.get("gm_model", "gemini-1.5-flash"),
            "force_regenerate": data.get("force_regenerate", False)
        }
        
        # Generate a unique task ID
        task_id = f"tutorial_{int(time.time())}_{params['topic'].replace(' ', '_')}"
        
        # Create the task and get the Task object
        task = task_manager.create_task(task_id, "tutorial", params)
        
        # Start the task in a background thread
        task_manager.run_task_in_thread(task_id, target=create_tutorial_task, kwargs=params)
        
        # Return the task ID, not the Task object
        return jsonify({"task_id": task_id, "message": "Tutorial generation started"})
    except Exception as e:
        logger.exception("Error in create_tutorial_endpoint")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


def create_tutorial_task(task_id, **params):
    """Background task to create a complete math tutorial."""
    try:
        topic = params["topic"]
        level = params["level"]
        duration = params["duration"]
        use_gm_api = params.get("use_gm_api", False)
        gm_model = params.get("gm_model", "gemini-1.5-flash")
        force_regenerate = params.get("force_regenerate", False)
        logger.info(f"Creating tutorial for task {task_id}: {topic}, {level}, {duration}min, force_regenerate={force_regenerate}")

        task_manager.update_task(task_id, progress=10, message=f"Starting tutorial generation for {topic}...")

        def progress_callback(progress, message):
            task_manager.update_task(task_id, progress=progress, message=message)

        video_generator.create_math_tutorial(
            topic=topic,
            level=level,
            duration=duration,
            use_gm_api=use_gm_api,
            gm_model=gm_model,
            progress_callback=progress_callback,
            force_regenerate=force_regenerate
        )

        dirs = get_project_dirs()
        output_video = os.path.join(dirs["videos"], "final_video.mp4")
        if os.path.exists(output_video):
            task_manager.update_task(task_id, progress=100, message="Tutorial generated successfully",
                                     status="completed", result={
                                         "video_path": output_video,
                                         "video_url": "/output/videos/final_video.mp4"
                                     })
            logger.info(f"Task {task_id} completed successfully")
            return {"video_path": output_video, "video_url": "/output/videos/final_video.mp4"}
        else:
            task_manager.update_task(task_id, progress=100, message="Failed to create tutorial video",
                                     status="error", error="Output video not found")
            logger.error(f"Task {task_id} failed: output video not found")
            return None
    except Exception as e:
        logger.exception(f"Error in create_tutorial_task {task_id}")
        task_manager.update_task(task_id, progress=100, message=f"Error: {str(e)}",
                                 status="error", error=str(e))
        return None

# ---------------------------
# Register Blueprint and Run App
# ---------------------------
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
