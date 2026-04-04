import time

from app.services.knowledge_sources.onet_integration import ONetKnowledgeBase, SKILL_TO_COURSES


def test_get_courses_for_skill_prefers_static_before_live_discovery(monkeypatch):
    knowledge_base = ONetKnowledgeBase(use_cache=False)
    knowledge_base._live_course_cache = {}

    called = {"live": False}

    def fake_discover(skill, max_results=5):
        called["live"] = True
        return [{"title": "Live Python", "provider": "edx", "url": "https://example.com/live"}]

    monkeypatch.setattr(knowledge_base, "discover_courses_live", fake_discover)

    courses = knowledge_base.get_courses_for_skill("python")

    assert courses == SKILL_TO_COURSES["python"]
    assert called["live"] is False


def test_get_courses_for_skill_prefers_live_when_requested(monkeypatch):
    knowledge_base = ONetKnowledgeBase(use_cache=False)
    knowledge_base._live_course_cache = {}

    called = {"live": False}

    def fake_discover(skill, max_results=5):
        called["live"] = True
        return [{"title": "Live Python", "provider": "edx", "url": "https://example.com/live"}]

    monkeypatch.setattr(knowledge_base, "discover_courses_live", fake_discover)

    courses = knowledge_base.get_courses_for_skill("python", prefer_live=True)

    assert called["live"] is True
    assert courses[0]["provider"] == "edx"


def test_get_courses_for_skill_uses_cached_results_before_static(monkeypatch):
    knowledge_base = ONetKnowledgeBase(use_cache=False)
    knowledge_base._live_course_cache = {
        "python": {
            "courses": [{"title": "Cached Python", "provider": "cache", "url": "https://example.com/cache"}],
            "timestamp": time.time(),
        }
    }

    monkeypatch.setattr(knowledge_base, "discover_courses_live", lambda skill, max_results=5: [])

    courses = knowledge_base.get_courses_for_skill("python")

    assert courses[0]["title"] == "Cached Python"


def test_build_open_catalog_results_returns_requested_count():
    knowledge_base = ONetKnowledgeBase(use_cache=False)
    courses = knowledge_base._build_open_catalog_results("python", max_results=5)

    assert len(courses) == 5
    assert courses[0]["provider"] == "coursera"
    assert courses[1]["provider"] == "edx"
    assert courses[0]["source"] == "coursera_catalog"
