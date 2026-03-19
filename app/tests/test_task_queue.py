"""Tests for app/services/task_queue.py."""
import time
import pytest
import asyncio
from app.services.task_queue import Task, TaskQueue, TaskStatus, BackgroundTaskRunner, task_runner


# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

def test_task_to_dict_pending():
    task = Task(task_id="t1", name="test_job")
    d = task.to_dict()
    assert d["task_id"] == "t1"
    assert d["name"] == "test_job"
    assert d["status"] == "pending"
    assert d["result"] is None
    assert d["error"] is None
    assert "created_at" in d
    assert "duration_seconds" in d
    assert d["completed_at"] is None


def test_task_to_dict_completed():
    t = time.time()
    task = Task(
        task_id="t2",
        name="done",
        status=TaskStatus.COMPLETED,
        result={"ok": True},
        created_at=t - 5,
        completed_at=t,
    )
    d = task.to_dict()
    assert d["status"] == "completed"
    assert d["result"] == {"ok": True}
    assert abs(d["duration_seconds"] - 5) < 1


def test_task_to_dict_failed():
    task = Task(task_id="t3", name="failed", status=TaskStatus.FAILED, error="oops")
    d = task.to_dict()
    assert d["status"] == "failed"
    assert d["error"] == "oops"


# ---------------------------------------------------------------------------
# TaskQueue class methods
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_queue():
    """Isolate each test by clearing the in-memory task store."""
    TaskQueue._tasks.clear()
    yield
    TaskQueue._tasks.clear()


def test_create_task_returns_id():
    tid = TaskQueue.create_task("extract")
    assert "extract" in tid
    assert TaskQueue.get_task(tid) is not None


def test_get_task_none_for_missing():
    assert TaskQueue.get_task("nonexistent_xyz") is None


def test_update_task_to_running():
    tid = TaskQueue.create_task("job")
    TaskQueue.update_task(tid, TaskStatus.RUNNING)
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.RUNNING
    assert task.completed_at is None


def test_update_task_to_completed():
    tid = TaskQueue.create_task("job")
    TaskQueue.update_task(tid, TaskStatus.COMPLETED, result={"items": 3})
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == {"items": 3}
    assert task.completed_at is not None


def test_update_task_to_failed():
    tid = TaskQueue.create_task("job")
    TaskQueue.update_task(tid, TaskStatus.FAILED, error="broken")
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.FAILED
    assert task.error == "broken"


def test_update_task_missing_id_is_noop():
    # No error should be raised
    TaskQueue.update_task("ghost_id", TaskStatus.RUNNING)


def test_list_tasks_empty():
    result = TaskQueue.list_tasks()
    assert result == []


def test_list_tasks_most_recent_first():
    t1 = TaskQueue.create_task("a")
    time.sleep(0.01)
    t2 = TaskQueue.create_task("b")
    tasks = TaskQueue.list_tasks()
    assert tasks[0]["task_id"] == t2
    assert tasks[1]["task_id"] == t1


def test_list_tasks_limit():
    for i in range(5):
        TaskQueue.create_task(f"job_{i}")
    tasks = TaskQueue.list_tasks(limit=3)
    assert len(tasks) == 3


def test_cleanup_removes_old_completed_tasks():
    # Fill up beyond _max_tasks to trigger cleanup
    original_max = TaskQueue._max_tasks
    TaskQueue._max_tasks = 5
    try:
        for i in range(4):
            tid = TaskQueue.create_task(f"done_{i}")
            TaskQueue.update_task(tid, TaskStatus.COMPLETED)
        # Creating one more should trigger cleanup (we're at 5 after this)
        TaskQueue.create_task("trigger")
        # Cleanup removes oldest completed tasks; we should still have ≤ max
        assert len(TaskQueue._tasks) <= TaskQueue._max_tasks
    finally:
        TaskQueue._max_tasks = original_max


# ---------------------------------------------------------------------------
# BackgroundTaskRunner – synchronous path
# ---------------------------------------------------------------------------

def test_run_task_sync_success():
    runner = BackgroundTaskRunner()
    tid = TaskQueue.create_task("sync_job")
    result = runner.run_task_sync(tid, lambda: {"done": True})
    assert result == {"done": True}
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.COMPLETED
    assert task.result == {"done": True}


def test_run_task_sync_failure():
    runner = BackgroundTaskRunner()
    tid = TaskQueue.create_task("fail_job")
    with pytest.raises(ValueError, match="boom"):
        runner.run_task_sync(tid, lambda: (_ for _ in ()).throw(ValueError("boom")))
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.FAILED
    assert "boom" in task.error


# ---------------------------------------------------------------------------
# BackgroundTaskRunner – async path
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_run_task_async_success():
    runner = BackgroundTaskRunner()
    tid = TaskQueue.create_task("async_job")

    async def work():
        return 42

    result = await runner.run_task(tid, work())
    assert result == 42
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.anyio
async def test_run_task_async_failure():
    runner = BackgroundTaskRunner()
    tid = TaskQueue.create_task("async_fail")

    async def bad():
        raise RuntimeError("async oops")

    with pytest.raises(RuntimeError):
        await runner.run_task(tid, bad())
    task = TaskQueue.get_task(tid)
    assert task.status == TaskStatus.FAILED


def test_module_level_task_runner_exists():
    assert task_runner is not None
    assert isinstance(task_runner, BackgroundTaskRunner)
