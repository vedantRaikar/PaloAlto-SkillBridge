import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from app.core.config import settings

class PendingItem(BaseModel):
    id: str
    title: str
    description: str
    item_type: str
    created_at: str
    retry_count: int = 0
    status: str = "pending"
    error: Optional[str] = None

class PendingQueue:
    def __init__(self):
        self.queue_path = settings.PENDING_REVIEW_PATH
        self._ensure_file()

    def _ensure_file(self):
        if not self.queue_path.exists():
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.queue_path, 'w') as f:
                json.dump({"items": [], "metadata": {"total": 0}}, f)

    def _load_queue(self) -> dict:
        with open(self.queue_path) as f:
            return json.load(f)

    def _save_queue(self, data: dict):
        with open(self.queue_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add(self, title: str, description: str, item_type: str = "job", error: Optional[str] = None) -> str:
        data = self._load_queue()
        
        item_id = f"{item_type}_{len(data['items']) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        item = PendingItem(
            id=item_id,
            title=title,
            description=description,
            item_type=item_type,
            created_at=datetime.now().isoformat(),
            error=error
        )
        
        data['items'].append(item.model_dump())
        data['metadata']['total'] = len(data['items'])
        
        self._save_queue(data)
        return item_id

    def get_all(self) -> List[PendingItem]:
        data = self._load_queue()
        return [PendingItem(**item) for item in data.get('items', [])]

    def get_pending(self) -> List[PendingItem]:
        return [item for item in self.get_all() if item.status == "pending"]

    def mark_reviewed(self, item_id: str):
        data = self._load_queue()
        for item in data['items']:
            if item['id'] == item_id:
                item['status'] = 'reviewed'
                break
        self._save_queue(data)

    def retry(self, item_id: str):
        data = self._load_queue()
        for item in data['items']:
            if item['id'] == item_id:
                item['retry_count'] += 1
                item['status'] = 'pending'
                item['error'] = None
                break
        self._save_queue(data)

    def remove(self, item_id: str):
        data = self._load_queue()
        data['items'] = [i for i in data['items'] if i['id'] != item_id]
        data['metadata']['total'] = len(data['items'])
        self._save_queue(data)

    def clear_reviewed(self):
        data = self._load_queue()
        data['items'] = [i for i in data['items'] if i['status'] != 'reviewed']
        data['metadata']['total'] = len(data['items'])
        self._save_queue(data)

    def get_stats(self) -> dict:
        data = self._load_queue()
        items = data.get('items', [])
        return {
            "total": len(items),
            "pending": len([i for i in items if i['status'] == 'pending']),
            "reviewed": len([i for i in items if i['status'] == 'reviewed']),
            "failed": len([i for i in items if i['status'] == 'failed'])
        }
