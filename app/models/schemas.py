from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    session_id: str
    message: str

class SessionRequest(BaseModel):
    user_data: Optional[Dict[str, Any]] = None

class UserExperienceRequest(BaseModel):
    session_id: str
    user_id: str
    rating: Optional[int] = None  # 1-5 scale
    feedback: Optional[str] = None
    usefulness_rating: Optional[int] = None  # 1-5 scale
    difficulty_appropriate: Optional[bool] = None
    would_recommend: Optional[bool] = None
    improvement_suggestions: Optional[str] = None
    favorite_features: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    difficulty_level: str
    proficiency_score: int
    teaching_strategy: str
    session_id: str

class SessionEndRequest(BaseModel):
    user_experience: Optional[UserExperienceRequest] = None