from pydantic import BaseModel
from typing import Optional, Literal
import uuid
import time


class ClipSettings(BaseModel):
    min_clips: int = 3
    max_clips: int = 8
    max_clip_seconds: int = 60
    preferred_seconds: int = 30
    aspect_ratio: Literal["9:16", "1:1", "16:9"] = "9:16"
    resolution: Literal["1080", "720"] = "1080"
    llm_provider: Literal["groq", "anthropic"] = "groq"
    subtitles: bool = True
    hook: bool = True
    highest_quality: bool = False


class ClipResult(BaseModel):
    filename: str
    title: str
    start: float
    end: float
    hook_text: Optional[str] = None


class Job(BaseModel):
    id: str
    status: Literal["queued", "downloading", "transcribing", "selecting", "rendering", "done", "error"] = "queued"
    progress: int = 0  # 0-100
    message: str = ""
    created_at: float = 0.0
    clips: list[ClipResult] = []
    error: Optional[str] = None

    @staticmethod
    def new() -> "Job":
        return Job(id=str(uuid.uuid4()), created_at=time.time())
