#!/usr/bin/env python3
"""
Main application server for the Math Tutorial Generator.
This script runs the Flask API server and serves the frontend.

Usage:
  python run_app.py [--debug] [--verbose] [--port PORT] [--no-reload]

Options:
  --debug      Run in debug mode with enhanced error messages
  --verbose    Enable verbose logging
  --port       Specify port number (default: 8742)
  --no-reload  Disable auto-reloading when files change (recommended during video generation)
"""

import os
import sys
import logging
import signal
import threading
import time
import argparse
import uuid
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from src.backend.api import api_bp  # Import the blueprint

# Dictionary to store job status information
active_jobs = {}

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run the Math Tutorial Generator server')
parser.add_argument('--debug', action='store_true', help='Run in debug mode with enhanced error messages')
parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
parser.add_argument('--port', type=int, default=8742, help='Port number (default: 8742)')
parser.add_argument('--no-reload', action='store_true', help='Disable auto-reloading when files change (recommended during video generation)')
args = parser.parse_args()

# Configure logging
log_level = logging.DEBUG if args.verbose else logging.INFO
# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log')
    ]
)
logger = logging.getLogger('run_app')

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

# Create a Flask app for serving frontend
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Mount the API blueprint at /api
app.register_blueprint(api_bp, url_prefix='/api')

# Add a health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint to verify the server is running."""
    return jsonify({
        "status": "ok",
        "timestamp": time.time(),
        "uptime": time.time() - start_time
    })

# Add a job status endpoint
@app.route('/job-status')
def job_status():
    """Check the status of a video generation job."""
    job_id = request.args.get('job_id')
    
    if not job_id or job_id not in active_jobs:
        return jsonify({
            "status": "error",
            "message": f"Job not found: {job_id}"
        }), 404
    
    return jsonify(active_jobs[job_id])

# Add a direct test video generation endpoint
@app.route('/test-video')
def test_video_endpoint():
    """Run the test video generator and return the result."""
    from src.backend.test_video_integration import run_test_video_and_return_path
    try:
        # Get query parameters
        topic = request.args.get('topic', 'Simple Triangle')
        duration = int(request.args.get('duration', 1))
        level = int(request.args.get('level', 1))
        dry_run = request.args.get('dry_run', 'false').lower() == 'true'
        
        logger.info(f"Generating video for topic: {topic}, duration: {duration}, level: {level}, dry_run: {dry_run}")
        
        # Create a job ID for tracking
        job_id = str(uuid.uuid4())
        
        # Store initial job status
        active_jobs[job_id] = {
            "job_id": job_id,
            "status": "started",
            "progress": 0,
            "message": "Video generation started",
            "topic": topic,
            "duration": duration,
            "level": level,
            "dry_run": dry_run,
            "start_time": time.time()
        }
        
        # For dry runs, we can return a response immediately
        if dry_run:
            # Run the test in a separate thread to avoid blocking
            threading.Thread(
                target=run_video_generation_job,
                args=(job_id, topic, duration, level, dry_run),
                daemon=True
            ).start()
            
            return jsonify({
                "status": "started",
                "message": "Video generation has been started (dry run mode)",
                "job_id": job_id
            })
        else:
            # For real runs, start the job in a background thread
            threading.Thread(
                target=run_video_generation_job,
                args=(job_id, topic, duration, level, dry_run),
                daemon=True
            ).start()
            
            return jsonify({
                "status": "started",
                "message": f"Video generation has started for '{topic}'. This may take several minutes.",
                "job_id": job_id
            })
            
    except Exception as e:
        logger.exception(f"Error in test video endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

def run_video_generation_job(job_id, topic, duration, level, dry_run):
    """Run the video generation job in a background thread."""
    from src.backend.test_video_integration import run_test_video_and_return_path
    
    try:
        # Define progress callback function - but we'll use it manually since
        # run_test_video_and_return_path doesn't support it
        def progress_callback(progress, message):
            active_jobs[job_id]["progress"] = progress
            active_jobs[job_id]["message"] = message
            logger.info(f"Job {job_id}: {progress}% - {message}")
            
        # Update job status
        active_jobs[job_id]["status"] = "running"
        active_jobs[job_id]["progress"] = 10
        active_jobs[job_id]["message"] = "Starting video generation..."
        
        # Update progress manually at various stages
        progress_callback(20, "Generating script...")
        
        # Run the video generation without the progress_callback parameter
        video_path, message = run_test_video_and_return_path(
            topic=topic,
            duration_minutes=duration,
            sophistication_level=level,
            dry_run=dry_run
        )
        
        # Update final progress
        if video_path and os.path.exists(video_path):
            logger.info(f"Video generated successfully at {video_path}")
            active_jobs[job_id]["status"] = "success"
            active_jobs[job_id]["progress"] = 100
            active_jobs[job_id]["message"] = message
            active_jobs[job_id]["video_path"] = video_path
            active_jobs[job_id]["video_url"] = f"/videos/{os.path.basename(video_path)}"
            active_jobs[job_id]["completion_time"] = time.time()
        else:
            logger.error(f"Video generation failed: {message}")
            active_jobs[job_id]["status"] = "error"
            active_jobs[job_id]["message"] = message or "Video generation failed"
            active_jobs[job_id]["completion_time"] = time.time()
    except Exception as e:
        logger.exception(f"Error in video generation job {job_id}: {e}")
        active_jobs[job_id]["status"] = "error"
        active_jobs[job_id]["message"] = f"An error occurred: {str(e)}"
        active_jobs[job_id]["completion_time"] = time.time()

# Add a route to serve videos from multiple potential locations
@app.route('/videos/<filename>')
def serve_videos(filename):
    """Serve videos from multiple potential locations."""
    # Check possible locations in order
    possible_paths = [
        ".",  # Current directory
        "output",  # Output directory
        "output/videos",  # Output videos directory
        "media/videos"  # Media directory
    ]
    
    for path in possible_paths:
        file_path = os.path.join(path, filename)
        if os.path.exists(file_path):
            logger.info(f"Serving video from {file_path}")
            return send_from_directory(path, filename)
    
    # If file not found in any location
    logger.error(f"Video file not found: {filename}")
    return jsonify({
        "status": "error",
        "message": f"Video file not found: {filename}"
    }), 404

# Error handler
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "The requested resource was not found"
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "status": "error",
        "message": "An internal server error occurred"
    }), 500

# Serve frontend files
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend files."""
    frontend_dir = os.path.join('src', 'frontend')
    return send_from_directory(frontend_dir, path)

# Handle graceful shutdown
def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Shutdown signal received, exiting gracefully...")
    # Perform any cleanup needed here
    sys.exit(0)

# Monitor active tasks
def task_monitor():
    """Monitor active tasks and log their status."""
    from src.backend.task_manager import task_manager, Task
    
    # Track task progress history to avoid duplicate logging
    task_history = {}
    
    while True:
        try:
            tasks = task_manager.get_all_tasks()
            active_tasks = sum(1 for t in tasks.values() if t.status not in ['completed', 'failed', 'error'])
            
            if active_tasks > 0:
                # Only log the number of active tasks once per monitoring cycle
                logger.info(f"Active tasks: {active_tasks}")
                
                for task in tasks.values():
                    task_id = task.task_id
                    
                    # Get previous state if available
                    prev_progress = None
                    prev_message = None
                    if task_id in task_history:
                        prev_progress = task_history[task_id].get('progress')
                        prev_message = task_history[task_id].get('message')
                    
                    # Check if progress or message has changed significantly
                    progress_changed = prev_progress is None or abs(task.progress - prev_progress) >= 5
                    message_changed = prev_message is None or task.message != prev_message
                    
                    # Only log if there are meaningful changes
                    if progress_changed or message_changed:
                        if task.status == 'running':
                            logger.info(f"Task {task_id}: {task.progress:.1f}% - {task.message}")
                        elif task.status in ['completed', 'failed', 'error']:
                            status_emoji = "✅" if task.status == 'completed' else "❌"
                            logger.info(f"Task {task_id}: {status_emoji} {task.status.upper()} - {task.message}")
                        
                        # Update task history
                        task_history[task_id] = {
                            'progress': task.progress,
                            'message': task.message,
                            'status': task.status
                        }
                
                # Clean up history for completed/error tasks
                for task_id in list(task_history.keys()):
                    if task_id not in tasks:
                        # Task no longer exists, remove from history
                        del task_history[task_id]
                    elif tasks[task_id].status in ['completed', 'failed', 'error']:
                        # Keep completed/failed tasks in history for one cycle, then remove
                        if task_history[task_id].get('status') in ['completed', 'failed', 'error']:
                            del task_history[task_id]
        except Exception as e:
            logger.error(f"Error in task monitor: {e}")
        
        # Sleep for 30 seconds instead of 60
        time.sleep(30)

if __name__ == '__main__':
    # Record the start time for uptime calculation
    start_time = time.time()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print server information
    print("=" * 50)
    print("  🧮 Math Tutorial Generator Server 🎥")
    print("=" * 50)
    print(f"Frontend: http://localhost:{args.port}")
    print(f"API: http://localhost:{args.port}/api")
    print(f"Debug mode: {'ON' if args.debug else 'OFF'}")
    print(f"Auto-reload: {'OFF' if args.no_reload else 'ON'}")
    print(f"Verbose logging: {'ON' if args.verbose else 'OFF'}")
    print("=" * 50)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',  # Make the server publicly available
        port=args.port,
        debug=args.debug,
        use_reloader=not args.no_reload  # Disable reloader if --no-reload is specified
    ) 