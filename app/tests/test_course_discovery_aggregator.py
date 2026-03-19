import pytest

from app.services.course_discovery.aggregator import CourseAggregator, FALLBACK_COURSES


class FakeMapper:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = 0

    def get_learning_path(self, skill):
        self.calls += 1
        return self.mapping.get(skill, [])


def test_get_courses_uses_mapper_and_cache():
    aggregator = CourseAggregator()
    mapper = FakeMapper(
        {
            "python": [
                {
                    "title": "Python Zero To Hero",
                    "provider": "demo",
                    "url": "https://example.com/python",
                    "instructor": "Instructor",
                    "duration_hours": 5,
                    "level": "beginner",
                    "is_free": True,
                    "rating": 4.8,
                    "num_students": 1000,
                    "description": "Python basics",
                }
            ]
        }
    )
    aggregator._skill_mapper = mapper

    first = aggregator._get_courses("python")
    second = aggregator._get_courses("python")

    assert first == second
    assert mapper.calls == 1
    assert first[0]["title"] == "Python Zero To Hero"


def test_get_courses_falls_back_when_no_mapping():
    aggregator = CourseAggregator()
    aggregator._skill_mapper = FakeMapper({})

    courses = aggregator._get_courses("unknown_skill")

    assert len(courses) == len(FALLBACK_COURSES)
    assert courses[0]["provider"] in {"freecodecamp", "coursera"}


def test_search_applies_provider_level_and_limit_filters():
    aggregator = CourseAggregator()
    aggregator._cache["python"] = [
        {
            "title": "Python Free",
            "provider": "freecodecamp",
            "url": "https://example.com/free",
            "instructor": "A",
            "duration_hours": 5,
            "level": "beginner",
            "is_free": True,
            "rating": 4.9,
            "num_students": 100,
            "description": "free",
        },
        {
            "title": "Python Paid",
            "provider": "coursera",
            "url": "https://example.com/paid",
            "instructor": "B",
            "duration_hours": 10,
            "level": "intermediate",
            "is_free": False,
            "rating": 4.5,
            "num_students": 200,
            "description": "paid",
        },
    ]

    response = aggregator.search(
        skill="python",
        providers=["freecodecamp"],
        max_results=1,
        level="beginner",
    )

    assert response.total == 1
    assert response.courses[0].provider == "freecodecamp"
    assert response.provider_breakdown == {"freecodecamp": 1}


@pytest.mark.anyio
async def test_search_all_delegates_to_search():
    aggregator = CourseAggregator()
    aggregator._cache["python"] = [
        {
            "title": "Python Free",
            "provider": "freecodecamp",
            "url": "https://example.com/free",
            "instructor": "A",
            "duration_hours": 5,
            "level": "beginner",
            "is_free": True,
            "rating": 4.9,
            "num_students": 100,
            "description": "free",
        }
    ]

    response = await aggregator.search_all(skill="python", max_results=5)

    assert response.search_skill == "python"
    assert response.total == 1
