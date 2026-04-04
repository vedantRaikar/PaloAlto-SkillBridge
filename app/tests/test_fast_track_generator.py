from app.services.fast_track_generator import FastTrackGenerator


class _FakeMapper:
    def get_learning_path(self, skill, refresh_live=False, prefer_live=False):
        return [
            {"title": "Course A", "duration_hours": None, "is_free": True},
            {"title": "Course B", "duration_hours": None, "is_free": False},
            {"title": "Course C", "duration_hours": 8, "is_free": True},
        ]


def test_get_course_duration_handles_none_duration_values():
    generator = FastTrackGenerator()
    generator._skill_mapper = _FakeMapper()

    duration = generator._get_course_duration("python")

    assert duration == 8


def test_get_fastest_courses_sorts_with_missing_duration_values():
    generator = FastTrackGenerator()
    generator._skill_mapper = _FakeMapper()

    courses = generator._get_fastest_courses("python", max_results=2)

    assert len(courses) == 2
    assert courses[0]["title"] == "Course C"
