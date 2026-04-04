from app.services.gap_analyzer import GapAnalyzer


def test_get_cached_courses_does_not_fetch_when_graph_is_empty(monkeypatch):
    analyzer = GapAnalyzer()
    analyzer._course_cache = {}

    monkeypatch.setattr(analyzer.graph_manager, "get_courses_for_skill", lambda skill_id: [])

    called = {"web": False}

    def fake_fetch(skill_id):
        called["web"] = True
        return [{"title": "Should Not Fetch"}]

    monkeypatch.setattr(analyzer, "_fetch_courses_web", fake_fetch)

    courses = analyzer._get_cached_courses("python")

    assert courses == []
    assert called["web"] is False