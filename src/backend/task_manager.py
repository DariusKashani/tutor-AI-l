"""
Task management system for tracking progress of long-running operations.
"""

import os
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("task_manager")

class Task:
    """
    Represents a task with status, progress, and metadata.
    """
    def __init__(self, task_id: str, task_type: str, params: Dict[str, Any] = None):
        self.task_id = task_id
        self.task_type = task_type
        self.status = "pending"  # pending, running, completed, failed, error
        self.progress = 0.0  # 0 to 100
        self.message = "Task initialized"
        self.params = params or {}
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at = None
        self.result = None
        self.error = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "params": self.params,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task instance from dictionary."""
        task = cls(data["task_id"], data["task_type"], data.get("params", {}))
        task.status = data.get("status", "pending")
        task.progress = data.get("progress", 0.0)
        task.message = data.get("message", "")
        task.created_at = data.get("created_at", time.time())
        task.updated_at = data.get("updated_at", time.time())
        task.completed_at = data.get("completed_at")
        task.result = data.get("result")
        task.error = data.get("error")
        return task


class TaskManager:
    """
    Manages tasks and their state persistence.
    """
    def __init__(self, persistence_file: str = None):
        # Set up persistence directory
        self.persistence_dir = Path("output/data")
        if not self.persistence_dir.exists():
            logger.info(f"Task persistence directory: {self.persistence_dir} (absolute: {self.persistence_dir.absolute()})")
            self.persistence_dir.mkdir(parents=True, exist_ok=True)
            
        # Set up persistence file
        self.persistence_file = persistence_file or str(self.persistence_dir / "tasks.json")
        logger.info(f"Initializing TaskManager with persistence file: {self.persistence_file}")
        
        self._tasks = {}
        self._lock = threading.RLock()
        self._load_tasks()
        
    def _load_tasks(self):
        """Load tasks from persistence file."""
        try:
            logger.info(f"Loading tasks from {self.persistence_file}")
            if not os.path.exists(self.persistence_file):
                logger.info("Persistence file doesn't exist, starting with empty tasks")
                return
                
            with open(self.persistence_file, 'r') as f:
                tasks_data = json.load(f)
            
            with self._lock:
                self._tasks = {
                    task_id: Task.from_dict(task_data)
                    for task_id, task_data in tasks_data.items()
                }
                
            logger.info(f"Found {len(self._tasks)} tasks in persistence file")
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            self._tasks = {}
    
    def _save_tasks(self):
        """Save tasks to persistence file."""
        try:
            with self._lock:
                tasks_data = {
                    task_id: task.to_dict()
                    for task_id, task in self._tasks.items()
                }
                
            with open(self.persistence_file, 'w') as f:
                json.dump(tasks_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
    
    def create_task(self, task_id: str, task_type: str, params: Dict[str, Any] = None) -> Task:
        """Create a new task."""
        with self._lock:
            task = Task(task_id, task_type, params)
            self._tasks[task_id] = task
            self._save_tasks()
            return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task(self, task_id: str, status: str = None, progress: float = None, 
                   message: str = None, result: Any = None, error: str = None) -> Optional[Task]:
        """Update task properties."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Attempted to update nonexistent task: {task_id}")
                return None
                
            if status:
                task.status = status
                if status in ["completed", "failed", "error"]:
                    task.completed_at = time.time()
                    
            if progress is not None:
                task.progress = progress
                
            if message:
                task.message = message
                
            if result is not None:
                task.result = result
                
            if error is not None:
                task.error = error
                
            task.updated_at = time.time()
            self._save_tasks()
            return task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._save_tasks()
                return True
            return False
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """Get all tasks."""
        with self._lock:
            return dict(self._tasks)
    
    def run_task_in_thread(self, task_id: str, target: Callable, args: tuple = None, kwargs: dict = None):
        """
        Run a task in a separate thread.
        
        Args:
            task_id: ID of the task to run
            target: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Cannot run nonexistent task: {task_id}")
            return
            
        # Update task status to running
        self.update_task(task_id, status="running", message="Task started")
        
        # Prepare arguments
        args = args or ()
        kwargs = kwargs or {}
        
        # Define wrapper function to handle task completion
        def task_wrapper():
            try:
                logger.info(f"Starting task {task_id} in thread")
                result = target(*args, **kwargs)
                if result:
                    self.update_task(task_id, status="completed", message="Task completed", result=result)
                logger.info(f"Task {task_id} completed")
            except Exception as e:
                logger.exception(f"Error in task {task_id}: {str(e)}")
                self.update_task(task_id, status="error", message=f"Error: {str(e)}", error=str(e))
        
        # Start thread
        thread = threading.Thread(target=task_wrapper)
        thread.daemon = True
        thread.start()
        logger.info(f"Started thread for task {task_id}")
        return thread
    
    def clear_tasks(self):
        """Clear all tasks."""
        with self._lock:
            self._tasks = {}
            self._save_tasks()


# Singleton instance
task_manager = TaskManager() 