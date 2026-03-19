"""Tests for app/services/pending_queue.py."""
import json
import pytest
from pathlib import Path
from app.services.pending_queue import PendingQueue, PendingItem


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    """Return a PendingQueue backed by a temporary file."""
    from app.core import config as cfg_module
    queue_file = tmp_path / "pending.json"
    monkeypatch.setattr(cfg_module.settings, "PENDING_REVIEW_PATH", queue_file)
    monkeypatch.setattr(cfg_module.settings, "DATA_DIR", tmp_path)
    q = PendingQueue()
    return q


# ---------------------------------------------------------------------------
# Initialization / file creation
# ---------------------------------------------------------------------------

def test_queue_creates_file_on_init(tmp_path, monkeypatch):
    from app.core import config as cfg_module
    queue_file = tmp_path / "pending2.json"
    monkeypatch.setattr(cfg_module.settings, "PENDING_REVIEW_PATH", queue_file)
    monkeypatch.setattr(cfg_module.settings, "DATA_DIR", tmp_path)
    assert not queue_file.exists()
    PendingQueue()
    assert queue_file.exists()
    data = json.loads(queue_file.read_text())
    assert data == {"items": [], "metadata": {"total": 0}}


# ---------------------------------------------------------------------------
# add / get_all / get_pending
# ---------------------------------------------------------------------------

def test_add_returns_id(queue):
    item_id = queue.add("Python Dev", "Build APIs", item_type="job")
    assert item_id.startswith("job_")


def test_get_all_after_add(queue):
    queue.add("Title A", "Desc A", item_type="job")
    queue.add("Title B", "Desc B", item_type="course")
    items = queue.get_all()
    assert len(items) == 2
    assert all(isinstance(i, PendingItem) for i in items)


def test_get_pending_filters_status(queue):
    queue.add("T1", "D1")
    queue.add("T2", "D2")
    pending = queue.get_pending()
    assert len(pending) == 2
    for item in pending:
        assert item.status == "pending"


def test_add_with_error(queue):
    queue.add("T3", "D3", error="API timeout")
    items = queue.get_all()
    assert items[0].error == "API timeout"


# ---------------------------------------------------------------------------
# mark_reviewed
# ---------------------------------------------------------------------------

def test_mark_reviewed_changes_status(queue):
    item_id = queue.add("T", "D")
    queue.mark_reviewed(item_id)
    items = queue.get_all()
    assert items[0].status == "reviewed"


def test_get_pending_excludes_reviewed(queue):
    id1 = queue.add("T1", "D1")
    queue.add("T2", "D2")
    queue.mark_reviewed(id1)
    pending = queue.get_pending()
    assert len(pending) == 1


# ---------------------------------------------------------------------------
# retry
# ---------------------------------------------------------------------------

def test_retry_increments_count_and_resets_status(queue):
    item_id = queue.add("T", "D")
    queue.mark_reviewed(item_id)
    queue.retry(item_id)
    item = queue.get_all()[0]
    assert item.status == "pending"
    assert item.retry_count == 1
    assert item.error is None


def test_retry_nonexistent_is_noop(queue):
    # Should not raise
    queue.retry("nonexistent_999")


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

def test_remove_deletes_item(queue):
    item_id = queue.add("T", "D")
    queue.add("T2", "D2")
    queue.remove(item_id)
    items = queue.get_all()
    assert len(items) == 1
    assert all(i.id != item_id for i in items)


def test_remove_updates_total(queue):
    item_id = queue.add("T", "D")
    queue.remove(item_id)
    with open(queue.queue_path) as f:
        data = json.load(f)
    assert data["metadata"]["total"] == 0


# ---------------------------------------------------------------------------
# clear_reviewed
# ---------------------------------------------------------------------------

def test_clear_reviewed_removes_reviewed_items(queue):
    id1 = queue.add("T1", "D1")
    queue.add("T2", "D2")
    queue.mark_reviewed(id1)
    queue.clear_reviewed()
    items = queue.get_all()
    assert len(items) == 1
    assert items[0].status == "pending"


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

def test_get_stats_empty(queue):
    stats = queue.get_stats()
    assert stats["total"] == 0
    assert stats["pending"] == 0
    assert stats["reviewed"] == 0


def test_get_stats_mixed(queue):
    id1 = queue.add("T1", "D1")
    queue.add("T2", "D2")
    queue.mark_reviewed(id1)
    stats = queue.get_stats()
    assert stats["total"] == 2
    assert stats["pending"] == 1
    assert stats["reviewed"] == 1
