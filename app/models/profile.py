from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class ProfileSource(str, Enum):
    RESUME = "resume"
    GITHUB = "github"
    MANUAL = "manual"
    MERGED = "merged"

class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

class GitHubProfile(BaseModel):
    username: str
    name: Optional[str] = None
    bio: Optional[str] = None
    followers: int = 0
    public_repos: int = 0
    languages: Dict[str, float] = Field(default_factory=dict)
    top_skills: List[str] = Field(default_factory=list)
    repos: List[dict] = Field(default_factory=list)

class ResumeProfile(BaseModel):
    name: Optional[str] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None

class UserProfile(BaseModel):
    id: str
    name: str
    sources: List[ProfileSource] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    github: Optional[GitHubProfile] = None
    resume: Optional[ResumeProfile] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    experience_years: Optional[int] = None
    readiness_scores: Dict[str, float] = Field(default_factory=dict)

class ProfileMergeRequest(BaseModel):
    user_id: str
    github_username: Optional[str] = None
    resume_base64: Optional[str] = None
    resume_filename: Optional[str] = None
    additional_skills: List[str] = Field(default_factory=list)
