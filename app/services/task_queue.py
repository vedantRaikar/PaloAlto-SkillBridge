import asyncio
import time
from typing import Optional, Dict, Callable, Any
from enum import Enum
from datetime import datetime
import uuid

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task:
    def __init__(
        self,
        task_id: str,
        name: str,
        status: TaskStatus = TaskStatus.PENDING,
        result: Any = None,
        error: Optional[str] = None,
        created_at: Optional[float] = None,
        completed_at: Optional[float] = None
    ):
        self.task_id = task_id
        self.name = name
        self.status = status
        self.result = result
        self.error = error
        self.created_at = created_at or time.time()
        self.completed_at = completed_at

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_seconds": (
                self.completed_at - self.created_at
                if self.completed_at
                else time.time() - self.created_at
            )
        }


class TaskQueue:
    _tasks: Dict[str, Task] = {}
    _max_tasks = 100

    @classmethod
    def create_task(cls, name: str) -> str:
        task_id = f"{name}_{uuid.uuid4().hex[:8]}"
        cls._tasks[task_id] = Task(task_id=task_id, name=name)
        cls._cleanup_old_tasks()
        return task_id

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Task]:
        return cls._tasks.get(task_id)

    @classmethod
    def update_task(
        cls,
        task_id: str,
        status: TaskStatus,
        result: Any = None,
        error: Optional[str] = None
    ):
        if task_id in cls._tasks:
            task = cls._tasks[task_id]
            task.status = status
            task.result = result
            task.error = error
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = time.time()

    @classmethod
    def list_tasks(cls, limit: int = 50) -> list:
        tasks = sorted(
            cls._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return [t.to_dict() for t in tasks[:limit]]

    @classmethod
    def _cleanup_old_tasks(cls):
        if len(cls._tasks) > cls._max_tasks:
            completed_tasks = [
                (tid, t) for tid, t in cls._tasks.items()
                if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]
            completed_tasks.sort(key=lambda x: x[1].created_at)
            
            to_remove = len(cls._tasks) - cls._max_tasks
            for tid, _ in completed_tasks[:to_remove]:
                del cls._tasks[tid]


class BackgroundTaskRunner:
    def __init__(self):
        self.queue = TaskQueue()

    async def run_task(
        self,
        task_id: str,
        coro: Callable
    ) -> Any:
        self.queue.update_task(task_id, TaskStatus.RUNNING)
        
        try:
            result = await coro
            self.queue.update_task(task_id, TaskStatus.COMPLETED, result=result)
            return result
        except Exception as e:
            self.queue.update_task(task_id, TaskStatus.FAILED, error=str(e))
            raise

    def run_task_sync(
        self,
        task_id: str,
        func: Callable
    ) -> Any:
        self.queue.update_task(task_id, TaskStatus.RUNNING)
        
        try:
            result = func()
            self.queue.update_task(task_id, TaskStatus.COMPLETED, result=result)
            return result
        except Exception as e:
            self.queue.update_task(task_id, TaskStatus.FAILED, error=str(e))
            raise


task_runner = BackgroundTaskRunner()
