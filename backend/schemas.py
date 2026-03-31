from pydantic import BaseModel
from typing import List, Optional

class AgentRequest(BaseModel):
    topic: str
    target: str
    style: str
    profile: dict

class EvaluateRequest(BaseModel):
    questions: list
    answers: list
    profile: dict
    topic: str

class SuggestRequest(BaseModel):
    profile: dict