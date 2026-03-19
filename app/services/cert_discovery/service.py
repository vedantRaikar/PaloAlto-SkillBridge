from typing import List, Optional, Dict, Any
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from app.models.certification import (
    Certification, CertificationSearchRequest, CertificationSearchResponse,
    CertificationProvider, RenewalDetails, ExamDetails, CertLevel
)
from app.core.config import settings

CERT_SKILL_ALIASES = {
    "aws": ["amazon web services", "amazon_webservices", "aws cloud"],
    "azure": ["microsoft azure", "azure cloud", "az-900"],
    "gcp": ["google cloud platform", "google cloud", "gcp cloud"],
    "security": ["cybersecurity", "infosec", "information security"],
    "networking": ["computer networking", "network administration"],
    "kubernetes": ["k8s", "kube", "container orchestration"],
    "machine learning": ["ml", "machine_learning", "ml ai"],
    "cloud": ["cloud computing", "cloud platform"],
    "docker": ["containerization", "containers"],
    "terraform": ["iac", "infrastructure as code"],
    "python": ["python3", "python programming"],
    "javascript": ["js", "ecmascript", "es6"],
    "typescript": ["ts", "typescript javascript"],
    "database": ["db", "databases", "sql", "nosql"],
}

PROVIDER_CERTS = {
    "aws": [
        {"id": "aws_saa", "name": "AWS Certified Solutions Architect - Associate", "short_name": "SAA-C03", "level": "associate", "cost_usd": 150, "validity_years": 3, "skills_covered": ["aws", "cloud", "architecture", "ec2", "s3", "vpc"], "exam_url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/"},
        {"id": "aws_dva", "name": "AWS Certified Developer - Associate", "short_name": "DVA-C02", "level": "associate", "cost_usd": 150, "validity_years": 3, "skills_covered": ["aws", "lambda", "api_gateway", "dynamodb"], "exam_url": "https://aws.amazon.com/certification/certified-developer-associate/"},
        {"id": "aws_sysops", "name": "AWS Certified SysOps Administrator - Associate", "short_name": "SOA-C02", "level": "associate", "cost_usd": 150, "validity_years": 3, "skills_covered": ["aws", "cloudwatch", "ec2", "deployment"], "exam_url": "https://aws.amazon.com/certification/certified-sysops-admin-associate/"},
        {"id": "aws_security", "name": "AWS Certified Security - Specialty", "short_name": "SCS-C02", "level": "professional", "cost_usd": 300, "validity_years": 3, "skills_covered": ["aws", "security", "iam", "kms", "encryption"], "exam_url": "https://aws.amazon.com/certification/certified-security-specialty/"},
        {"id": "aws_ml", "name": "AWS Certified Machine Learning - Specialty", "short_name": "MLS-C01", "level": "professional", "cost_usd": 300, "validity_years": 3, "skills_covered": ["aws", "machine_learning", "sagemaker"], "exam_url": "https://aws.amazon.com/certification/certified-machine-learning-specialty/"},
    ],
    "azure": [
        {"id": "azure_az900", "name": "Microsoft Azure Fundamentals", "short_name": "AZ-900", "level": "fundamentals", "cost_usd": 99, "validity_years": None, "skills_covered": ["azure", "cloud", "security", "pricing"], "exam_url": "https://learn.microsoft.com/certifications/azure-fundamentals/"},
        {"id": "azure_az104", "name": "Microsoft Azure Administrator Associate", "short_name": "AZ-104", "level": "associate", "cost_usd": 165, "validity_years": 1, "skills_covered": ["azure", "vm", "storage", "networking"], "exam_url": "https://learn.microsoft.com/certifications/azure-administrator/"},
        {"id": "azure_az204", "name": "Microsoft Azure Developer Associate", "short_name": "AZ-204", "level": "associate", "cost_usd": 165, "validity_years": 1, "skills_covered": ["azure", "app_service", "functions", "cosmos_db"], "exam_url": "https://learn.microsoft.com/certifications/azure-developer/"},
        {"id": "azure_az305", "name": "Microsoft Azure Solutions Architect Expert", "short_name": "AZ-305", "level": "expert", "cost_usd": 165, "validity_years": 1, "skills_covered": ["azure", "architecture", "identity", "security"], "exam_url": "https://learn.microsoft.com/certifications/azure-solutions-architect/"},
    ],
    "gcp": [
        {"id": "gcp_ace", "name": "Google Cloud Associate Cloud Engineer", "short_name": "ACE", "level": "associate", "cost_usd": 125, "validity_years": 2, "skills_covered": ["gcp", "cloud", "gke", "compute_engine"], "exam_url": "https://cloud.google.com/certification/cloud-engineer"},
        {"id": "gcp_pca", "name": "Google Cloud Professional Cloud Architect", "short_name": "PCA", "level": "professional", "cost_usd": 200, "validity_years": 2, "skills_covered": ["gcp", "cloud", "architecture", "kubernetes"], "exam_url": "https://cloud.google.com/certification/cloud-architect"},
        {"id": "gcp_pmle", "name": "Google Cloud Professional Machine Learning Engineer", "short_name": "PMLE", "level": "professional", "cost_usd": 200, "validity_years": 2, "skills_covered": ["gcp", "machine_learning", "tensorflow", "vertex_ai"], "exam_url": "https://cloud.google.com/certification/machine-learning-engineer"},
    ],
    "comptia": [
        {"id": "comptia_a", "name": "CompTIA A+", "short_name": "A+", "level": "fundamentals", "cost_usd": 246, "validity_years": 3, "skills_covered": ["hardware", "networking", "security", "troubleshooting"], "exam_url": "https://www.comptia.org/certifications/a"},
        {"id": "comptia_network", "name": "CompTIA Network+", "short_name": "Net+", "level": "associate", "cost_usd": 346, "validity_years": 3, "skills_covered": ["networking", "routing", "switching"], "exam_url": "https://www.comptia.org/certifications/network"},
        {"id": "comptia_security", "name": "CompTIA Security+", "short_name": "Sec+", "level": "associate", "cost_usd": 370, "validity_years": 3, "skills_covered": ["security", "threats", "vulnerabilities"], "exam_url": "https://www.comptia.org/certifications/security"},
        {"id": "comptia_cysa", "name": "CompTIA CySA+", "short_name": "CySA+", "level": "professional", "cost_usd": 370, "validity_years": 3, "skills_covered": ["cybersecurity", "threat_detection", "incident_response"], "exam_url": "https://www.comptia.org/certifications/cybersecurity-analyst"},
    ],
    "hashicorp": [
        {"id": "terraform_associate", "name": "HashiCorp Certified: Terraform Associate", "short_name": "Terraform", "level": "associate", "cost_usd": 70.50, "validity_years": 2, "skills_covered": ["terraform", "infrastructure", "cloud", "iac"], "exam_url": "https://www.hashicorp.com/certification/terraform-associate/"},
        {"id": "vault_associate", "name": "HashiCorp Certified: Vault Associate", "short_name": "Vault", "level": "associate", "cost_usd": 70.50, "validity_years": 2, "skills_covered": ["vault", "security", "secrets_management"], "exam_url": "https://www.hashicorp.com/certification/vault-associate/"},
    ],
}


class CertificationDiscoveryService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self._llm = None
        self._providers = self._get_providers()
        self._initialize_llm()
        self._cert_cache: Dict[str, List[Certification]] = {}

    def _initialize_llm(self):
        if self._llm is None and self.api_key:
            try:
                self._llm = ChatGroq(
                    api_key=self.api_key,
                    model="llama-3.1-8b-instant",
                    temperature=0.2,
                    max_tokens=2048
                )
            except Exception:
                self._llm = None

    def _get_providers(self) -> List[CertificationProvider]:
        return [
            CertificationProvider(id="aws", name="Amazon Web Services", url="https://aws.amazon.com/certification"),
            CertificationProvider(id="gcp", name="Google Cloud", url="https://cloud.google.com/certification"),
            CertificationProvider(id="azure", name="Microsoft Azure", url="https://learn.microsoft.com/certifications"),
            CertificationProvider(id="comptia", name="CompTIA", url="https://www.comptia.org/certifications"),
            CertificationProvider(id="hashicorp", name="HashiCorp", url="https://www.hashicorp.com/certification"),
        ]

    def _create_certification(self, data: Dict[str, Any]) -> Certification:
        return Certification(
            id=data.get("id", ""),
            name=data.get("name", "Unknown"),
            short_name=data.get("short_name"),
            provider=data.get("provider", data.get("id", "").split("_")[0] if "_" in data.get("id", "") else "other"),
            certification_url=data.get("exam_url", ""),
            exam_url=data.get("exam_url"),
            level=data.get("level", "associate"),
            cost_usd=data.get("cost_usd"),
            validity_years=data.get("validity_years"),
            skills_covered=data.get("skills_covered", []),
            prerequisites=data.get("prerequisites", []),
            renewal=RenewalDetails(required=data.get("validity_years") is not None),
            exam_details=ExamDetails(),
            description=f"Professional certification for {data.get('name', 'skills')}",
        )

    def _infer_provider(self, skill: str) -> Optional[str]:
        skill_lower = skill.lower()
        providers_map = {
            "aws": ["aws", "amazon", "ec2", "s3", "lambda", "dynamodb"],
            "azure": ["azure", "microsoft", "az-"],
            "gcp": ["gcp", "google cloud", "bigquery", "vertex"],
            "comptia": ["security+", "network+", "a+", "cydsa"],
            "hashicorp": ["terraform", "vault", "consul", "nomad"],
        }
        
        for provider, keywords in providers_map.items():
            if any(kw in skill_lower for kw in keywords):
                return provider
        return None

    def _search_certs_by_provider(self, skill: str, provider: str) -> List[Certification]:
        if provider not in PROVIDER_CERTS:
            return []
        
        certs = []
        for cert_data in PROVIDER_CERTS[provider]:
            skills_covered = cert_data.get("skills_covered", [])
            if any(skill.lower() in s.lower() for s in skills_covered):
                certs.append(self._create_certification(cert_data))
        
        return certs

    def search(self, skill: Optional[str] = None, provider: Optional[str] = None, level: Optional[str] = None, max_results: int = 20) -> CertificationSearchResponse:
        results = []
        
        if skill:
            skill_lower = skill.lower().replace("_", " ")
            inferred_provider = self._infer_provider(skill_lower)
            
            if inferred_provider:
                results.extend(self._search_certs_by_provider(skill_lower, inferred_provider))
            
            if not provider:
                for prov, certs in PROVIDER_CERTS.items():
                    for cert_data in certs:
                        skills = cert_data.get("skills_covered", [])
                        if any(skill_lower in s.lower() or skill_lower in cert_data.get("name", "").lower() for s in skills):
                            results.append(self._create_certification(cert_data))
        
        if provider:
            results = [c for c in results if c.provider == provider.lower()]
        
        if level:
            results = [c for c in results if c.level == level.lower()]
        
        seen = set()
        unique_results = []
        for c in results:
            if c.id not in seen:
                seen.add(c.id)
                unique_results.append(c)
        
        results = unique_results[:max_results]
        providers_found = list(set(c.provider for c in results))
        
        return CertificationSearchResponse(
            certifications=results,
            total=len(results),
            providers_found=providers_found,
            search_params={"skill": skill, "provider": provider, "level": level, "max_results": max_results},
        )

    async def search_llm(self, skill: str, provider: Optional[str] = None, level: Optional[str] = None, max_results: int = 20) -> CertificationSearchResponse:
        return self.search(skill, provider, level, max_results)

    def get_by_id(self, cert_id: str) -> Optional[Certification]:
        for certs in PROVIDER_CERTS.values():
            for cert_data in certs:
                if cert_data.get("id") == cert_id:
                    return self._create_certification(cert_data)
        return None

    def _skills_match(self, skill1: str, skill2: str) -> bool:
        """Check if skills match (exact or alias)"""
        s1 = skill1.lower().strip()
        s2 = skill2.lower().strip()
        
        if s1 == s2:
            return True
        
        for skill, aliases in CERT_SKILL_ALIASES.items():
            if s1 == skill.lower() and s2 in [a.lower() for a in aliases]:
                return True
            if s2 == skill.lower() and s1 in [a.lower() for a in aliases]:
                return True
        
        tokens1 = set(s1.replace("_", " ").split())
        tokens2 = set(s2.replace("_", " ").split())
        if tokens1 == tokens2 or tokens1.issubset(tokens2) or tokens2.issubset(tokens1):
            return True
        
        return False

    def get_by_skill(self, skill_id: str) -> List[Certification]:
        if skill_id in self._cert_cache:
            return self._cert_cache[skill_id]
        
        results = []
        
        for certs in PROVIDER_CERTS.values():
            for cert_data in certs:
                skills = cert_data.get("skills_covered", [])
                if any(self._skills_match(skill_id, s) for s in skills):
                    results.append(self._create_certification(cert_data))
                elif self._skills_match(skill_id, cert_data.get("name", "")):
                    results.append(self._create_certification(cert_data))
        
        seen = set()
        unique_results = []
        for c in results:
            if c.id not in seen:
                seen.add(c.id)
                unique_results.append(c)
        
        self._cert_cache[skill_id] = unique_results
        return unique_results

    def get_providers(self) -> List[CertificationProvider]:
        return self._providers

    def get_by_provider(self, provider: str) -> List[Certification]:
        if provider not in PROVIDER_CERTS:
            return []
        return [self._create_certification(c) for c in PROVIDER_CERTS[provider]]

    def get_prerequisites(self, cert_id: str) -> List[Certification]:
        return []

    def get_career_path(self, cert_id: str) -> List[Certification]:
        return []

    async def recommend_for_skills_llm(self, skills: List[str], context: str = "", goal: str = "career advancement", level: str = "intermediate", industry: str = "technology") -> List[Certification]:
        return self.recommend_for_skills(skills)

    def recommend_for_skills(self, skills: List[str]) -> List[Certification]:
        recommendations = []
        for skill in skills:
            certs = self.get_by_skill(skill)
            recommendations.extend(certs)
        
        seen = set()
        unique = []
        for c in recommendations:
            if c.id not in seen:
                seen.add(c.id)
                unique.append(c)
        
        return unique[:10]

    def refresh(self, provider: Optional[str] = None) -> int:
        self._cert_cache.clear()
        return sum(len(certs) for certs in PROVIDER_CERTS.values())


_certification_service: Optional[CertificationDiscoveryService] = None


def get_certification_service() -> CertificationDiscoveryService:
    global _certification_service
    if _certification_service is None:
        _certification_service = CertificationDiscoveryService()
    return _certification_service
