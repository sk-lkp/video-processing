from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class VideoBase(BaseModel):
    filename: str
    original_filename: str
    duration: float
    size: int
    upload_time: datetime
    path: str
    is_processed: bool = False
    quality: str = "original"

class VideoCreate(VideoBase):
    pass

class Video(VideoBase):
    id: int
    parent_id: Optional[int] = None
    
    class Config:
        orm_mode = True

class JobBase(BaseModel):
    type: str
    status: str = "pending"
    created_at: datetime
    parameters: dict

class JobCreate(JobBase):
    pass

class Job(JobBase):
    id: int
    job_id: str
    video_id: int
    completed_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class OverlayBase(BaseModel):
    type: str
    content: str
    position: str = "top-left"
    start_time: float = 0
    end_time: Optional[float] = None
    size: Optional[int] = None

class OverlayCreate(OverlayBase):
    video_id: int

class Overlay(OverlayBase):
    id: int
    video_id: int
    
    class Config:
        orm_mode = True

class TrimRequest(BaseModel):
    video_id: int
    start_time: float
    end_time: float

class QualityRequest(BaseModel):
    video_id: int
    quality: str  # 1080p, 720p, 480p