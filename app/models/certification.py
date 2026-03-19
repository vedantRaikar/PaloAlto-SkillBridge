from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CertLevel(str, Enum):
    FUNDAMENTALS = "fundamentals"
    ASSOCIATE = "associate"
    PROFESSIONAL = "professional"
    EXPERT = "expert"
    MASTER = "master"

class CertProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    COMPTIA = "comptia"
    ISC2 = "isc2"
    ISACA = "isaca"
    HASHICORP = "hashicorp"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    ORACLE = "oracle"
    vmware = "vmware"
    PMI = "pmi"
    SCRUM = "scrum"
    OTHER = "other"

class ExamDetails(BaseModel):
    duration_minutes: Optional[int] = Field(None, description="Exam duration in minutes")
    questions: Optional[int] = Field(None, description="Number of questions")
    format: Optional[str] = Field(None, description="Exam format (multiple choice, hands-on, etc.)")
    passing_score: Optional[str] = Field(None, description="Passing score")
    languages: List[str] = Field(default_factory=lambda: ["en"])
    delivery: Optional[str] = Field(None, description="Online proctored, testing center, etc.")

class RenewalDetails(BaseModel):
    required: bool = Field(False)
    period_years: Optional[int] = Field(None, description="Renewal period in years")
    requirements: Optional[str] = Field(None, description="Renewal requirements")
    cost_usd: Optional[float] = Field(None, description="Renewal cost")

class Certification(BaseModel):
    id: str = Field(..., description="Unique certification identifier")
    name: str = Field(..., description="Full certification name")
    short_name: Optional[str] = Field(None, description="Short/abbreviated name")
    provider: str = Field(..., description="Certification provider")
    certification_url: str = Field(..., description="Official certification page URL")
    exam_url: Optional[str] = Field(None, description="Exam registration URL")
    exam_code: Optional[str] = Field(None, description="Official exam code")
    level: str = Field("associate", description="Certification level")
    cost_usd: Optional[float] = Field(None, description="Exam cost in USD")
    validity_years: Optional[int] = Field(None, description="Validity period in years (None = lifetime)")
    skills_covered: List[str] = Field(default_factory=list, description="List of skill IDs covered")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite certifications or skills")
    renewal: RenewalDetails = Field(default_factory=RenewalDetails)
    exam_details: ExamDetails = Field(default_factory=ExamDetails)
    description: Optional[str] = Field(None, description="Certification description")
    target_roles: List[str] = Field(default_factory=list, description="Target job roles")
    industry: Optional[str] = Field(None, description="Industry focus")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_graph_node(self) -> dict:
        return {
            "id": f"cert_{self.id}",
            "type": "certification",
            "name": self.name,
            "provider": self.provider,
            "url": self.certification_url,
            "level": self.level,
            "cost_usd": self.cost_usd,
            "validity_years": self.validity_years,
            "renewal_required": self.renewal.required,
        }


class CertificationSearchRequest(BaseModel):
    skill: Optional[str] = Field(None, description="Filter by skill")
    provider: Optional[str] = Field(None, description="Filter by provider")
    level: Optional[str] = Field(None, description="Filter by level")
    max_results: int = Field(20, ge=1, le=100)
    include_prerequisites: bool = Field(False, description="Include prerequisite certs")


class CertificationSearchResponse(BaseModel):
    certifications: List[Certification] = Field(default_factory=list)
    total: int = Field(0)
    providers_found: List[str] = Field(default_factory=list)
    search_params: dict = Field(default_factory=dict)


class CertificationProvider(BaseModel):
    id: str
    name: str
    url: str
    logo_url: Optional[str] = None
    certifications_count: int = 0
    popular_certs: List[str] = Field(default_factory=list)


class CertificationRefreshRequest(BaseModel):
    provider: Optional[str] = Field(None, description="Refresh specific provider")
    force: bool = Field(False)


class CertificationStorage(BaseModel):
    certifications: List[Certification] = Field(default_factory=list)
    providers: List[CertificationProvider] = Field(default_factory=list)
    last_refresh: Optional[str] = Field(None)
    total_cached: int = Field(0)


AWS_CERTIFICATIONS = [
    {
        "id": "aws_saa_c03",
        "name": "AWS Certified Solutions Architect - Associate",
        "short_name": "SAA-C03",
        "provider": "aws",
        "level": "associate",
        "cost_usd": 150,
        "validity_years": 3,
        "skills_covered": ["aws", "cloud", "architecture", "ec2", "s3", "vpc", "iam"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 3, "requirements": "Pass current associate exam or earn professional cert"},
        "exam_details": {"duration_minutes": 130, "questions": 65, "format": "Multiple choice", "passing_score": "72%", "delivery": "Testing center or online proctored"},
        "target_roles": ["Solutions Architect", "Cloud Engineer"],
        "industry": "cloud"
    },
    {
        "id": "aws_dva_c02",
        "name": "AWS Certified Developer - Associate",
        "short_name": "DVA-C02",
        "provider": "aws",
        "level": "associate",
        "cost_usd": 150,
        "validity_years": 3,
        "skills_covered": ["aws", "lambda", "api_gateway", "dynamodb", "ci_cd", "docker"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 130, "questions": 65, "format": "Multiple choice"},
        "target_roles": ["Developer", "Software Engineer"],
        "industry": "cloud"
    },
    {
        "id": "aws_sysops",
        "name": "AWS Certified SysOps Administrator - Associate",
        "short_name": "SOA-C02",
        "provider": "aws",
        "level": "associate",
        "cost_usd": 150,
        "validity_years": 3,
        "skills_covered": ["aws", "cloudwatch", "ec2", "vpc", "security", "deployment"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 130, "questions": 65, "format": "Multiple choice"},
        "target_roles": ["SysOps Administrator", "Cloud Administrator"],
        "industry": "cloud"
    },
    {
        "id": "aws_security",
        "name": "AWS Certified Security - Specialty",
        "short_name": "SCS-C02",
        "provider": "aws",
        "level": "professional",
        "cost_usd": 300,
        "validity_years": 3,
        "skills_covered": ["aws", "security", "iam", "kms", "encryption", "compliance"],
        "prerequisites": ["aws_saa_c03"],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 170, "questions": 65, "format": "Multiple choice and multiple response"},
        "target_roles": ["Security Engineer", "Cloud Security Architect"],
        "industry": "cloud"
    },
    {
        "id": "aws_ml",
        "name": "AWS Certified Machine Learning - Specialty",
        "short_name": "MLS-C01",
        "provider": "aws",
        "level": "professional",
        "cost_usd": 300,
        "validity_years": 3,
        "skills_covered": ["aws", "machine_learning", "sagemaker", "deep_learning", "python"],
        "prerequisites": ["aws_saa_c03"],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 180, "questions": 65, "format": "Multiple choice"},
        "target_roles": ["ML Engineer", "Data Scientist"],
        "industry": "ai"
    },
    {
        "id": "aws_data",
        "name": "AWS Certified Data Analytics - Specialty",
        "short_name": "DAS-C01",
        "provider": "aws",
        "level": "professional",
        "cost_usd": 300,
        "validity_years": 3,
        "skills_covered": ["aws", "redshift", "kinesis", "glue", "athena", "data_engineering"],
        "prerequisites": ["aws_saa_c03"],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 180, "questions": 65},
        "target_roles": ["Data Engineer", "Analytics Engineer"],
        "industry": "data"
    }
]

GCP_CERTIFICATIONS = [
    {
        "id": "gcp_ace",
        "name": "Google Cloud Associate Cloud Engineer",
        "short_name": "ACE",
        "provider": "gcp",
        "level": "associate",
        "cost_usd": 125,
        "validity_years": 2,
        "skills_covered": ["gcp", "cloud", "gke", "compute_engine", "storage", "iam"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 2},
        "exam_details": {"duration_minutes": 120, "questions": 50, "format": "Multiple choice"},
        "target_roles": ["Cloud Engineer", "Cloud Administrator"],
        "industry": "cloud"
    },
    {
        "id": "gcp_professional",
        "name": "Google Cloud Professional Cloud Architect",
        "short_name": "PCA",
        "provider": "gcp",
        "level": "professional",
        "cost_usd": 200,
        "validity_years": 2,
        "skills_covered": ["gcp", "cloud", "architecture", "kubernetes", "data", "security"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 2},
        "exam_details": {"duration_minutes": 120, "questions": 50},
        "target_roles": ["Solutions Architect", "Cloud Architect"],
        "industry": "cloud"
    },
    {
        "id": "gcp_ml",
        "name": "Google Cloud Professional Machine Learning Engineer",
        "short_name": "PMLE",
        "provider": "gcp",
        "level": "professional",
        "cost_usd": 200,
        "validity_years": 2,
        "skills_covered": ["gcp", "machine_learning", "tensorflow", "vertex_ai", "bigquery_ml"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 2},
        "exam_details": {"duration_minutes": 120, "questions": 60},
        "target_roles": ["ML Engineer", "Data Scientist"],
        "industry": "ai"
    }
]

AZURE_CERTIFICATIONS = [
    {
        "id": "azure_fundamentals",
        "name": "Microsoft Azure Fundamentals",
        "short_name": "AZ-900",
        "provider": "azure",
        "level": "fundamentals",
        "cost_usd": 99,
        "validity_years": None,
        "skills_covered": ["azure", "cloud", "security", "compliance", "pricing"],
        "prerequisites": [],
        "renewal": {"required": False},
        "exam_details": {"duration_minutes": 45, "questions": 40, "format": "Multiple choice"},
        "target_roles": ["Cloud Beginners", "IT Support"],
        "industry": "cloud"
    },
    {
        "id": "azure_admin",
        "name": "Microsoft Azure Administrator Associate",
        "short_name": "AZ-104",
        "provider": "azure",
        "level": "associate",
        "cost_usd": 165,
        "validity_years": 1,
        "skills_covered": ["azure", "vm", "storage", "networking", "security", "monitoring"],
        "prerequisites": ["azure_fundamentals"],
        "renewal": {"required": True, "period_years": 1, "requirements": "Pass exam"},
        "exam_details": {"duration_minutes": 120, "questions": 60},
        "target_roles": ["Azure Administrator", "Cloud Administrator"],
        "industry": "cloud"
    },
    {
        "id": "azure_developer",
        "name": "Microsoft Azure Developer Associate",
        "short_name": "AZ-204",
        "provider": "azure",
        "level": "associate",
        "cost_usd": 165,
        "validity_years": 1,
        "skills_covered": ["azure", "app_service", "functions", "cosmos_db", "devops", "api"],
        "prerequisites": ["azure_fundamentals"],
        "renewal": {"required": True, "period_years": 1},
        "exam_details": {"duration_minutes": 120, "questions": 60},
        "target_roles": ["Azure Developer", "Software Engineer"],
        "industry": "cloud"
    },
    {
        "id": "azure_solutions",
        "name": "Microsoft Azure Solutions Architect Expert",
        "short_name": "AZ-305",
        "provider": "azure",
        "level": "expert",
        "cost_usd": 165,
        "validity_years": 1,
        "skills_covered": ["azure", "architecture", "identity", "security", "data", "monitoring"],
        "prerequisites": ["azure_admin", "azure_developer"],
        "renewal": {"required": True, "period_years": 1},
        "exam_details": {"duration_minutes": 180, "questions": 50},
        "target_roles": ["Solutions Architect", "Cloud Architect"],
        "industry": "cloud"
    }
]

COMPTIA_CERTIFICATIONS = [
    {
        "id": "comptia_a",
        "name": "CompTIA A+",
        "short_name": "A+",
        "provider": "comptia",
        "level": "fundamentals",
        "cost_usd": 246,
        "validity_years": 3,
        "skills_covered": ["hardware", "networking", "security", "troubleshooting", "mobile"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 3, "requirements": "CEUs or pass latest exam"},
        "exam_details": {"duration_minutes": 90, "questions": 90, "format": "Multiple choice and performance-based"},
        "target_roles": ["IT Support", "Help Desk Technician"],
        "industry": "it"
    },
    {
        "id": "comptia_network",
        "name": "CompTIA Network+",
        "short_name": "Net+",
        "provider": "comptia",
        "level": "associate",
        "cost_usd": 346,
        "validity_years": 3,
        "skills_covered": ["networking", "routing", "switching", "wireless", "troubleshooting"],
        "prerequisites": ["comptia_a"],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 90, "questions": 90},
        "target_roles": ["Network Administrator", "Network Technician"],
        "industry": "networking"
    },
    {
        "id": "comptia_security",
        "name": "CompTIA Security+",
        "short_name": "Sec+",
        "provider": "comptia",
        "level": "associate",
        "cost_usd": 370,
        "validity_years": 3,
        "skills_covered": ["security", "threats", "vulnerabilities", "identity", "compliance"],
        "prerequisites": ["comptia_network"],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 90, "questions": 90},
        "target_roles": ["Security Administrator", "Security Analyst"],
        "industry": "security"
    },
    {
        "id": "comptia_cydsa",
        "name": "CompTIA CySA+",
        "short_name": "CySA+",
        "provider": "comptia",
        "level": "professional",
        "cost_usd": 370,
        "validity_years": 3,
        "skills_covered": ["cybersecurity", "threat_detection", "incident_response", "monitoring", "analytics"],
        "prerequisites": ["comptia_security"],
        "renewal": {"required": True, "period_years": 3},
        "exam_details": {"duration_minutes": 165, "questions": 85},
        "target_roles": ["Cybersecurity Analyst", "SOC Analyst"],
        "industry": "security"
    }
]

HASHICORP_CERTIFICATIONS = [
    {
        "id": "terraform_associate",
        "name": "HashiCorp Certified: Terraform Associate",
        "short_name": "Terraform",
        "provider": "hashicorp",
        "level": "associate",
        "cost_usd": 70.50,
        "validity_years": 2,
        "skills_covered": ["terraform", "infrastructure", "cloud", "devops", "iac"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 2, "requirements": "Pass exam"},
        "exam_details": {"duration_minutes": 60, "questions": 57, "format": "Multiple choice"},
        "target_roles": ["DevOps Engineer", "Cloud Engineer", "Infrastructure Engineer"],
        "industry": "devops"
    },
    {
        "id": "vault_associate",
        "name": "HashiCorp Certified: Vault Associate",
        "short_name": "Vault",
        "provider": "hashicorp",
        "level": "associate",
        "cost_usd": 70.50,
        "validity_years": 2,
        "skills_covered": ["vault", "security", "secrets_management", "encryption", "iam"],
        "prerequisites": [],
        "renewal": {"required": True, "period_years": 2},
        "exam_details": {"duration_minutes": 60, "questions": 47},
        "target_roles": ["Security Engineer", "DevOps Engineer"],
        "industry": "security"
    }
]

ALL_CERTIFICATIONS = AWS_CERTIFICATIONS + GCP_CERTIFICATIONS + AZURE_CERTIFICATIONS + COMPTIA_CERTIFICATIONS + HASHICORP_CERTIFICATIONS
