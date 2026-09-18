from pydantic import BaseModel, Field


class InvestigateRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language investigation question")
