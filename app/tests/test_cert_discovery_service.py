from app.services.cert_discovery.service import CertificationDiscoveryService


def test_search_finds_cloud_certifications():
    service = CertificationDiscoveryService(api_key="")

    response = service.search(skill="aws")

    assert response.total > 0
    assert any(cert.provider == "aws" for cert in response.certifications)


def test_get_by_skill_supports_alias_matching():
    service = CertificationDiscoveryService(api_key="")

    certs = service.get_by_skill("machine learning")

    assert len(certs) > 0
    assert any("machine" in cert.name.lower() for cert in certs)


def test_recommend_for_skills_deduplicates_and_limits():
    service = CertificationDiscoveryService(api_key="")

    recommendations = service.recommend_for_skills(["aws", "cloud", "aws"])

    ids = [c.id for c in recommendations]
    assert len(ids) == len(set(ids))
    assert len(recommendations) <= 10


def test_get_by_provider_and_refresh():
    service = CertificationDiscoveryService(api_key="")

    azure = service.get_by_provider("azure")
    unknown = service.get_by_provider("nonexistent")
    total = service.refresh()

    assert len(azure) > 0
    assert unknown == []
    assert total > 0
