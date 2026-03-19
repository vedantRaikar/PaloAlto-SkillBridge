import json
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.models.graph import ExtractionResult, Node, Link

class ExtractedNode(BaseModel):
    id: str
    type: str = Field(default="skill")
    category: Optional[str] = None

class ExtractedLink(BaseModel):
    source: str
    target: str
    type: str = "REQUIRES"

class LLMExtractionOutput(BaseModel):
    nodes: list[ExtractedNode] = Field(default_factory=list)
    links: list[ExtractedLink] = Field(default_factory=list)

EXTRACTION_PROMPT = PromptTemplate.from_template('''
You are a skill extraction system. Analyze the job description and extract technical skills, technologies, and the job role.

Extract:
1. All required skills/technologies mentioned (programming languages, frameworks, tools, platforms, databases, etc.)
2. The job role/title
3. Relationships between role and skills

Return ONLY valid JSON:
{{
  "nodes": [
    {{"id": "skill_name_in_snake_case", "type": "skill", "category": "inferred_category"}}
  ],
  "links": [
    {{"source": "role_id", "target": "skill_id", "type": "REQUIRES"}}
  ]
}}

Guidelines:
- Use lowercase IDs with underscores for skill names (e.g., machine_learning, amazon_web_services)
- Infer appropriate categories based on what the skill is (programming, frontend, backend, devops, cloud, database, ai, tools, security, mobile, api, architecture, data, infrastructure)
- Combine multi-word skills into single snake_case IDs
- Remove version numbers and articles

Job Title: {title}
Job Description: {description}

JSON Response:
''')

class EntityExtractor:
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant"):
        self.model = model
        self.llm = None
        self.api_key = api_key
        
        if api_key:
            self._initialize_llm()

    def _initialize_llm(self):
        self.llm = ChatGroq(
            api_key=self.api_key,
            model=self.model,
            temperature=0.1,
            max_tokens=2048
        )

    def _has_api_key(self) -> bool:
        return bool(self.api_key)

    async def extract(self, title: str, description: str) -> ExtractionResult:
        if not self._has_api_key():
            return ExtractionResult(
                nodes=[],
                links=[],
                success=False,
                method="llm_disabled"
            )

        try:
            parser = JsonOutputParser(pydantic_object=LLMExtractionOutput)
            chain = EXTRACTION_PROMPT | self.llm | parser
            
            result = await chain.ainvoke({
                "title": title,
                "description": description
            })

            nodes = [
                Node(
                    id=n["id"],
                    type="skill" if n["type"] == "skill" else "role",
                    category=n.get("category")
                )
                for n in result.get("nodes", [])
            ]

            links = [
                Link(
                    source=l["source"],
                    target=l["target"],
                    type=l.get("type", "REQUIRES")
                )
                for l in result.get("links", [])
            ]

            return ExtractionResult(
                nodes=nodes,
                links=links,
                success=len(nodes) > 0,
                method="llm"
            )

        except Exception as e:
            return ExtractionResult(
                nodes=[],
                links=[],
                success=False,
                method=f"llm_error: {str(e)}"
            )

    def extract_sync(self, title: str, description: str) -> ExtractionResult:
        if not self._has_api_key():
            return ExtractionResult(
                nodes=[],
                links=[],
                success=False,
                method="llm_disabled"
            )

        try:
            parser = JsonOutputParser(pydantic_object=LLMExtractionOutput)
            chain = EXTRACTION_PROMPT | self.llm | parser
            
            result = chain.invoke({
                "title": title,
                "description": description
            })

            nodes = [
                Node(
                    id=n["id"],
                    type="skill" if n["type"] == "skill" else "role",
                    category=n.get("category")
                )
                for n in result.get("nodes", [])
            ]

            links = [
                Link(
                    source=l["source"],
                    target=l["target"],
                    type=l.get("type", "REQUIRES")
                )
                for l in result.get("links", [])
            ]

            return ExtractionResult(
                nodes=nodes,
                links=links,
                success=len(nodes) > 0,
                method="llm"
            )

        except Exception as e:
            return ExtractionResult(
                nodes=[],
                links=[],
                success=False,
                method=f"llm_error: {str(e)}"
            )
