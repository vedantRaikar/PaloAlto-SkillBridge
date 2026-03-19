"""
Course Discovery Module
=====================
Provides course recommendations using O*NET knowledge base.
All mappings are pre-verified - no web scraping required.
"""

from app.services.course_discovery.aggregator import CourseAggregator, get_course_aggregator

__all__ = [
    "CourseAggregator",
    "get_course_aggregator",
]
