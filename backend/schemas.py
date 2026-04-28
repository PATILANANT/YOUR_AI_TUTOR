from pydantic import BaseModel
from typing import List, Optional

class AgentRequest(BaseModel):
    topic: str
    target: str
    style: str
    profile: dict
    conversation_id: Optional[int] = None
    chat_history: Optional[List[dict]] = []

class EvaluateRequest(BaseModel):
    questions: list
    answers: list
    profile: dict
    topic: str

class SuggestRequest(BaseModel):
    profile: dict

class ChatRequest(BaseModel):
    query: str
    language: Optional[str] = "English"
    conversation_id: Optional[int] = None
    chat_history: Optional[List[dict]] = []
    profile: Optional[dict] = None